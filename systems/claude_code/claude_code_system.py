"""
KramaBench SUT that drives the plain `claude` (Claude Code) CLI.

Sibling of `UnsupervisedSystem` — both are thin subclasses of
`ClaudeBasedSystem`. This one has no install/scaffold step (plain
Claude Code has no `install` subcommand) and no `--max-budget-usd`
flag, so the base class behavior is sufficient as-is.

Working directories live at `../claude-areas/<domain>/` peer to the
KramaBench repo, deliberately disjoint from `unsup-areas/` so the two
SUTs can run side-by-side without colliding on data, manifests, locks,
or Claude Code session transcripts (`~/.claude/projects/`).
"""

from __future__ import annotations

from systems.claude_based.base import ClaudeBasedSystem

CLAUDE_BIN = "claude"


class ClaudeCodeSystem(ClaudeBasedSystem):
    """SUT that drives the plain `claude` (Claude Code) CLI."""

    SYSTEM_NAME = "ClaudeCodeSystem"
    CLI_BIN = CLAUDE_BIN
    AREAS_DIRNAME = "claude-areas"
