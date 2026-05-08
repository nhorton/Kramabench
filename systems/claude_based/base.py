"""
Shared base class for KramaBench SUTs that drive a Claude Code-style CLI
(currently `unsupervised` and plain `claude`).

Both SUTs follow the same lifecycle:
- `process_dataset` is called once per benchmark run. We build (or reuse) a
  per-domain "area" directory at `../<AREAS_DIRNAME>/<domain>/` peer to the
  KramaBench repo, run an optional CLI-specific install step, hard-copy the
  domain's data files into `datasources/local_files/<domain>/`, and run an
  optional CLI-specific connect step (e.g. UnsupervisedSystem seeds catalog
  markdown for the staged files). Idempotent via a `.kramabench.json`
  manifest.
- `serve_query` is called per task, possibly from worker processes. Each
  call spawns a fresh non-interactive `<cli> -p` session in the area
  directory. To avoid cross-task interference in the shared area dir, calls
  within a domain are serialized by an fcntl filelock on
  `<area_dir>/.kramabench.serve.lock`. Use `--num_workers 1` for best
  throughput.

Subclasses configure three class attrs (SYSTEM_NAME, CLI_BIN,
AREAS_DIRNAME) and may override `_install_step`, `_connect_step`, and
`_extra_invocation_argv`.

Returns the standard contract dict
(`{"explanation": {"answer": ...}, "pipeline_code": ..., "token_usage*": ...}`).
"""

from __future__ import annotations

import datetime as _dt
import fcntl
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from benchmark.benchmark_api import System

PER_TASK_INSTRUCTIONS = """\

You are answering a KramaBench task. Constraints for this run:
  - Treat the question above as the user request.
  - Use only files under `datasources/local_files/{domain}/`. Reference
    them with their relative paths under that directory.
  - Write your final answer pipeline (the SQL and/or Python you ran to
    produce the answer, with brief commentary) as a single markdown
    document to `outputs/{task_id}/pipeline.md` (create directories).
  - Use `queries/adhoc/{task_id}/...` for any intermediate query files
    you produce. Do not write outside `outputs/{task_id}/` or
    `queries/adhoc/{task_id}/`.
  - End your final assistant message with ONLY the answer to the
    question, on its own. No preamble, no explanation in the final
    message.
"""


class ClaudeBasedSystem(System):
    """Base SUT that drives a Claude Code-style CLI in `-p` JSON mode."""

    SYSTEM_NAME: str = ""
    CLI_BIN: str = ""
    AREAS_DIRNAME: str = ""
    # Prepended verbatim to the per-task query (not to the connect-datasource
    # prompt). Lets a subclass route every task through a CLI-side mode
    # selector — e.g. unsupervised's `/deepwork Data Query: `.
    REQUEST_PREFIX: str = ""

    def __init__(
        self,
        verbose: bool = False,
        output_dir: str | os.PathLike | None = None,
        model: str | None = None,
        task_timeout_s: int = 1800,
        connect_timeout_s: int = 1800,
        cli_bin: str | None = None,
        **_: Any,
    ) -> None:
        if not self.SYSTEM_NAME or not self.CLI_BIN or not self.AREAS_DIRNAME:
            raise TypeError(
                f"{type(self).__name__} must set SYSTEM_NAME, CLI_BIN, and AREAS_DIRNAME class attrs."
            )
        super().__init__(self.SYSTEM_NAME, verbose=verbose)
        if output_dir is None:
            raise ValueError(f"{self.SYSTEM_NAME} requires output_dir")
        self.output_dir = str(output_dir)
        self.model = model
        self.task_timeout_s = task_timeout_s
        self.connect_timeout_s = connect_timeout_s
        self.cli_bin = cli_bin or self.CLI_BIN

        # Hardcoded per the plan: peer to the repo root.
        self._repo_root = Path(__file__).resolve().parents[2]
        self.areas_root = self._repo_root.parent / self.AREAS_DIRNAME

        # Populated in process_dataset; safely picklable (strings only).
        self.domain: str | None = None
        self.area_dir: str | None = None

    def _derive_domain(self, dataset_directory: str | os.PathLike) -> str:
        # `data/<x>/input` -> `<x>`; `data/<x>/tiny` -> `<x>-tiny`.
        # See evaluate.py:109-158 for the layout convention.
        p = Path(dataset_directory).resolve()
        parent = p.parent.name
        base = p.name
        return parent if base == "input" else f"{parent}-{base}"

    def _run_subprocess(
        self,
        argv: List[str],
        cwd: str,
        timeout: int,
        log_dir: Path,
        log_prefix: str,
    ) -> subprocess.CompletedProcess:
        log_dir.mkdir(parents=True, exist_ok=True)
        if self.verbose:
            print(f"[{self.SYSTEM_NAME}] $ {' '.join(argv)}  (cwd={cwd})", file=sys.stderr)
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            (log_dir / f"{log_prefix}.error.txt").write_text(
                f"TimeoutExpired after {timeout}s\nstdout:\n{e.stdout or ''}\nstderr:\n{e.stderr or ''}\n",
            )
            raise
        (log_dir / f"{log_prefix}.stdout.txt").write_text(proc.stdout or "")
        (log_dir / f"{log_prefix}.stderr.txt").write_text(proc.stderr or "")
        return proc

    def _build_invocation(self, prompt: str) -> List[str]:
        argv = [
            self.cli_bin,
            "-p",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "bypassPermissions",
        ]
        if self.model:
            argv += ["--model", self.model]
        argv += self._extra_invocation_argv()
        return argv

    def _extra_invocation_argv(self) -> List[str]:
        """Override to append CLI-specific flags (e.g. `--max-budget-usd`)."""
        return []

    def _install_step(self, area_dir: Path, log_dir: Path) -> None:
        """Override to run a CLI-specific install/scaffold step. Default: no-op."""
        return

    def _connect_step(self, domain: str, area_dir: Path, log_dir: Path) -> None:
        """Override to run a CLI-specific connect/catalog-seeding step.
        Default: no-op (the SUT is expected to discover datasources itself
        per task)."""
        return

    def _read_manifest(self, manifest_path: Path) -> Dict[str, Any] | None:
        try:
            return json.loads(manifest_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def process_dataset(self, dataset_directory: str | os.PathLike) -> None:
        dataset_directory = str(dataset_directory)
        domain = self._derive_domain(dataset_directory)
        self.areas_root.mkdir(parents=True, exist_ok=True)
        area_dir = self.areas_root / domain
        area_dir.mkdir(parents=True, exist_ok=True)

        log_dir = Path(self.output_dir) / "_setup" / domain
        log_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = area_dir / ".kramabench.json"

        # Hold an exclusive lock on a sibling .lock file so concurrent harness
        # invocations don't clobber install / copy / connect.
        setup_lock = area_dir / ".kramabench.setup.lock"
        with open(setup_lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                manifest = self._read_manifest(manifest_path)
                already_set_up = (
                    manifest is not None
                    and manifest.get("kramabench_data_dir") == os.fspath(Path(dataset_directory).resolve())
                    and manifest.get("connected_at")
                )
                if not already_set_up:
                    self._setup_area(domain, dataset_directory, area_dir, log_dir)
                    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
                    manifest = {
                        "domain": domain,
                        "kramabench_data_dir": os.fspath(Path(dataset_directory).resolve()),
                        "installed_at": now,
                        "connected_at": now,
                    }
                    manifest_path.write_text(json.dumps(manifest, indent=2))
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

        self.domain = domain
        self.area_dir = str(area_dir)
        self.dataset_directory = dataset_directory

    def _setup_area(
        self,
        domain: str,
        dataset_directory: str,
        area_dir: Path,
        log_dir: Path,
    ) -> None:
        # 1. CLI-specific scaffold (e.g. `unsupervised install`); no-op by default.
        self._install_step(area_dir, log_dir)

        # 2. Hard-copy the data files in.
        staged_root = area_dir / "datasources" / "local_files" / domain
        staged_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dataset_directory, staged_root, dirs_exist_ok=True)

        # 3. CLI-specific connect/catalog-seeding step; no-op by default.
        self._connect_step(domain, area_dir, log_dir)

    def serve_query(
        self,
        query: str,
        query_id: str,
        subset_files: List[str] | None = None,
    ) -> Dict[str, Any]:
        if not self.area_dir or not self.domain:
            raise RuntimeError(
                "serve_query called before process_dataset; harness must call process_dataset first."
            )

        task_scratch = Path(self.output_dir) / query_id
        task_scratch.mkdir(parents=True, exist_ok=True)
        prompt = self._build_task_prompt(query, query_id, subset_files or [])
        (task_scratch / "prompt.txt").write_text(prompt)

        argv = self._build_invocation(prompt)
        empty_response = {
            "explanation": {"answer": "", "id": query_id},
            "pipeline_code": "",
            "token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }

        # Serialize calls within the area dir so concurrent workers don't trample
        # each other's queries/adhoc/<task_id> or outputs/<task_id>.
        serve_lock = Path(self.area_dir) / ".kramabench.serve.lock"
        try:
            with open(serve_lock, "w") as lf:
                fcntl.flock(lf, fcntl.LOCK_EX)
                try:
                    proc = self._run_subprocess(
                        argv,
                        cwd=self.area_dir,
                        timeout=self.task_timeout_s,
                        log_dir=task_scratch,
                        log_prefix="run",
                    )
                finally:
                    fcntl.flock(lf, fcntl.LOCK_UN)
        except subprocess.TimeoutExpired:
            (task_scratch / "error.txt").write_text(f"timeout after {self.task_timeout_s}s\n")
            return empty_response

        if proc.returncode != 0:
            err = (proc.stderr or "") + "\n" + (proc.stdout or "")
            note = ""
            if "max-budget" in err.lower() or "budget" in err.lower():
                note = "[budget cap hit] "
            (task_scratch / "error.txt").write_text(
                f"{note}exit={proc.returncode}\nstderr:\n{proc.stderr}\nstdout:\n{proc.stdout}\n"
            )
            return empty_response

        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            (task_scratch / "error.txt").write_text(f"could not parse stdout as JSON: {e}\n")
            return empty_response

        # Claude Code's -p --output-format json envelope:
        # {"type":"result","subtype":"success","is_error":bool,"result":"...",
        #  "usage":{"input_tokens":N,"output_tokens":N,...},"total_cost_usd":...}
        is_error = bool(parsed.get("is_error"))
        subtype = parsed.get("subtype", "")
        result_text = parsed.get("result") or ""

        if is_error or subtype == "error_max_turns":
            note = ""
            if "budget" in (result_text.lower() if isinstance(result_text, str) else ""):
                note = "[budget cap hit] "
            (task_scratch / "error.txt").write_text(f"{note}claude reported error: {parsed}\n")
            # We can still try to surface whatever partial result Claude returned.
            if not result_text:
                return empty_response

        usage = parsed.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)

        pipeline_code = self._collect_pipeline_code(query_id)
        # Mirror the captured pipeline into per-task scratch for easier inspection.
        if pipeline_code:
            (task_scratch / "pipeline.md").write_text(pipeline_code)

        return {
            "explanation": {"answer": result_text, "id": query_id},
            "pipeline_code": pipeline_code,
            "token_usage": input_tokens + output_tokens,
            "token_usage_input": input_tokens,
            "token_usage_output": output_tokens,
        }

    def _build_task_prompt(self, query: str, query_id: str, subset_files: List[str]) -> str:
        domain = self.domain
        parts = [self.REQUEST_PREFIX + query.strip()]
        if subset_files:
            listing = "\n".join(f"  - {p}" for p in subset_files)
            parts.append(
                "Use only these files (paths relative to "
                f"`datasources/local_files/{domain}/`):\n{listing}"
            )
        parts.append(PER_TASK_INSTRUCTIONS.format(domain=domain, task_id=query_id))
        return "\n\n".join(parts)

    def _collect_pipeline_code(self, query_id: str) -> str:
        """Concatenate outputs/<task_id>/pipeline.md plus any new files under
        queries/adhoc/<task_id>/ into a single string."""
        if not self.area_dir:
            return ""
        chunks: List[str] = []
        pipeline_md = Path(self.area_dir) / "outputs" / query_id / "pipeline.md"
        if pipeline_md.is_file():
            chunks.append(f"# outputs/{query_id}/pipeline.md\n\n" + pipeline_md.read_text())

        adhoc_dir = Path(self.area_dir) / "queries" / "adhoc" / query_id
        if adhoc_dir.is_dir():
            for path in sorted(adhoc_dir.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(Path(self.area_dir))
                    try:
                        body = path.read_text()
                    except (UnicodeDecodeError, OSError):
                        continue
                    chunks.append(f"# {rel}\n\n{body}")
        return "\n\n".join(chunks)
