# KramaBench Reference

## Workload selection

| Workload | Tasks | Use for |
|---|---|---|
| `legal-tiny` | 1 | Smoke-test on legal data |
| `environment-tiny` | 1 | Cheapest smoke (deterministic scoring) |
| `archeology` | 9–30 | Real evaluation |
| `astronomy` | 9–30 | Real evaluation |
| `biomedical` | 9–30 | Real evaluation |
| `environment` | 9–30 | Real evaluation |
| `legal` | 9–30 | Real evaluation |
| `wildfire` | 9–30 | Real evaluation |

Tiny workloads share the full domain's `data/<domain>/input/` directory.

## All evaluate.py flags

| Flag | Effect |
|---|---|
| `--use_system_cache` | Reuse SUT outputs from `results/<SUT>/response_cache/` |
| `--use_evaluation_cache` | Reuse latest `<workload>_measures_*.csv`, skip both SUT and evaluator |
| `--use_truth_subset` | Restrict each task's input to workload JSON's `data_sources` |
| `--run_subtasks` | Execute and evaluate sub-tasks too |
| `--no_pipeline_eval` | Skip LLM-graded pipeline quality review (saves API calls) |
| `--num_workers N` | Parallelism (default 8) |

## UnsupervisedSystem SUT lifecycle

Source: `systems/unsupervised/unsupervised_system.py`.

### process_dataset (once per run)
- Derives `domain` from path (`data/<x>/input` → `<x>`, `data/<x>/tiny` → `<x>-tiny`)
- Builds/reuses `../unsup-areas/<domain>/` peer directory
- Runs `unsupervised install <area_dir>`
- Copies data to `<area>/datasources/local_files/<domain>/`
- Catalogs files into `datasources/local_files/<domain>/catalog/tables/*.md`
- All gated by `<area_dir>/.kramabench.json` manifest — re-runs skip setup

### serve_query (per task per worker)
- Spawns `unsupervised -p <prompt> --output-format json --no-session-persistence --permission-mode bypassPermissions --max-budget-usd 20.0`
- Tells analyst to write final pipeline to `outputs/<task_id>/pipeline.md`
- Captures answer from JSON, tokens from usage metadata, pipeline from files
- On timeout/error/budget-cap: returns empty answer + writes `error.txt`

### Constraints
- **Use `--num_workers 1`**. Multiple workers serialize via `fcntl` filelock anyway.
- **Budget per task is $20 USD** by default. Override via `UnsupervisedSystem(max_budget_usd=…)`.
- Per-task scratch: `system_scratch/UnsupervisedSystem/<task_id>/` contains
  `prompt.txt`, `run.stdout.txt`, `run.stderr.txt`, `pipeline.md`, and on
  failure `error.txt`.

## Expected runtimes

For `UnsupervisedSystem`:
- **First task on a domain:** 5–10 min (install + connect-datasource)
- **Subsequent tasks (same domain):** 30s–6 min each
- **Connect step:** amortized via `<area_dir>/.kramabench.json` manifest

## Known gotchas

1. **`pip install -e ".[all]"` does NOT work.** setuptools fails on flat layout.
   Always use `requirements-dev.txt`.

2. **Tiny variants don't have a tiny data dir.** `data/<x>/tiny/` is never
   read; only the workload JSON is smaller.

3. **Evaluator constructs `GPTInterface` even with `--no_pipeline_eval`.**
   `OPENAI_API_KEY` must at least exist (dummy is fine if no LLM metrics fire).

4. **SUT must be picklable.** `benchmark.py` deepcopies once per worker.
   No live subprocess handles or unpicklable clients as instance attrs.

5. **Connect step is the long pole.** First run on fresh domain takes ~5 min.
   Subsequent runs skip via manifest.

6. **`unsupervised` CLI auth.** Uses logged-in Claude Code on the local
   machine. No `ANTHROPIC_API_KEY` needed if logged in; verify with
   `claude --version`. If not logged in, set `ANTHROPIC_API_KEY`.

## Running long jobs

Use background + Monitor instead of foreground:

```
Bash(run_in_background=true): the evaluate.py command, redirected to /tmp/kbench-run.log
Monitor: tail -f /tmp/kbench-run.log | grep -E --line-buffered \\
    "Starting benchmark|Processing time|Worker [0-9]|task_id:|metric|Total score|Error|Traceback|TimeoutExpired|budget"
```

Don't use `tail -f | grep -m 1` — it'll hang if the log goes quiet. Look for
"Total score is:" as the natural finish signal; exit code 0 from background
task is a separate confirmation.

## Reading metrics CSV

Headline metric depends on `answer_type`:

| answer_type | headline metric | passing means |
|---|---|---|
| `numeric_exact` | `success` | value == 1.0 |
| `numeric_approximate` | `mean_absolute_error` / `rae_score` | smaller = better |
| `string_exact` | `success` | exact-match |
| `string_approximate` | `llm_paraphrase` | LLM-judged binary |
| `list_exact` | `f1` / `precision` / `recall` | 1.0 = perfect |
| `list_approximate` | `f1_approximate` | 1.0 = perfect |

## Adding a new SUT

1. Subclass `benchmark.benchmark_api.System`
2. Implement `process_dataset(dataset_directory)` — must set
   `self.dataset_directory`
3. Implement `serve_query(query, query_id, subset_files) -> dict` — return
   `{"explanation": {"answer": ...}, "pipeline_code": str, "token_usage": int (optional)}`
4. Re-export from `systems/__init__.py` so `getattr(systems, name)` finds it
5. Mock-test against the contract (see `tests/test_unsupervised_system.py`)
