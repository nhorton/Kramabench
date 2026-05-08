# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

KramaBench is a benchmark for end-to-end data-science agents. Each task in a workload asks a System Under Test (SUT) to load raw files from a domain "data lake," build a pipeline, and produce a final answer. The harness scores both the final answer and intermediate sub-task answers against ground truth.

## Common commands

Install:
```bash
pip install -r requirements-dev.txt   # one-shot dev setup (preferred — see note below)
```

`pip install -e ".[all]"` from `pyproject.toml` does NOT work out-of-the-box —
setuptools auto-discovery sees `data/`, `systems/`, `experts/`, etc. as
multiple top-level packages and bails. `requirements-dev.txt` mirrors
`[project] + .baselines + .dev` plus the few transitive imports
(`untruncate-json`, etc.) that aren't declared in `pyproject.toml`. Update it
when you add a real new dependency.

Run the benchmark on one workload:
```bash
python evaluate.py --sut <SUTClassName> --workload <domain>
# domains: archeology, astronomy, biomedical, environment, legal, wildfire
# also: legal-tiny, environment-tiny for smoke tests
```

Useful flags (defined in `evaluate.py`):
- `--use_system_cache` reuse prior system outputs from `results/<SUT>/response_cache/`
- `--use_evaluation_cache` reuse the most recent `<workload>_measures_*.csv` instead of re-evaluating
- `--use_truth_subset` restrict each task's input to the ground-truth `data_sources` from the workload JSON
- `--run_subtasks` execute and evaluate sub-tasks in addition to the top-level task
- `--no_pipeline_eval` skip the LLM-based pipeline-design/implementation grading (saves API calls)
- `--num_workers N` parallelism (default 8, uses `ProcessPoolExecutor`)

`./eval.sh` runs all six domains for one SUT (activates a conda env named `smol311` — adjust if not using conda).

Tests:
```bash
pytest                                    # config in pyproject.toml: -sv --durations=0
pytest tests/test_per_task_caching.py     # single file
pytest -k cache_merge                     # by name
```

Lint: `ruff check .` (line-length 119, isort first-party = `kramabench, benchmark, systems`).

## Architecture

### The flow of one `evaluate.py` run
1. Loads `workload/<workload>.json` — a list of task dicts (`id`, `query`, `answer`, `answer_type`, `data_sources`, optional `subtasks`).
2. Instantiates the SUT by name: `getattr(__import__("systems"), args.sut)(verbose=…, output_dir=…)`. **Any new SUT class must be re-exported from `systems/__init__.py` so this lookup succeeds.**
3. `Benchmark.run_benchmark` (`benchmark/benchmark.py`) calls `system.process_dataset(data/<workload>/input)` once, then partitions task IDs round-robin across `num_workers` and runs each partition in a child process via `Executor.run_workload`.
4. `Executor.run_task` (`benchmark/executor.py`) calls `system.serve_query(query, query_id, subset_files)`. The SUT must return `{"explanation": {"answer": ...}, "pipeline_code": <str>, "token_usage"...}`.
5. `Evaluator` (`benchmark/evaluator.py`) scores each result using metrics chosen by `answer_type` (see `benchmark/fixtures/answer_type_fixtures.json`). Results are written to `results/<SUT>/<workload>_measures_<timestamp>.csv` and aggregated into `results/aggregated_results.csv`.

### The SUT contract (`benchmark/benchmark_api.py`)
A SUT subclasses `System` and implements:
- `process_dataset(dataset_directory)` — must set `self.dataset_directory` (the executor will refuse to run otherwise).
- `serve_query(query, query_id, subset_files)` — returns the dict above. `subset_files` is the truth/deepresearch subset when those flags are set, otherwise `[]` (SUT decides what to read).

Because workers are spawned with `ProcessPoolExecutor` and the harness `copy.deepcopy`s the SUT for each worker, **SUT instances must be picklable** (no open file handles, no unpicklable model clients held as attributes after `process_dataset`).

### Caching layers (easy to confuse)
- **System cache** (`--use_system_cache` / `--cache_system_output`): raw SUT responses. Per-task files live in `results/<SUT>/response_cache/tasks/<basename>_task_<task_id>_<ts>.json` and are merged into a single `<basename>_<ts>.json`.
- **Evaluation cache** (`--use_evaluation_cache`): the post-scoring `<workload>_measures_*.csv`. Skips re-running both the SUT and the evaluator.
- **System scratch**: `system_scratch/<SUT>/` is the SUT's writable working dir (passed in as `output_dir`).

### Bundled SUTs
- `systems/dummy_system.py:DummySystem` — returns canned output. Use for testing the harness.
- `systems/baseline_example.py:ExampleBaselineSystem` — minimal scaffold to copy from.
- `systems/dsguru/` — DS-GURU baseline (sample rows → prompt → execute → retry); variations are concrete classes like `BaselineLLMSystemGPTo3FewShot` re-exported via `dsguru/__init__.py`.
- `systems/smolagents/` — smolagents-based agents.

### Workloads and data
- `workload/<domain>.json` — task definitions. Each task may declare `data_sources` (truth subset) and `deepresearch_subset` (alternative file subset).
- `data/<domain>/input/` — the actual files the SUT reads (PDFs, CSVs, HTML, etc.). For `*-tiny` workloads the directory is `data/<domain>/tiny/`.
- `benchmark/fixtures/*.json` — drive the metric selection per `answer_type` and per task.

## Working in this branch

This branch is for building an adapter that runs KramaBench tasks via the locally-installed `unsupervised` CLI. Concretely, that means a new SUT class (e.g. `systems/unsupervised/…`) that implements `process_dataset` (point unsupervised at `data/<domain>/input` as a DuckDB-compatible datasource) and `serve_query` (drive unsupervised to write+run queries and return its answer + the generated code in the `{"explanation": {"answer": …}, "pipeline_code": …}` shape). Remember to re-export the class from `systems/__init__.py` so `--sut` can find it.

### Input mode: Full

`UnsupervisedSystem` runs in the paper's **Full input mode** — the SUT is shown the entire domain data lake (every file in `data/<domain>/input/`, distractors included) and has to discover which files matter as part of solving each task. `process_dataset` `shutil.copytree`s the whole tree into `unsup-areas/<domain>/datasources/local_files/<domain>/` and the connect-datasource prompt walks every file recursively to seed a catalog before any task runs. Closest paper analog is smolagents single-agent DR (agentic retrieval over the full lake), not DS-Guru (one-pass sampling). The two other modes from the paper are Oracle (only the task's gold `data_sources` are exposed — toggled here via `--use_truth_subset`, which injects the gold list into the per-task prompt but still leaves the full staged tree on disk) and Trimmed (gold + distractors capped at 10 files). When comparing scores against the paper, look at the Full-mode column unless `--use_truth_subset` was passed. See `REFERENCE_PERFORMANCE.md` for the per-mode SOTA numbers to beat.
