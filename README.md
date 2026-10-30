# ErrorAgent: agentic scene reconstruction from partial video

An agent CLI (Claude Code or Codex) gets one video, the whole walkthrough or a
part of it cut beforehand, and rebuilds the entire room as an animated Blender scene
(`result.blend`). Comparing the result with ground truth in regions the clip
did and did not see is a separate step and is not in this suite.

The task follows BVB: one video in, primitives-only bpy, an animated camera,
and `result.blend` out. The execution environment follows 4DCodeBench: one
container per run, the host's subscription login mounted read-only, and the
CLI's own transcript kept. `BVB/` and `4DCodeBench/` are kept only as
references; nothing here imports them.

```
docker/Dockerfile        Ubuntu 22.04, Blender 4.2, xvfb, ffmpeg, Claude Code, Codex
task/TASK.md             the prompt template, identical for every video
pipeline/run.py          jobs file -> one container per trial -> runs/
pipeline/clip.py         probes a video's frame count, frame rate, size and duration
pipeline/agents.py       each CLI's headless command line
pipeline/inspect_blend.py  post-run check: does result.blend open, and what does it contain
jobs.example.toml        settings and [[job]] entries
```

## Setup

```bash
docker build -t erroragent:latest --build-arg UID=$(id -u) --build-arg GID=$(id -g) docker/
```

Log in once on the host (`claude` then `/login`; `codex login`). Each run
mounts `~/.claude/.credentials.json` or `~/.codex/auth.json` read-only and
nothing else from your home. A container cannot refresh an expired token, so
re-login on the host if a run fails on authentication.

Put the videos under `videos/<dataset>/<scene>.mp4`, for example
`videos/scannet/scene0011_00.mp4`.

## Run

```bash
cp jobs.example.toml jobs.toml          # edit the [[job]] entries
python3 pipeline/run.py jobs.toml --dry-run
python3 pipeline/run.py jobs.toml
```

A job is one video, agent, model and effort, run for `trials` trials. The
pipeline does not cut or re-encode videos: each one is mounted read-only as
the agent's input exactly as it is on disk. To test a partial walkthrough, cut
that part into its own file beforehand. Trials run one after another. A trial that already has a
`run.json` is skipped unless `--force` is given.

Each trial writes `runs/<dataset>/<scene>/<agent>-<model>-<effort>/<trial>/`:

| Path | What it is |
|---|---|
| `TASK.md` | the exact prompt it got |
| `workspace/output/result.blend` | the delivery |
| `workspace/scratch/`, `workspace/frames/` | its scripts, previews and extracted frames |
| `agent.log` | the CLI's event stream (Claude `stream-json`, Codex `--json`) |
| `home/.claude/projects/`, `home/.codex/sessions/` | the CLI's own session transcript |
| `summary.json` | scene settings, cameras, and each object's collections and world bounding box |
| `run.json` | the job, the video's path and properties, the full command, exit code, time, checks |

`run.json` records the input video's path (`clip.source`) and its frame
count, frame rate, size and duration. Blender frame `f` matches video frame
`f-1`. If the video was cut from a longer walkthrough, keep track of its
first source frame yourself to match the reconstructed camera against
ScanNet's poses.

## Choices worth knowing

- **The prompt is the same for every video.** It says the video may not show
  the whole room and asks for the entire room, guessing plausibly where there is
  no evidence. Without that line, an agent given half a walkthrough may build
  only what it saw, and then there are no unseen-region objects to count. Edit
  `task/TASK.md` to change this.
- **Isolation.** The agent runs as your UID, not as root, so its files belong
  to you. Claude Code runs with `bypassPermissions`, a fixed tool list
  (`Bash Read Write Edit Glob Grep Task TodoWrite`) and no MCP servers.
  Without `--strict-mcp-config`, the subscription login brings your claude.ai
  connectors (Drive, Gmail, Notion, ...) into the container. Codex runs with
  web search, apps, plugins, browser, computer use and image generation turned
  off. The network stays on because the CLIs must reach their providers.
- **Looking at the video.** Neither CLI can play a video. The prompt tells the
  agent to extract frames with ffmpeg and open the images, which works with
  Claude Code's `Read` and Codex's `view_image`.
