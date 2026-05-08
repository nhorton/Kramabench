# KramaBench Reference Performance

Source: Lai, Vitagliano, Zhang, et al. *KramaBench: A Benchmark for AI Systems on
Data-to-Insight Pipelines over Data Lakes.* ICLR 2026 (arXiv:2506.06541v3, 5 Mar 2026).
Local copy: `kramabench_paper.pdf` / `kramabench_paper.txt`.

All numbers are end-to-end accuracy in **percent (0–100)**, mean ± std across 3 runs
unless marked `*` (single run; high cost or model deprecated). Domains: Archeology,
Astronomy, Biomedical, Environment, Legal, Wildfire.

---

## 1. Headline numbers

- Best end-to-end accuracy on the **Full** data lake: **55.83%** — smolagents DR (single-agent), Claude-3.7-Sonnet.
- Best end-to-end accuracy on the **Oracle** input (gold files only): **62.81%** — smolagents Reflexion, Claude-3.7-Sonnet.
- Best end-to-end accuracy on **Trimmed** input (≤10 files): **58.12%** — smolagents single DR, Claude-3.7-Sonnet*.
- Online deep-research with web access on Trimmed: **52.18%** (OpenAI DR*) and **18.48%** (Gemini 2.5 Pro Agentic*).
- Best DS-Guru variant on Full: **24.98%** — DS-Guru few-shot, GPT-o3.
- Pipeline-design score (best LLM): **41.71%** — DS-Guru one-shot, GPT-o3.
- Sub-task implementation score (best LLM): **22.05%** — DS-Guru few-shot, GPT-o3.
- Human baseline on Full: **76.75%** (n=9 data-science practitioners).

Key takeaways from the paper:
- Even with Oracle retrieval the best system tops out at 62.81%, so retrieval is *not* the dominant blocker.
- Agentic control flow gains are large (smolagents DR Claude-3.7 +30.85% over best DS-Guru).
- Multi-agent (Reflexion) buys only −0.45% over single-agent DR on Full input.
- Obscured-input drop is 15–18% for top configs (up to 50.04% drop for Reflexion + Claude-3.7), suggesting parametric-knowledge leakage.

---

## 2. Benchmark composition (Table 2 / Table 16)

| Domain      | # tasks | # subtasks | % Hard | # files | # sources | Size   |
|-------------|--------:|-----------:|-------:|--------:|----------:|-------:|
| Archeology  | 12      | 71         | 50.00% | 5       | 2         | 7.5 MB |
| Astronomy   | 12      | 68         | 50.00% | 1556    | 8         | 486 MB |
| Biomedical  | 9       | 38         | 66.66% | 7       | 2         | 175 MB |
| Environment | 20      | 148        | 70.00% | 37      | 3         | 31 MB  |
| Legal       | 30      | 188        | 53.33% | 136     | 2         | 1.3 MB |
| Wildfire    | 21      | 120        | 71.42% | 23      | 7         | 1 GB   |
| **Total**   | **104** | **633**    | 60.58% | 1764    | 24        | 1.7 GB |

Hard = needs multiple files or a pipeline of >3 steps.

Answer types and metrics (Table 17): String exact (0/1 acc), String approximate
(ParaPluie 0/1), Numeric exact (0/1), Numeric approximate (1/(1+RAE)), List exact
(F1), List approximate (F1 if match >0.9). LLM-as-judge ≈84% agreement with humans.

---

## 3. Evaluation settings

Three input modes:
- **Full** — entire data lake exposed to the system's retriever.
- **Oracle** — only gold files for each task (isolates non-retrieval failures).
- **Trimmed** — gold files + random distractors, capped at 10 files (matches closed-source DR UI limits). `Oracle*` = randomly sampled 10 gold files when gold > 10.

Three automation tiers:
- End-to-end automation (primary metric).
- Pipeline design — coverage of human-curated key functionalities (LLM-judge).
- Sub-task implementation — answer accuracy on individual sub-tasks given gold subset.

Obscured inputs: data fields rewritten so a memorizing model fails but a real pipeline still works. Used to test parametric-knowledge leakage.

---

## 4. Full Input Mode — per-domain (Table 9)

Best per row in **bold**.

| System | Model | Arche | Astro | Biomed | Env | Legal | Wildfire | **Overall** |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Human baseline* | — | 58.33 | 70.00 | **100.00** | 76.90 | 86.67 | 66.20 | **76.75** |
| DS-Guru no-context | GPT-o3 | 16.67 | 0.00 | 0.10 | 5.00 | 0.00 | 14.18 | 5.87 ± 0.71 |
| DS-Guru no-context | GPT-4o | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| DS-Guru no-context | Llama-3.3-Instruct | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.59 | 0.33 ± 0.46 |
| DS-Guru no-context | Deepseek-R1 | 2.78 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.33 ± 0.46 |
| DS-Guru no-context | Qwen2.5-Coder* | 0.00 | 1.37 | 2.02 | 1.07 | 1.44 | 13.68 | 3.72 |
| DS-Guru no-context | Claude-3.5-Sonnet* | 16.67 | 1.62 | 2.87 | 1.17 | 7.33 | 13.63 | 7.45 |
| DS-Guru no-context | Claude-3.7-Sonnet | 2.78 | 3.33 | 0.00 | 0.00 | 1.11 | 4.38 | 1.88 ± 0.81 |
| DS-Guru one-shot | GPT-o3 | 19.44 | 0.00 | 0.53 | 16.11 | 10.00 | 40.01 | 16.67 ± 2.93 |
| DS-Guru one-shot | GPT-4o | 8.33 | 6.67 | 3.70 | 0.00 | 4.41 | 13.69 | 6.08 ± 1.25 |
| DS-Guru one-shot | Llama-3.3-Instruct | 16.67 | 0.00 | 0.10 | 0.00 | 0.74 | 5.97 | 3.42 ± 0.37 |
| DS-Guru one-shot | Deepseek-R1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| DS-Guru one-shot | Qwen2.5-Coder* | 0.00 | 1.36 | 2.22 | 12.59 | 1.15 | 16.48 | 6.43 |
| DS-Guru one-shot | Claude-3.5-Sonnet* | 0.00 | 4.15 | 2.15 | 6.21 | 6.68 | 34.99 | 10.85 |
| DS-Guru one-shot | Claude-3.7-Sonnet | 2.78 | 0.00 | 0.00 | 3.33 | 0.00 | 1.59 | 1.31 ± 1.22 |
| DS-Guru few-shot | GPT-o3 | 13.89 | 0.00 | 0.10 | 49.56 | 9.26 | 52.92 | **24.98 ± 1.25** |
| DS-Guru few-shot | GPT-4o | 13.89 | 3.33 | 0.00 | 0.00 | 4.84 | 25.69 | 8.67 ± 1.48 |
| DS-Guru few-shot | Llama-3.3-Instruct | 22.22 | 0.00 | 0.20 | 0.00 | 3.33 | 23.25 | 8.40 ± 1.01 |
| DS-Guru few-shot | Deepseek-R1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.59 | 0.33 ± 0.46 |
| DS-Guru few-shot | Qwen2.5-Coder* | 8.33 | 2.40 | 4.35 | 12.64 | 9.06 | 16.48 | 9.98 |
| DS-Guru few-shot | Claude-3.5-Sonnet* | 16.67 | 1.52 | 1.96 | 11.21 | 7.01 | 39.16 | 14.35 |
| DS-Guru few-shot | Claude-3.7-Sonnet | 5.56 | 0.00 | 0.00 | 15.00 | 8.89 | 10.09 | 8.29 ± 1.12 |
| smolagents DR | GPT-o3 | 33.33 | 23.33 | 37.04 | 31.33 | 17.78 | 35.23 | 28.07 ± 8.80 |
| smolagents DR | GPT-4o* | 33.33 | 0.00 | 11.11 | 35.00 | 40.00 | 38.10 | 30.77 |
| smolagents DR | Claude-3.5-Sonnet* | 33.33 | 0.00 | 22.22 | 60.00 | 46.67 | 52.38 | 41.35 |
| smolagents DR | **Claude-3.7-Sonnet** | **44.44** | **50.00** | 38.89 | **60.56** | **61.23** | 60.16 | **55.83 ± 3.41** |
| smolagents Reflexion | GPT-o3 | 30.56 | 46.67 | 29.63 | 23.89 | 26.67 | 35.04 | 30.53 ± 10.79 |
| smolagents Reflexion | Claude-3.7-Sonnet | 41.67 | 45.00 | **50.00** | 56.25 | 58.33 | **65.38** | 55.37 ± 3.36 |
| smolagents PDT | GPT-o3 | 8.33 | 0.00 | 0.00 | 1.42 | 4.51 | 22.01 | 7.57 ± 1.28 |
| smolagents PDT | Claude-3.7-Sonnet | 19.44 | 6.67 | 5.56 | 9.84 | 6.25 | 22.58 | 12.01 ± 1.03 |

---

## 5. Oracle Input Mode — per-domain (Table 10)

| System | Model | Arche | Astro | Biomed | Env | Legal | Wildfire | **Overall** |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DS-Guru no-context | GPT-o3 | 11.11 | 10.00 | 11.11 | 0.00 | 0.00 | 10.17 | 5.36 ± 1.20 |
| DS-Guru no-context | GPT-4o | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| DS-Guru no-context | Llama-3.3-Instruct | 5.56 | 0.00 | 11.11 | 0.00 | 0.00 | 1.59 | 1.96 ± 0.80 |
| DS-Guru no-context | Deepseek-R1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| DS-Guru no-context | Qwen2.5-Coder* | 10.24 | 6.74 | 7.71 | 7.14 | 1.52 | 4.53 | 6.62 |
| DS-Guru no-context | Claude-3.5-Sonnet* | 16.52 | 10.63 | 9.87 | 12.51 | 9.80 | 0.00 | 11.63 |
| DS-Guru no-context | Claude-3.7-Sonnet | 4.17 | 10.00 | 0.00 | 1.58 | 1.67 | 8.96 | 4.11 ± 0.79 |
| DS-Guru one-shot | GPT-o3 | 8.33 | 16.67 | 7.51 | 23.89 | 15.56 | 42.80 | 21.35 ± 0.84 |
| DS-Guru one-shot | GPT-4o | 11.11 | 13.33 | 5.19 | 12.33 | 6.67 | 19.85 | 11.54 ± 1.47 |
| DS-Guru one-shot | Llama-3.3-Instruct | 0.00 | 6.67 | 7.41 | 0.00 | 0.00 | 26.37 | 6.74 ± 1.49 |
| DS-Guru one-shot | Deepseek-R1 | 2.78 | 6.67 | 0.00 | 0.00 | 0.00 | 0.00 | 0.98 ± 0.80 |
| DS-Guru one-shot | Qwen2.5-Coder* | 9.72 | 11.57 | 5.37 | 15.13 | 8.96 | 13.22 | 11.26 |
| DS-Guru one-shot | Claude-3.5-Sonnet* | 17.07 | 10.24 | 9.44 | 22.27 | 11.47 | 17.93 | 15.48 |
| DS-Guru one-shot | Claude-3.7-Sonnet | 0.00 | 0.00 | 0.00 | 6.67 | 3.33 | 4.76 | 3.27 ± 1.31 |
| DS-Guru few-shot | GPT-o3 | 16.67 | 26.67 | 7.41 | 50.11 | **61.03** | 52.02 | 43.71 ± 1.94 |
| DS-Guru few-shot | GPT-4o | 13.89 | 20.00 | 3.70 | 18.44 | 37.78 | 36.67 | 26.20 ± 2.34 |
| DS-Guru few-shot | Llama-3.3-Instruct | 13.89 | 10.00 | 11.11 | 0.00 | 6.67 | 29.72 | 11.67 ± 0.65 |
| DS-Guru few-shot | Deepseek-R1 | 5.56 | 6.67 | 0.00 | 0.00 | 0.00 | 0.00 | 1.31 ± 0.46 |
| DS-Guru few-shot | Qwen2.5-Coder* | 11.83 | 14.91 | 7.51 | 18.39 | 13.70 | 18.51 | 15.15 |
| DS-Guru few-shot | Claude-3.5-Sonnet* | 16.24 | 14.02 | 14.80 | 33.83 | 26.36 | 25.02 | 24.22 |
| DS-Guru few-shot | Claude-3.7-Sonnet | 20.83 | 25.00 | 0.00 | 9.17 | 31.67 | 18.17 | 19.75 ± 3.36 |
| smolagents DR | GPT-o3 | 27.78 | 26.67 | 37.04 | 24.00 | 17.78 | 32.89 | 25.86 ± 4.57 |
| smolagents DR | GPT-4o* | 25.00 | 25.00 | 22.22 | 20.00 | 56.67 | 38.10 | 39.00 |
| smolagents DR | Claude-3.5-Sonnet* | 16.67 | 25.00 | 33.33 | 25.00 | 66.66 | 66.66 | 47.00 |
| smolagents DR | Claude-3.7-Sonnet | **45.83** | **65.00** | 58.33 | 46.83 | 65.00 | **75.08** | 60.67 ± 1.23 |
| smolagents Reflexion | GPT-o3 | 30.56 | 40.00 | 44.44 | 31.44 | 22.22 | 39.78 | 32.33 ± 4.44 |
| smolagents Reflexion | **Claude-3.7-Sonnet** | 37.50 | 50.00 | **83.33** | **62.67** | 70.00 | 64.45 | **62.81 ± 3.10** |
| smolagents PDT | GPT-o3 | 8.33 | 0.00 | 0.00 | 3.26 | 8.62 | 15.86 | 7.69 ± 2.69 |
| smolagents PDT | Claude-3.7-Sonnet | 16.67 | 10.00 | 11.11 | 11.50 | 9.24 | 25.50 | 14.38 ± 2.15 |

Oracle vs Full deltas: DS-Guru gains average +6.38% (up to +18.73%) when given gold
files. smolagents DR Claude-3.7 gains only +4.84% — agentic retrieval already
finds most of the right files.

---

## 6. Trimmed Input Mode (≤10 files) — per-domain (Table 11)

`*` indicates web browsing on. All scores single-run (std = 0).

| System | Model | Arche | Astro | Biomed | Env | Legal | Wildfire | **Overall** | Mean min/task |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DS-Guru few-shot | GPT-o3 | 25.00 | 0.00 | 3.70 | 48.33 | 51.11 | 48.87 | 37.84 ± 3.90 | 3.81 |
| smolagents single DR | Claude-3.7-Sonnet* | **50.00** | **80.00** | 55.56 | 40.83 | 60.00 | 67.24 | **58.12** | 4.81 |
| smolagents Reflexion | Claude-3.7-Sonnet* | 33.33 | 50.00 | **66.67** | 43.33 | 55.54 | 64.44 | 52.81 | 9.70 |
| smolagents PDT | Claude-3.7-Sonnet* | 16.67 | 0.00 | 0.00 | 14.37 | 13.33 | 0.00 | 8.70 | 8.24 |
| OpenAI DR (web on) | — | 40.00 | 33.33 | 44.45 | **61.67** | 50.00 | **67.28** | 52.18 | 10.35 |
| Gemini 2.5 Pro Agentic (web on) | — | 25.00 | 16.67 | 33.33 | 25.00 | 13.33 | 24.87 | 18.48 | 2.48 |

Note: under Trimmed, Astronomy jumps to 80% for smolagents single DR — likely
because the gold files are pre-selected, sidestepping the proprietary scientific
formats that broke retrieval on Full.

---

## 7. Lower automation: pipeline design and sub-task implementation (Table 8, Full input)

DS-Guru variants × four LLMs.

| Variant | Setting | GPT-o3 | GPT-4o | Llama3-Instruct | DeepSeek-R1 |
|---|---|---:|---:|---:|---:|
| no-context | End-to-end          | 5.87 ± 0.71 | 0.00 | 0.33 ± 0.46 | 0.33 ± 0.46 |
| no-context | Pipeline Design     | 39.75 ± 0.73 | 29.73 ± 1.16 | 21.80 ± 1.30 | 0.63 ± 0.47 |
| no-context | Sub-task Implement. | 10.69 ± 0.35 | 3.32 ± 0.54 | 3.88 ± 0.25 | 1.48 ± 0.08 |
| one-shot | End-to-end            | 16.67 ± 2.93 | 6.08 ± 1.25 | 3.42 ± 0.37 | 0.00 |
| one-shot | Pipeline Design       | **41.71 ± 1.00** | 21.26 ± 0.64 | 15.53 ± 0.73 | 1.59 ± 0.77 |
| one-shot | Sub-task Implement.   | 17.33 ± 0.48 | 5.08 ± 0.57 | 2.80 ± 0.08 | 3.91 ± 0.44 |
| few-shot | End-to-end            | **24.98 ± 1.25** | 8.67 ± 1.48 | 8.40 ± 1.01 | 0.33 ± 0.46 |
| few-shot | Pipeline Design       | 37.99 ± 2.64 | 20.31 ± 0.07 | 12.81 ± 1.04 | 1.11 ± 0.72 |
| few-shot | Sub-task Implement.   | **22.05 ± 0.71** | 6.60 ± 0.29 | 5.53 ± 0.49 | 5.79 ± 0.72 |

Observations:
- LLMs identify up to **41.71%** of important data tasks (pipeline design) but fully implement only **22.05%** of individual data tasks.
- GPT-o3 is strong at pipeline design (39.75% even no-context) but weak at implementation.
- DeepSeek-R1 shows the inverse pattern: ~1% pipeline design vs 5.79% implementation.

---

## 8. Obscured input — knowledge-leakage probe (Table 7)

Full input vs the same task with renamed/obscured fields.

| System | Model | Full | Oracle | Obscured |
|---|---|---:|---:|---:|
| DS-Guru no-context | GPT-o3 | 5.87 ± 0.71 | 5.36 ± 1.20 | 3.69 ± 1.63 |
| DS-Guru no-context | Claude-3.7 | 1.88 ± 0.81 | 4.11 ± 0.79 | 0.00 |
| DS-Guru one-shot | GPT-o3 | 16.67 ± 2.93 | 21.35 ± 0.84 | 7.85 ± 1.27 |
| DS-Guru one-shot | Claude-3.7 | 1.31 ± 1.22 | 3.27 ± 1.31 | 0.50 ± 0.50 |
| DS-Guru few-shot | GPT-o3 | 24.98 ± 1.25 | 43.71 ± 1.94 | 23.02 ± 0.49 |
| DS-Guru few-shot | Claude-3.7 | 8.29 ± 1.12 | 19.75 ± 3.36 | 3.80 ± 3.80 |
| smolagents DR | GPT-o3 | 28.07 ± 8.80 | 25.86 ± 4.57 | 10.07 ± 0.30 |
| smolagents DR | Claude-3.7 | 55.83 ± 3.41 | 60.67 ± 1.23 | 12.77 |
| smolagents Reflexion | GPT-o3 | 30.53 ± 10.79 | 32.33 ± 4.44 | 9.52 ± 3.95 |
| smolagents Reflexion | Claude-3.7 | 55.37 ± 3.36 | 62.81 ± 3.10 | 13.94 |
| smolagents PDT | GPT-o3 | 7.57 ± 1.28 | 7.69 ± 2.69 | 3.87 ± 3.52 |
| smolagents PDT | Claude-3.7 | 12.01 ± 1.03 | 14.38 ± 2.15 | 2.23 |

Largest fluctuation: smolagents Reflexion + Claude-3.7 drops 62.81 → 13.94 on
obscured Oracle (−48.87%), confirming heavy reliance on parametric knowledge in
that config. GPT-o3 is much more robust (drop of 21–24% on top configs vs
50%+ for Claude-3.7).

---

## 9. Cost / runtime tradeoff — Full input (Table 12)

| SUT | Accuracy | Total runtime | Acc/runtime | Acc/1k in-tok | Acc/1k out-tok |
|---|---:|---:|---:|---:|---:|
| GPT-o3 — Naive (no-context)       | 5.87 ± 0.71  | 1h 01m 41s | 0.17 ± 0.02 | 4.73 ± 0.51 | 2.69 ± 0.31 |
| GPT-o3 — One Shot                 | 16.67 ± 2.93 | 1h 11m 26s | 0.42 ± 0.12 | 0.43 ± 0.07 | 9.16 ± 1.63 |
| GPT-o3 — Few Shot                 | 24.98 ± 1.25 | 2h 30m 42s | 0.31 ± 0.07 | 0.29 ± 0.05 | 8.58 ± 0.61 |
| GPT-4o — Naive                    | 0.00         | 38m 42s    | 0.00        | 0.00        | 0.00        |
| GPT-4o — One Shot                 | 6.08 ± 1.25  | 39m 15s    | 0.27 ± 0.06 | 0.45 ± 0.09 | 9.81 ± 2.06 |
| GPT-4o — Few Shot                 | 8.67 ± 1.48  | 1h 13m 13s | 0.22 ± 0.05 | 0.26 ± 0.03 | 7.68 ± 1.33 |
| Llama3-Instruct — Naive           | 0.33 ± 0.46  | 35m 09s    | 0.01 ± 0.02 | 0.26 ± 0.37 | 0.37 ± 0.52 |
| Llama3-Instruct — One Shot        | 3.42 ± 0.37  | 1h 38m 51s | 0.06 ± 0.01 | 0.25 ± 0.03 | 5.63 ± 0.61 |
| Llama3-Instruct — Few Shot        | 8.40 ± 1.01  | 2h 10m 11s | 0.12 ± 0.03 | 0.27 ± 0.04 | 8.98 ± 1.20 |
| DeepSeek-R1 — Naive               | 0.33 ± 0.46  | 1h 36m 29s | 0.01 ± 0.01 | 0.26 ± 0.37 | 0.16 ± 0.23 |
| DeepSeek-R1 — One Shot            | 0.00         | 1h 46m 09s | 0.00        | 0.00        | 0.00        |
| DeepSeek-R1 — Few Shot            | 0.33 ± 0.46  | 1h 56m 18s | 0.01 ± 0.01 | 0.01 ± 0.01 | 0.15 ± 0.22 |

Per-task wall time (min): smolagents DR Claude-3.7 ~6.10; OpenAI DR ~10.35;
DS-Guru few-shot ~0.76 (>10× faster than smolagents DR).

Eval cost (DS-Guru few-shot, GPT-o3): 4,501 / 116,805 / 10,358 tokens for
end-to-end / pipeline-design / sub-task evaluations respectively.

---

## 10. DS-Guru hyperparameter ablations (GPT-o3, Tables 13–15)

Iterations (max retries, fixed 5 sampled rows):

| Iterations | 5 | 10 | 15 | 20 |
|---|---:|---:|---:|---:|
| Overall | 23.36 | 22.83 | 20.73 | 21.33 |
| Tokens/iter (mean) | 64,549 | 72,926 | 70,845 | 72,302 |

Sampled rows per file (Table 14):

| Rows | Arche | Astro | Biomed | Env | Legal | Wildfire | Overall | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 10  | 18.75 | 12.80 | 8.63 | 34.52 | 13.32 | 37.42 | 22.89 | 732.45 |
| 50  | 23.48 | 10.55 | 7.87 | 37.60 | 14.08 | 40.63 | 24.68 | 655.61 |
| 100 | 20.61 | 11.95 | 8.53 | 34.84 | 12.20 | 40.60 | 23.36 | 1374.82 |
| 150 | 21.08 | 10.58 | 8.64 | 31.68 | 13.09 | 39.22 | 22.58 | 802.90 |

Drop at 100+ rows: prompt overflows context, OPS sampler falls back to no
data snippet.

Tries (Table 15):

| Tries | Arche | Astro | Biomed | Env | Legal | Wildfire | Overall | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5  | 20.61 | 11.95 | 8.53 | 34.84 | 12.20 | 40.60 | 23.36 | 1374.82 |
| 10 | 19.86 | 11.60 | 8.71 | 36.66 | 10.79 | 37.86 | 22.83 | 575.88 |
| 15 | 20.47 | 7.00  | 8.72 | 36.84 | 9.51  | 31.47 | 20.73 | 721.95 |

Take-away: more retries doesn't help — single-agent loops get stuck instead
of debugging deeper problems.

---

## 11. Human baseline (Appendix F)

- 9 data-science practitioners, same conditions as LLM SUTs, Full input.
- **Overall: 76.75%**, per-domain Arche 58.33 / Astro 70.00 / Biomed 100.00 / Env 76.90 / Legal 86.67 / Wildfire 66.20.
- Failure breakdown across all human solutions:
  - Incorrect pipeline design: **46%** (largest category — joins, aggregation rules, grouping/filtering).
  - Lack of domain knowledge: **24%**.
  - Wrong inputs (file selection): **12%**.
  - Wrong answer format/units/rounding: **9%**.
  - Library/version issues: **9%**.
- Headline: ~46% of human errors are pipeline-design errors, mirroring the dominant LLM failure mode.

---

## 12. Per-domain failure analysis (Appendix D.1, smolagents-Reflexion)

Reported per-domain accuracy from this analysis (slightly different from Table 9 because traces were re-scored):

1. **Archeology — 33.33%**: solves single-table questions; fails on cross-file joins because it treats files as raw text rather than tables.
2. **Astronomy — 16.67%** (lowest): hits proprietary scientific formats (FORTRAN-style `.dat`, SP3 orbits, satellite products) and can't load them.
3. **Biomedical — 44.44%**: single-sheet ops fine; fails to navigate multi-sheet workbooks. Cross-sheet clinical × phosphoproteomics joins, sign errors in correlation stats.
4. **Environment — 60.00%**: clean CSVs do well; remaining errors are arithmetic (incorrect aggregation scope, rounding).
5. **Legal — 63.33%**: simple pipelines fine; messy headers / multi-row metadata / partial subtotals cause incorrect loading and wrong sums/aggregates.
6. **Wildfire — 52.38%**: struggles with geospatial data — GeoPackage layers, spatial joins, rolling-window aggregations. Text lookups OK.

Cross-domain spread of best system: **41.67% (Archeology) to 65.38% (Wildfire)** — primary source is the differing data-task challenges per domain, not raw difficulty.

Failure-to-ask-clarification (Cemri et al. 2025 framework, DS-Guru few-shot):
- GPT-o3: 24% of 104 tasks fail this way.
- Claude 3.5: 43%.

---

## 13. Quick reference — what to compare a new SUT against

If the SUT runs the **Full** data lake with **no web access**:
- Beat 1.88% (Claude-3.7 no-context) → barely competitive with weakest LLMs.
- Beat 24.98% (DS-Guru few-shot GPT-o3) → competitive with the structured baseline.
- Beat 55.83% (smolagents DR Claude-3.7) → state-of-the-art on Full.
- Beat 76.75% → exceeds the human baseline.

If the SUT runs the **Oracle** mode:
- 62.81% (smolagents Reflexion Claude-3.7) is the SOTA ceiling.

If the SUT runs **Trimmed** with web access:
- 58.12% (smolagents single DR Claude-3.7) without web; 52.18% (OpenAI DR) with web.

Per-domain SOTA (Full, best of any system):
Arche 44.44, Astro 50.00, Biomed 50.00, Env 60.56, Legal 61.23, Wildfire 65.38.

Per-domain SOTA (Oracle, best of any system):
Arche 45.83, Astro 65.00, Biomed 83.33, Env 62.67, Legal 70.00, Wildfire 75.08.
