"""The headless command line of each agent CLI, and where it keeps its files under $HOME."""

from __future__ import annotations

from dataclasses import dataclass

TASK = "/task/TASK.md"
WORKSPACE = "/workspace"


@dataclass(frozen=True)
class Agent:
    name: str
    credential: str     # the credential file, relative to $HOME, on the host and in the container
    sessions: str       # the CLI's own transcripts, relative to $HOME

    def command(self, model: str, effort: str) -> list[str]:
        raise NotImplementedError


class ClaudeCode(Agent):
    def command(self, model: str, effort: str) -> list[str]:
        return ["bash", "-c", (
            f'ENABLE_CLAUDEAI_MCP_SERVERS=false claude -p "$(cat {TASK})" --model {model} --effort {effort} '
            "--permission-mode bypassPermissions --strict-mcp-config "
            "--tools Bash,Read,Write,Edit,Glob,Grep,Task,TodoWrite "
            "--output-format stream-json --verbose < /dev/null"
        )]


class Codex(Agent):
    def command(self, model: str, effort: str) -> list[str]:
        return ["bash", "-c", (
            f'codex exec "$(cat {TASK})" --model {model} '
            f'-c model_reasoning_effort="{effort}" -c web_search="disabled" '
            "--disable plugins --disable remote_plugin --disable apps --disable browser_use "
            "--disable computer_use --disable image_generation "
            f"--dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C {WORKSPACE} --json < /dev/null"
        )]


AGENTS: dict[str, Agent] = {
    "claude": ClaudeCode("claude", credential=".claude/.credentials.json", sessions=".claude/projects"),
    "codex": Codex("codex", credential=".codex/auth.json", sessions=".codex/sessions"),
}
