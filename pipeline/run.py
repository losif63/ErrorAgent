"""Run reconstruction jobs, each trial in its own container with one agent CLI.

    python pipeline/run.py jobs.toml [--dry-run] [--force]

A job is one video, agent, model and effort, run for `trials` trials. The video
is used as given (any splitting happens beforehand) and mounted read-only at
/input/video.mp4. Each trial goes to runs/<video>/<agent>-<model>-<effort>/<trial>/:

    TASK.md         the prompt it was given, mounted read-only at /task/TASK.md
    workspace/      its /workspace: output/result.blend, scratch/, frames/
    home/           its $HOME, which holds the CLI's own session transcript
    agent.log       the CLI's stdout and stderr, its event stream
    summary.json    what inspect_blend.py read from result.blend
    run.json        the job, the video's path and properties, the command, exit and timing

A trial whose run.json exists is skipped unless --force is given.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import AGENTS, TASK, WORKSPACE
from clip import probe

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "task" / "TASK.md"
INSPECT = Path(__file__).resolve().parent / "inspect_blend.py"
HOME = "/home/agent"
VIDEO = "/input/video.mp4"
BLEND = "output/result.blend"
BLENDER_VERSION = "5.2"


def resolve(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def expand(document: dict) -> list[dict]:
    """Return one entry per (job, trial)."""

    trials = []
    for job in document["job"]:
        if job["agent"] not in AGENTS:
            raise KeyError(f"unknown agent {job['agent']!r}; known: {sorted(AGENTS)}")
        for trial in range(1, int(job.get("trials", 1)) + 1):
            trials.append({key: job[key] for key in ("video", "agent", "model", "effort")}
                          | {"trial": trial})
    return trials


def render_task(clip: dict) -> str:
    values = {key: clip[key] for key in ("duration", "frames", "width", "height")}
    values["fps"] = f"{clip['fps']:g}"
    values["blender_version"] = BLENDER_VERSION
    return re.sub(r"{{(\w+)}}", lambda match: str(values[match.group(1)]), TEMPLATE.read_text())


def docker_run(config: dict, name: str, mounts: list[tuple[Path, str, str]],
               command: list[str], network: bool) -> list[str]:
    return [
        "docker", "run", "--rm", "--init", "--name", name,
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--env", f"HOME={HOME}",
        f"--cpus={config.get('cpus', os.cpu_count())}", f"--memory={config.get('memory', '16g')}",
        *([] if network else ["--network", "none"]),
        *(item for source, target, mode in mounts for item in ("-v", f"{source}:{target}:{mode}")),
        "-w", WORKSPACE,
        config.get("image", "erroragent:latest"),
        *command,
    ]


def run_process(command: list[str], log: Path) -> int:
    """Run the container to completion with its output in `log`; return its exit code."""

    with log.open("w", encoding="utf-8") as sink:
        return subprocess.run(command, stdout=sink, stderr=subprocess.STDOUT, check=False).returncode


def one(trial: dict, config: dict, dry_run: bool, force: bool) -> dict | None:
    agent = AGENTS[trial["agent"]]
    video = resolve(config.get("videos_root", "videos")) / trial["video"]
    run_dir = (resolve(config.get("runs_root", "runs")) / Path(trial["video"]).with_suffix("")
               / f"{agent.name}-{trial['model']}-{trial['effort']}" / str(trial["trial"]))
    label = f"{trial['video']} {agent.name}-{trial['model']}-{trial['effort']} #{trial['trial']}"
    if (run_dir / "run.json").exists() and not force:
        print(f"[skip] {label}: {run_dir / 'run.json'} exists")
        return None

    credential = Path.home() / agent.credential
    if "credentials" in config and agent.name in config["credentials"]:
        credential = resolve(config["credentials"][agent.name])
    command = agent.command(trial["model"], trial["effort"])
    if dry_run:
        print(f"[dry-run] {label}\n  video {video}\n  run   {run_dir}\n  $ {shlex.join(command)}")
        return None
    if not video.is_file():
        raise FileNotFoundError(video)
    if not credential.is_file():
        raise FileNotFoundError(f"{agent.name} credential {credential}")

    if run_dir.exists():
        shutil.rmtree(run_dir)
    workspace, home = run_dir / "workspace", run_dir / "home"
    for directory in (workspace / "output", workspace / "scratch", home / agent.sessions):
        directory.mkdir(parents=True)
    # the credential is bind-mounted over this empty file, so docker does not create it as root
    (home / agent.credential).touch()
    clip = {"source": str(video), **probe(video)}
    (run_dir / "TASK.md").write_text(render_task(clip), encoding="utf-8")

    name = f"recon-{uuid.uuid4().hex[:12]}"
    mounts = [
        (video.resolve(), VIDEO, "ro"),
        (run_dir / "TASK.md", TASK, "ro"),
        (workspace, WORKSPACE, "rw"),
        (home, HOME, "rw"),
        (credential.resolve(), f"{HOME}/{agent.credential}", "ro"),
    ]
    agent_command = docker_run(config, name, mounts, command, network=True)
    record = {**trial, "clip": clip,
              "frame_map": "Blender frame f = video frame f-1",
              "image": config.get("image", "erroragent:latest"), "container": name,
              "command": shlex.join(agent_command)}
    print(f"[run] {label} -> {run_dir}", flush=True)

    started = time.time()
    record["exit"] = run_process(agent_command, run_dir / "agent.log")
    record["seconds"] = round(time.time() - started, 1)
    record["delivered"] = (workspace / BLEND).is_file()

    if record["delivered"]:
        inspect = docker_run(config, f"{name}-inspect", [
            (workspace / BLEND, "/check/result.blend", "ro"),
            (INSPECT, "/check/inspect_blend.py", "ro"),
            (run_dir, "/check/out", "rw"),
        ], ["blender", "--background", "/check/result.blend", "--python-exit-code", "1",
            "--python", "/check/inspect_blend.py", "--", "/check/out/summary.json"], network=False)
        result = subprocess.run(inspect, capture_output=True, text=True, check=False)
        record["blend_opens"] = result.returncode == 0 and (run_dir / "summary.json").is_file()
        if record["blend_opens"]:
            summary = json.loads((run_dir / "summary.json").read_text())
            record.update({key: summary[key] for key in ("meshes", "cameras", "lights", "scene_camera")})
        else:
            record["inspect_error"] = (result.stdout + result.stderr)[-2000:]

    (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"[done] {label}: exit {record['exit']}, {record['seconds']}s, "
          f"delivered={record['delivered']} opens={record.get('blend_opens')}", flush=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent reconstruction jobs in containers.")
    parser.add_argument("jobs", type=Path, help="a jobs .toml (see jobs.example.toml)")
    parser.add_argument("--dry-run", action="store_true", help="print each trial's command; run nothing")
    parser.add_argument("--force", action="store_true", help="rerun trials whose run.json exists")
    args = parser.parse_args()

    config = tomllib.loads(args.jobs.read_text(encoding="utf-8"))
    records = [one(trial, config, args.dry_run, args.force) for trial in expand(config)]
    ran = [record for record in records if record is not None]
    failed = [record for record in ran if record["exit"] != 0 or not record.get("blend_opens")]
    if ran:
        print(f"[summary] {len(ran) - len(failed)}/{len(ran)} delivered a result.blend that opens")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
