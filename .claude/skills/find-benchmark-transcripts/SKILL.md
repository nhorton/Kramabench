---
name: find-benchmark-transcripts
description: Locate Claude Code session artifacts on disk for UnsupervisedSystem benchmark runs — run via Explore subagent for speed and low token cost.
---

# Find Benchmark Transcripts

> **WARNING: Full transcripts are suppressed.**
> `UnsupervisedSystem` passes `--no-session-persistence` to every
> `unsupervised -p` invocation (see
> `systems/unsupervised/unsupervised_system.py` line 159).
> This flag prevents Claude Code from writing the `*.jsonl` conversation
> transcript it normally keeps under `~/.claude/projects/`. Full turn-by-turn
> transcripts DO NOT exist on disk for these sessions.
>
> What **is** still recoverable is listed below.

---

## Where to look

| Location | What survives | Notes |
|---|---|---|
| `~/.cache/claude-cli-nodejs/-<mangled-cwd>/mcp-logs-*/` | MCP server logs — `<ISO-ts>.jsonl` per session, a few KB each | **Richest surviving artifact.** Contains session id + cwd on first line. |
| `/tmp/claude-1000/-<mangled-cwd>/<session-uuid>/tasks/` | Empty-but-named session directories | Confirms session ids and approximate timing (dir mtime). |
| `/workspaces/Kramabench/system_scratch/UnsupervisedSystem/<task_id>/` | `prompt.txt`, `run.stdout.txt`, `run.stderr.txt`, `pipeline.md`, `error.txt` | Written by our SUT, not Claude Code. Most useful for debugging. |
| `/workspaces/unsup-areas/<domain>/outputs/<task_id>/pipeline.md` | Final pipeline markdown written by the analyst | Written by the Claude Code session into the area dir. |
| `/workspaces/unsup-areas/<domain>/queries/adhoc/<task_id>/` | Intermediate query files | Also written by the session into the area dir. |
| `~/.claude/projects/` | Nothing (confirm absence) | `--no-session-persistence` suppresses JSONL here. |

---

## Path mangling rule

Claude Code derives a directory name from the working directory by replacing
every `/` with `-`. The leading `/` becomes a leading `-`.

Example: cwd `/workspaces/unsup-areas/environment`
→ directory name `-workspaces-unsup-areas-environment`

So the MCP log root for domain `legal` is:
`~/.cache/claude-cli-nodejs/-workspaces-unsup-areas-legal/`

And the tmp session dir root is:
`/tmp/claude-1000/-workspaces-unsup-areas-legal/`

---

## How to find them fast

Use these shell snippets. Replace `<DOMAIN>` with the benchmark domain
(e.g. `environment`, `legal`, `astronomy`).

**1. Find recent MCP logs (best signal):**
```bash
find ~/.cache/claude-cli-nodejs -name '*.jsonl' -newer /tmp/kbench-run.log 2>/dev/null | sort
```
If no marker file exists, use a timestamp approach:
```bash
find ~/.cache/claude-cli-nodejs -name '*.jsonl' -mmin -120 2>/dev/null | sort
```

**2. Browse all MCP log dirs for a specific domain:**
```bash
ls -la ~/.cache/claude-cli-nodejs/-workspaces-unsup-areas-<DOMAIN>/ 2>/dev/null
```

**3. Check tmp session dirs (session uuid directories):**
```bash
ls -la /tmp/claude-1000/-workspaces-unsup-areas-<DOMAIN>/ 2>/dev/null
```

**4. Confirm absence of full transcripts in ~/.claude/projects:**
```bash
find ~/.claude/projects -name '*.jsonl' -mmin -120 2>/dev/null | wc -l
# Expect 0 when --no-session-persistence is active
```

**5. Gather all per-task SUT scratch for a domain run:**
```bash
ls /workspaces/Kramabench/system_scratch/UnsupervisedSystem/ 2>/dev/null
```

**6. Read the first line of an MCP log to confirm session id + cwd:**
```bash
head -c 512 ~/.cache/claude-cli-nodejs/-workspaces-unsup-areas-<DOMAIN>/mcp-logs-deepwork/<ISO-ts>.jsonl
```

**7. Find area-dir pipeline outputs:**
```bash
find /workspaces/unsup-areas/<DOMAIN>/outputs -name 'pipeline.md' 2>/dev/null | sort
find /workspaces/unsup-areas/<DOMAIN>/queries/adhoc -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort
```

---

## Reporting format

Return absolute paths grouped by session (one session = one benchmark task
invocation). For each session report:

- Session id (from MCP log first line or `/tmp/claude-1000/` directory name)
- Domain and task id (infer from cwd / path)
- MCP log files: absolute path, size, mtime
- Tmp session dir: absolute path, mtime
- SUT scratch dir: absolute path and which files are present
- Area-dir outputs: pipeline.md and adhoc query paths if present

Keep the report under 250 words. Omit sessions that have no surviving
artifacts at all. If `~/.claude/projects/` is empty (as expected), state that
once and do not repeat it per session.

---

## How to invoke this skill

This skill should be executed by spawning an **Explore subagent**, not the
main session, to keep token costs low. Use the Agent tool with
`subagent_type: "explore"`.

Prompt template to pass to the subagent:

```
You are finding Claude Code session artifacts for a recent KramaBench
UnsupervisedSystem run on domain "<DOMAIN>".

NOTE: --no-session-persistence suppresses full *.jsonl transcripts under
~/.claude/projects/. Full transcripts do NOT exist. Focus on:
  - MCP logs under ~/.cache/claude-cli-nodejs/-workspaces-unsup-areas-<DOMAIN>/
  - Session dirs under /tmp/claude-1000/-workspaces-unsup-areas-<DOMAIN>/
  - Per-task SUT scratch under /workspaces/Kramabench/system_scratch/UnsupervisedSystem/
  - Area-dir outputs under /workspaces/unsup-areas/<DOMAIN>/outputs/ and queries/adhoc/

Path mangling rule: replace each '/' with '-' (leading '/' → '-').

Run these commands (replace <DOMAIN> with the actual domain):
  find ~/.cache/claude-cli-nodejs -name '*.jsonl' -mmin -120 2>/dev/null | sort
  ls -la /tmp/claude-1000/-workspaces-unsup-areas-<DOMAIN>/ 2>/dev/null
  ls /workspaces/Kramabench/system_scratch/UnsupervisedSystem/ 2>/dev/null
  find /workspaces/unsup-areas/<DOMAIN>/outputs -name 'pipeline.md' 2>/dev/null | sort

Report absolute paths grouped by session (session id, domain, task id, file
sizes and mtimes). Keep report under 250 words.
```
