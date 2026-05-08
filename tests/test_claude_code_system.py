"""Mocked unit tests for systems.claude_code.ClaudeCodeSystem.

These tests stub out `subprocess.run` so they don't actually invoke the
`claude` CLI or hit any LLM API. They cover the bits that differ from
UnsupervisedSystem: no install step, no `--max-budget-usd` flag, distinct
areas dir.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from systems.claude_code import ClaudeCodeSystem


def _make_dataset(tmp_path: Path, name: str = "legal", basename: str = "input") -> Path:
    ds = tmp_path / "data" / name / basename
    ds.mkdir(parents=True)
    (ds / "a.csv").write_text("a,b\n1,2\n")
    return ds


def _make_sut(tmp_path: Path) -> ClaudeCodeSystem:
    sut = ClaudeCodeSystem(verbose=False, output_dir=str(tmp_path / "scratch"))
    sut.areas_root = tmp_path / "claude-areas"
    return sut


def _ok_run(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _ok_claude_json(answer: str = "42", input_tokens: int = 10, output_tokens: int = 5) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": answer,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            "total_cost_usd": 0.01,
        }
    )


def test_class_attrs_match_areas_layout(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    assert sut.cli_bin == "claude"
    assert sut.SYSTEM_NAME == "ClaudeCodeSystem"
    assert sut.AREAS_DIRNAME == "claude-areas"


def test_invocation_argv_has_no_budget_flag(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    argv = sut._build_invocation("hello")
    assert argv[:2] == ["claude", "-p"]
    assert "--output-format" in argv and "json" in argv
    assert "--permission-mode" in argv and "bypassPermissions" in argv
    # Plain `claude` does not accept --max-budget-usd; ensure it is NOT included.
    assert "--max-budget-usd" not in argv


def test_process_dataset_skips_install_runs_only_connect(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    ds = _make_dataset(tmp_path, name="legal", basename="input")

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return _ok_run(stdout=_ok_claude_json(answer="connect-complete"))

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        sut.process_dataset(str(ds))

    # ClaudeCodeSystem has no install step — exactly one subprocess call (connect).
    assert len(calls) == 1
    assert calls[0][:2] == ["claude", "-p"]

    # Files copied; manifest written.
    area_dir = Path(sut.area_dir)  # type: ignore[arg-type]
    assert area_dir == sut.areas_root / "legal"
    assert (area_dir / "datasources" / "local_files" / "legal" / "a.csv").exists()
    assert (area_dir / ".kramabench.json").exists()


def test_serve_query_returns_contract(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    ds = _make_dataset(tmp_path)

    area_dir = sut.areas_root / "legal"
    area_dir.mkdir(parents=True)
    sut.domain = "legal"
    sut.area_dir = str(area_dir)
    sut.dataset_directory = str(ds)

    task_id = "legal-easy-1"
    pipeline_path = area_dir / "outputs" / task_id / "pipeline.md"
    pipeline_path.parent.mkdir(parents=True)
    pipeline_path.write_text("```sql\nSELECT 1\n```\n")

    def fake_run(argv, **kwargs):
        # Confirm we shelled out to `claude`, not `unsupervised`.
        assert argv[0] == "claude"
        # ClaudeCodeSystem has no REQUEST_PREFIX, so the prompt must start
        # with the raw query, not a slash-command.
        prompt = argv[argv.index("-p") + 1]
        assert prompt.startswith("What is X?"), prompt[:60]
        return _ok_run(stdout=_ok_claude_json(answer="42", input_tokens=100, output_tokens=20))

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        result = sut.serve_query(query="What is X?", query_id=task_id, subset_files=[])

    assert result["explanation"]["answer"] == "42"
    assert result["token_usage"] == 120
    assert "SELECT 1" in result["pipeline_code"]


def test_areas_root_distinct_from_unsupervised(tmp_path: Path) -> None:
    """Sanity: a fresh ClaudeCodeSystem and UnsupervisedSystem should not collide
    on the on-disk areas directory, even with default settings."""
    from systems.unsupervised import UnsupervisedSystem

    cc = ClaudeCodeSystem(output_dir=str(tmp_path / "cc_scratch"))
    us = UnsupervisedSystem(output_dir=str(tmp_path / "us_scratch"))
    assert cc.areas_root.name == "claude-areas"
    assert us.areas_root.name == "unsup-areas"
    assert cc.areas_root != us.areas_root
