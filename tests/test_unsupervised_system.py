"""Mocked unit tests for systems.unsupervised.UnsupervisedSystem.

These tests stub out `subprocess.run` so they don't actually invoke the
`unsupervised` CLI or hit any LLM API.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from systems.unsupervised import UnsupervisedSystem


def _make_dataset(tmp_path: Path, name: str = "legal", basename: str = "input") -> Path:
    """Create a fake dataset dir matching `data/<domain>/{input|tiny}` layout."""
    ds = tmp_path / "data" / name / basename
    ds.mkdir(parents=True)
    (ds / "a.csv").write_text("a,b\n1,2\n")
    (ds / "subdir").mkdir()
    (ds / "subdir" / "b.csv").write_text("c\n3\n")
    return ds


def _make_sut(tmp_path: Path, areas_root: Path | None = None) -> UnsupervisedSystem:
    sut = UnsupervisedSystem(
        verbose=False,
        output_dir=str(tmp_path / "scratch"),
        max_budget_usd=20.0,
    )
    if areas_root is None:
        areas_root = tmp_path / "unsup-areas"
    sut.areas_root = areas_root
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


def test_derive_domain_input_and_tiny(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    assert sut._derive_domain(tmp_path / "data" / "legal" / "input") == "legal"
    assert sut._derive_domain(tmp_path / "data" / "legal" / "tiny") == "legal-tiny"


def test_process_dataset_runs_install_then_connect_then_writes_manifest(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    ds = _make_dataset(tmp_path, name="legal", basename="input")

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        # First call is `unsupervised install`; we need to create the scaffold
        # marker so subsequent runs see it.
        if argv[:2] == [sut.cli_bin, "install"]:
            target = Path(argv[2])
            (target / "datasources" / "local_files").mkdir(parents=True, exist_ok=True)
            (target / "datasources" / "local_files" / "engine_factory.py").write_text("# stub\n")
            return _ok_run()
        # Otherwise it's the connect-datasource invocation.
        return _ok_run(stdout=_ok_claude_json(answer="connect-complete"))

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        sut.process_dataset(str(ds))

    assert sut.domain == "legal"
    area_dir = Path(sut.area_dir)  # type: ignore[arg-type]
    assert area_dir == sut.areas_root / "legal"
    # Files were copied into datasources/local_files/<domain>/.
    assert (area_dir / "datasources" / "local_files" / "legal" / "a.csv").exists()
    assert (area_dir / "datasources" / "local_files" / "legal" / "subdir" / "b.csv").exists()
    # Manifest written.
    manifest = json.loads((area_dir / ".kramabench.json").read_text())
    assert manifest["domain"] == "legal"
    assert manifest["kramabench_data_dir"] == str(ds.resolve())
    # Two subprocess invocations: install + connect.
    assert len(calls) == 2
    assert calls[0][:2] == [sut.cli_bin, "install"]
    assert calls[1][:2] == [sut.cli_bin, "-p"]
    assert "--permission-mode" in calls[1]
    assert "--max-budget-usd" in calls[1]
    # The connect-datasource prompt must NOT carry the per-task /deepwork prefix.
    connect_prompt = calls[1][calls[1].index("-p") + 1]
    assert not connect_prompt.startswith("/deepwork"), connect_prompt[:60]


def test_process_dataset_idempotent_when_manifest_matches(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    ds = _make_dataset(tmp_path, name="legal", basename="input")

    def first_run(argv, **kwargs):
        if argv[:2] == [sut.cli_bin, "install"]:
            target = Path(argv[2])
            (target / "datasources" / "local_files").mkdir(parents=True, exist_ok=True)
            (target / "datasources" / "local_files" / "engine_factory.py").write_text("# stub\n")
            return _ok_run()
        return _ok_run(stdout=_ok_claude_json(answer="connect-complete"))

    with patch("systems.claude_based.base.subprocess.run", side_effect=first_run):
        sut.process_dataset(str(ds))

    # Second call should not invoke subprocess at all.
    with patch("systems.claude_based.base.subprocess.run") as mock_run:
        sut.process_dataset(str(ds))
        assert mock_run.call_count == 0


def test_serve_query_returns_contract_and_extracts_pipeline(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    ds = _make_dataset(tmp_path)

    # Pre-stage area dir state so process_dataset doesn't run subprocesses.
    area_dir = sut.areas_root / "legal"
    (area_dir / "datasources" / "local_files").mkdir(parents=True, exist_ok=True)
    (area_dir / "datasources" / "local_files" / "engine_factory.py").write_text("# stub\n")
    (area_dir / ".kramabench.json").write_text(
        json.dumps(
            {
                "domain": "legal",
                "kramabench_data_dir": str(ds.resolve()),
                "installed_at": "x",
                "connected_at": "x",
            }
        )
    )
    sut.domain = "legal"
    sut.area_dir = str(area_dir)
    sut.dataset_directory = str(ds)

    # Simulate the analyst writing a pipeline file.
    task_id = "legal-easy-1"
    pipeline_path = area_dir / "outputs" / task_id / "pipeline.md"
    pipeline_path.parent.mkdir(parents=True)
    pipeline_path.write_text("```sql\nSELECT 1\n```\n")
    adhoc_path = area_dir / "queries" / "adhoc" / task_id / "step1.md"
    adhoc_path.parent.mkdir(parents=True)
    adhoc_path.write_text("---\nsql: SELECT 2\n---\n")

    def fake_run(argv, **kwargs):
        # Sanity-check the prompt was constructed properly.
        prompt = argv[argv.index("-p") + 1]
        # Per-task prompts must be prefixed with the unsupervised /deepwork
        # mode selector so the analyst routes the request correctly.
        assert prompt.startswith("/deepwork Data Query: What is X?"), prompt[:80]
        assert "datasources/local_files/legal/" in prompt
        assert "outputs/legal-easy-1/pipeline.md" in prompt
        # subset_files was provided -> they must appear in the prompt.
        assert "a.csv" in prompt
        return _ok_run(stdout=_ok_claude_json(answer="42", input_tokens=100, output_tokens=20))

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        result = sut.serve_query(query="What is X?", query_id=task_id, subset_files=["a.csv"])

    assert result["explanation"]["answer"] == "42"
    assert result["token_usage"] == 120
    assert result["token_usage_input"] == 100
    assert result["token_usage_output"] == 20
    assert "SELECT 1" in result["pipeline_code"]
    assert "SELECT 2" in result["pipeline_code"]


def test_serve_query_returns_empty_response_on_nonzero_exit_and_logs_budget_hit(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    area_dir = sut.areas_root / "legal"
    area_dir.mkdir(parents=True)
    sut.domain = "legal"
    sut.area_dir = str(area_dir)

    def fake_run(argv, **kwargs):
        return _ok_run(stdout="", stderr="error: --max-budget-usd cap reached", returncode=2)

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        result = sut.serve_query(query="q", query_id="legal-easy-1", subset_files=[])

    assert result == {
        "explanation": {"answer": "", "id": "legal-easy-1"},
        "pipeline_code": "",
        "token_usage": 0,
        "token_usage_input": 0,
        "token_usage_output": 0,
    }
    err = (Path(sut.output_dir) / "legal-easy-1" / "error.txt").read_text()
    assert "[budget cap hit]" in err


def test_serve_query_returns_empty_response_on_timeout(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    area_dir = sut.areas_root / "legal"
    area_dir.mkdir(parents=True)
    sut.domain = "legal"
    sut.area_dir = str(area_dir)

    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=1, output="", stderr="")

    with patch("systems.claude_based.base.subprocess.run", side_effect=fake_run):
        result = sut.serve_query(query="q", query_id="legal-easy-1", subset_files=[])

    assert result["explanation"]["answer"] == ""
    err = (Path(sut.output_dir) / "legal-easy-1" / "error.txt").read_text()
    assert "timeout" in err


def test_serve_query_raises_if_not_configured(tmp_path: Path) -> None:
    sut = _make_sut(tmp_path)
    with pytest.raises(RuntimeError):
        sut.serve_query(query="q", query_id="x", subset_files=[])


def test_sut_is_picklable(tmp_path: Path) -> None:
    """The harness deepcopies the SUT once per worker; we hold only paths/strings."""
    import copy

    sut = _make_sut(tmp_path)
    sut.domain = "legal"
    sut.area_dir = str(tmp_path / "unsup-areas" / "legal")
    sut.dataset_directory = str(tmp_path / "data" / "legal" / "input")
    clone = copy.deepcopy(sut)
    assert clone.domain == "legal"
    assert clone.area_dir == sut.area_dir
