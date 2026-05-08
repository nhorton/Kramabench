"""
KramaBench SUT that drives the locally-installed `unsupervised` CLI
(a Claude Code wrapper shipping an `analyst` role with DuckDB tooling).

Thin subclass of `ClaudeBasedSystem`. Adds two unsupervised-specific
behaviors:
  - an `unsupervised install <area_dir>` scaffold step on first setup;
  - a `--max-budget-usd` flag on every CLI invocation.

Everything else (area-dir lifecycle, fcntl locking, JSON envelope
parsing, pipeline collection) lives in the base class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from systems.claude_based.base import ClaudeBasedSystem

UNSUPERVISED_BIN = "unsupervised"


class UnsupervisedSystem(ClaudeBasedSystem):
    """SUT that drives the `unsupervised` CLI (Claude Code wrapper)."""

    SYSTEM_NAME = "UnsupervisedSystem"
    CLI_BIN = UNSUPERVISED_BIN
    AREAS_DIRNAME = "unsup-areas"
    # Routes every task through unsupervised's `/deepwork` analyst mode.
    # Not applied to the connect-datasource prompt (catalog seeding).
    REQUEST_PREFIX = "/deepwork Data Query: "

    def __init__(
        self,
        max_budget_usd: float | None = 20.0,
        unsupervised_bin: str | None = None,
        **kwargs: Any,
    ) -> None:
        # Preserve the `unsupervised_bin=` kwarg name from the previous API.
        if unsupervised_bin is not None:
            kwargs.setdefault("cli_bin", unsupervised_bin)
        super().__init__(**kwargs)
        self.max_budget_usd = max_budget_usd

    def _extra_invocation_argv(self) -> List[str]:
        if self.max_budget_usd is None:
            return []
        return ["--max-budget-usd", str(self.max_budget_usd)]

    def _install_step(self, area_dir: Path, log_dir: Path) -> None:
        scaffold_marker = area_dir / "datasources" / "local_files" / "engine_factory.py"
        if scaffold_marker.exists():
            return
        proc = self._run_subprocess(
            [self.cli_bin, "install", str(area_dir)],
            cwd=str(area_dir),
            timeout=self.connect_timeout_s,
            log_dir=log_dir,
            log_prefix="install",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"unsupervised install failed (exit {proc.returncode}); see {log_dir}/install.stderr.txt"
            )
