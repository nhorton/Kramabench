---
name: run-kramabench
description: Run KramaBench evaluations via evaluate.py — env setup, workload selection, expected runtimes, result interpretation, and known gotchas (especially around the UnsupervisedSystem SUT). Invoke when the user asks to run the benchmark, smoke-test a SUT, evaluate a system against a workload, or interpret a measures CSV.
---

! pip install -r /workspaces/Kramabench/requirements-dev.txt

# Running KramaBench

The benchmark entrypoint is `evaluate.py`. It instantiates a SUT class,
calls `process_dataset` once, fans tasks across worker processes, and scores
answers against workload definitions. Results land under `results/<SUT>/`.

## Quick start

```bash
python /workspaces/Kramabench/evaluate.py \
    --sut <SUTClassName> \
    --workload <workload-name> \
    --num_workers 1 \
    --verbose 2>&1 | tee /tmp/kbench-<sut>-<workload>.log
```

For a smoke-test (fewer API calls), add `--no_pipeline_eval`.

**Workload choices:** `environment-tiny` (fastest, deterministic), `legal-tiny`,
or full domains: `archeology`, `astronomy`, `biomedical`, `environment`,
`legal`, `wildfire`.

## Run both SUTs in parallel

Each KramaBench workload should be run against **both** the `UnsupervisedSystem`
and `ClaudeCodeSystem` SUTs. The two are independent (different `results/<SUT>/`
output dirs and different status files), so launch them concurrently rather
than serially.

For a given workload, kick off both runs as separate background Bash calls in
the **same** assistant message — that schedules them to run in parallel:

```bash
# call 1 (run_in_background=true)
python /workspaces/Kramabench/evaluate.py --sut UnsupervisedSystem \
    --workload <workload> --num_workers 1 --verbose \
    2>&1 | tee /tmp/kbench-unsupervised-<workload>.log

# call 2 (run_in_background=true), in the SAME message as call 1
python /workspaces/Kramabench/evaluate.py --sut ClaudeCodeSystem \
    --workload <workload> --num_workers 1 --verbose \
    2>&1 | tee /tmp/kbench-claude-code-<workload>.log
```

When each finishes, update **its own** status file (see below) — never mix
results from the two SUTs into one file.

**For long-running jobs:** redirect to per-run log files as shown, then
`Monitor: tail -f /tmp/kbench-<sut>-<workload>.log` to watch progress.

## Reading results

1. `results/<SUT>/<workload>_measures_<timestamp>.csv` — per-task metrics
   in long form: `sut, workload, task_id, metric, value`. Headline metric
   depends on `answer_type` (exact match, approximate, score, F1, etc.).

2. `results/aggregated_results.csv` — rolled up across all runs.

3. Stdout shows `Total score is: …` at the end.

## Update the per-SUT status CSV after every run

There is one status CSV per SUT — pick the one that matches the SUT you ran:

| SUT | Status file |
|---|---|
| `UnsupervisedSystem` | `/workspaces/Kramabench/UNSUPERVISED_BENCHMARK_STATUS.csv` |
| `ClaudeCodeSystem` | `/workspaces/Kramabench/CLAUDE_CODE_BENCHMARK_STATUS.csv` |

Never write `UnsupervisedSystem` rows into the Claude Code file or vice versa.
When you run both SUTs in parallel for a workload, each finishing run updates
**only** its own file.

Columns (both files):
`sut,workload,task_id,metric,value,status,run_timestamp,measures_csv,notes`.

After a run finishes (whether `done`, `partial`, or `error`):

1. **Locate the workload's row(s)** — initially there's one `todo` placeholder
   row per `(sut, workload)` with `task_id`, `metric`, `value` empty.
2. **On success:** delete the placeholder and append one row per
   `(task_id, metric)` pair from the new
   `results/<SUT>/<workload>_measures_<timestamp>.csv`. Set `status=done`,
   `run_timestamp` to the CSV's timestamp suffix, and `measures_csv` to the
   CSV's repo-relative path.
3. **On error or no CSV produced:** keep a single row, set `status=error`
   (or `partial` if some tasks scored), and put the failure reason in `notes`.
4. **On re-run of an already-done workload:** replace its rows with rows from
   the newer CSV. Don't keep stale rows.

The CSV is the atomic source of truth — aggregates (per-domain mean success,
F1, etc.) are computed by grouping rows, never stored as columns. Don't add
summary/aggregate columns.

## Key flags

| Flag | Effect |
|---|---|
| `--use_system_cache` | Reuse SUT outputs from `response_cache/` |
| `--use_evaluation_cache` | Reuse latest CSV, skip SUT + evaluator |
| `--use_truth_subset` | Restrict to workload JSON's `data_sources` |
| `--run_subtasks` | Execute sub-tasks too |
| `--no_pipeline_eval` | Skip LLM-graded pipeline quality (saves API calls) |
| `--num_workers N` | Parallelism (default 8) |

## SUTs on this branch

- **`UnsupervisedSystem`** — uses the `unsupervised` CLI (Claude Code
  wrapper). Must be logged into Claude Code; verify with `claude --version`.
- **`ClaudeCodeSystem`** — drives Claude Code directly without the
  `unsupervised` wrapper. Same auth requirement.

Both share the picklability constraints in `benchmark/benchmark_api.py`. See
[REFERENCE.md](./REFERENCE.md) for lifecycle, constraints, expected runtimes,
and troubleshooting.

For full workload table, all flags, SUT architecture details, and known gotchas, see [REFERENCE.md](./REFERENCE.md).
