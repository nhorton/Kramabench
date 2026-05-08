# Benchmark status

Per-workload run tracker for KramaBench evaluations. The table below is the
source of truth — one row per `(sut, workload, task_id, metric)` tuple. This
matches the long-form shape of `results/<sut>/<workload>_measures_*.csv`, so
aggregate scores (per-domain mean success, F1, etc.) are computed by grouping
rows, not stored as columns.

## How to read / update

- `status` is `todo` (not yet run), `done` (measures CSV produced), `error`
  (run failed — see `notes`), or `partial` (some tasks ran, some didn't).
- A `todo` workload has a single placeholder row with `task_id`, `metric`, and
  `value` all set to `—`.
- When a run completes, **delete the placeholder** and append one row per
  `(task_id, metric)` pair from the measures CSV.
- `run_timestamp` is the timestamp suffix of the measures CSV
  (e.g. `2026-05-08_14-32-11`).
- `measures_csv` is the relative path to the CSV the row was sourced from.
- Aggregates: compute on read. `mean(value)` filtered to `metric=success` and
  `workload=archeology` gives the archeology success rate, etc.

## Status table

| sut | workload | task_id | metric | value | status | run_timestamp | measures_csv | notes |
|---|---|---|---|---|---|---|---|---|
| UnsupervisedSystem | archeology       | — | — | — | todo | — | — | — |
| UnsupervisedSystem | astronomy        | — | — | — | todo | — | — | — |
| UnsupervisedSystem | biomedical       | — | — | — | todo | — | — | — |
| UnsupervisedSystem | environment      | — | — | — | todo | — | — | — |
| UnsupervisedSystem | legal            | — | — | — | todo | — | — | — |
| UnsupervisedSystem | wildfire         | — | — | — | todo | — | — | — |
| UnsupervisedSystem | environment-tiny | — | — | — | todo | — | — | — |
| UnsupervisedSystem | legal-tiny       | — | — | — | todo | — | — | — |
