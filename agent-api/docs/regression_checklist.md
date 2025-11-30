# Animation Agent Regression Checklist

This document defines a systematic checklist to verify that recent changes to:
1. SQL persistence (uniform placeholders & metadata JSONB),
2. Axis label fallback / guards in templates,
3. Preview error classification,
4. SSE heartbeat & progress streaming,
work correctly and remain stable after future changes.

Use this before merges, releases, or after dependency upgrades.

---

## 1. Purpose

Provide a fast, repeatable sequence of validations ensuring the animation pipeline:
- Persists run state reliably.
- Handles dataset preprocessing & sampling.
- Generates previews with responsive streaming feedback.
- Classifies runtime errors intelligently (avoids futile auto-fix loops).
- Renders final video artifacts and stores them properly.

---

## 2. Scope

Covers the animation_agent end‑to‑end path:
Prompt → Intent detection → Preprocess/melt → Spec + template → Code validation → Preview (heartbeat/progress) → Runtime auto-fix (conditional) → Final render → Artifact persistence.

---

## 3. Preconditions

- Containers / services running (API + Postgres).
- Fresh virtual environment or container built with current code.
- Test dataset(s):
  - Large wide-form (e.g., life_expectancy_years.csv).
  - Small long-form dataset.
  - Corrupted / missing column dataset (to trigger classification).
- Manim CLI installed and discoverable in PATH.
- Database schema applied.

---

## 4. High-Level Checklist Categories

A. Database & Persistence  
B. Preview Pipeline (Manim)  
C. Error Classification & Auto-fix Control  
D. SSE Stream & Heartbeats  
E. Dataset Preprocessing & Sampling  
F. Rendering & Artifact Storage  
G. Performance & Timeouts  
H. Security / Stability / Restart Resilience  
I. Common Pitfalls Re-Validation  

---

## 5. Detailed Checklist

### A. Database & Persistence
- [ ] Run creation inserts use uniform placeholders (no mixed $1 and :name syntax in logs).
- [ ] No syntax error at or near ':' appears for agent_runs.
- [ ] metadata column in agent_runs stores valid JSONB (jsonb_typeof(metadata) → object).
- [ ] Artifacts rows show storage_path as string (no dict serialization leakage).
- [ ] Duplicate dataset upload with skip_duplicate returns original dataset_id (no duplicate DB row).
- [ ] Canceling a run updates state to CANCELED without orphaned artifacts.

### B. Preview Pipeline (Manim)
- [ ] Preview starts with "Generating preview..." event.
- [ ] Heartbeat events (RunHeartbeat) appear at configured interval (default 5s).
- [ ] Progress messages increment frame counts (e.g., "Preview progress: X frame(s) written...").
- [ ] No server reload mid-preview (verify absence of watcher-triggered shutdown during preview).
- [ ] Preview completes with images list and elapsed_seconds.

### C. Error Classification & Auto-fix Control
Trigger each category intentionally:
- MissingAxisLabel: Temporarily force a template to set X_LABEL = None → classified correctly, allow_llm_fix=False.
- SceneSyntax: Introduce a deliberate syntax error (unmatched parenthesis) → allow_llm_fix=True, fix attempts run.
- MissingDataColumn: Remove required value column from dataset → classification stops auto-fix.
- DataTypeIssue: Insert non-numeric strings where numeric expected → classification stops auto-fix.
- PerformanceTimeout: Lower preview_timeout_seconds artificially → classification stops auto-fix.
- UnknownRuntime: Simulate an obscure exception → one fix attempt only.

Checks:
- [ ] allow_llm_fix flag respected in preview loop.
- [ ] Error messages prefixed with [Category].
- [ ] No auto-fix attempts run for categories with allow_llm_fix=False.

### D. SSE Stream & Heartbeats
- [ ] Heartbeat events have empty content but include elapsed_seconds.
- [ ] Front-end continues updating progress (no “stuck” UI).
- [ ] Disconnection (manual restart) stops heartbeats; UI detects absence gracefully (client logic).
- [ ] RunHeartbeat does not increment auto-fix counters.

### E. Dataset Preprocessing & Sampling
- [ ] Wide-form dataset melts successfully (log: Melted wide dataset -> path ... groups/time_points stats).
- [ ] Auto-selected chart_type (e.g., distribution) after melt when chart_type was unknown.
- [ ] Provisional data binding displayed (group_col, time_col, value_col).
- [ ] Axis label fallback ensures non-empty defaults ("Value", "Count") even if spec axes missing.
- [ ] (If sampling implemented) PreviewSampleNotice event lists sampled groups/timepoints; full render still uses entire dataset.

### F. Rendering & Artifact Storage
- [ ] Render phase transitions state to RENDERING.
- [ ] Final videos persisted: artifacts row with kind=video, storage_path not empty.
- [ ] RunCompleted event emitted after video artifact persistence.
- [ ] Re-run with same dataset does not duplicate artifact entries unnecessarily (unless code differs).

### G. Performance & Timeouts
- [ ] Preview timeout produces PerformanceTimeout classification (no auto-fix loop).
- [ ] Adjusting sample_every or max_frames reduces preview duration predictably.
- [ ] Large dataset preview finishes within acceptable time with sampling enabled.
- [ ] CPU / memory usage stable (no runaway process accumulation).

### H. Security / Stability / Restart Resilience
- [ ] Intentional API container restart during idle does not corrupt ongoing dataset registry (test by listing datasets after restart).
- [ ] Long preview not interrupted by file watcher (artifact directories excluded or moved).
- [ ] No sensitive keys logged beyond allowed environment echo at startup.
- [ ] Unauthenticated run persists with user_id="local" safely.

### I. Common Pitfalls Re-Validation
- [ ] No residual mixed placeholder SQL statements in logs.
- [ ] Text(None) never appears in any scene file after template generation.
- [ ] Heartbeats never flood (interval respected; < 1 event per second).
- [ ] Auto-fix attempts capped as configured (no infinite loop).
- [ ] Work directories cleaned (no unbounded growth under artifacts/work).
- [ ] Stale preview tokens cleaned or limited (no thousands of preview-* directories accumulating).

---

## 6. Suggested Ad Hoc Test Scenarios

| Scenario | Expected Outcome |
|----------|------------------|
| Missing time column | RunError (MissingDataColumn) quickly; no fix attempts |
| Syntax error in construct | SceneSyntax classification; <= 2 auto-fix attempts; success or failure |
| Huge dataset (thousands rows) | Sampling / progress events; completion under timeout |
| Preview timeout (forced) | PerformanceTimeout classification; abort; clear message |
| Axis label None | Guard prevents AttributeError; preview renders or classification triggers MissingAxisLabel |
| Server restart mid-preview | Client detects lost heartbeats; prompts user to retry |

---

## 7. Manual SQL Verification Commands (reference)
Use psql or any DB client:
- Check latest runs:
  SELECT run_id, state, jsonb_typeof(metadata) FROM public.agent_runs ORDER BY created_at DESC LIMIT 10;
- Check artifacts:
  SELECT kind, storage_path FROM public.artifacts ORDER BY created_at DESC LIMIT 10;
- Confirm no mixed placeholder errors in recent logs.

---

## 8. Rolling Back / Recovery Steps
If classification causes unexpected aborts:
1. Temporarily disable classification (set allow_llm_fix=True unconditionally) to isolate problem source.
2. Revert preview_manim streaming wrapper (threaded section) if heartbeats misbehave.
3. Capture failing scene file for offline Manim run to differentiate template vs infrastructure issue.

---

## 9. Performance Benchmarks (Targets)
- Preview (50 sampled frames, medium dataset): < 30s.
- Heartbeat interval drift: ±1s max.
- Auto-fix cycle time (LLM round-trip): < 10s per attempt.
- Full render (medium quality, ~30s scene): < 2–3 minutes.

---

## 10. Common Pitfalls to Avoid (Expanded)
- Forgetting to propagate allow_llm_fix upstream → wasted LLM calls.
- Setting heartbeat interval too low → log/stream spam.
- Not sanitizing axis labels → regression of NoneType Text errors.
- Accidentally re-introducing mixed SQL placeholders when refactoring persistence.
- Sampling logic mutating original dataset silently (ensure preview vs full separation).
- Overlapping cleanup (deleting work dir before frame counting completes).
- Missing JSON serialization on metadata if new fields (always json.dumps before insert).
- Hardcoding run_id usage in filesystem paths without existence checks.

---

## 11. Automation Roadmap
- Add unit tests for classify_preview_error categories.
- Integration test to simulate preview timeout and verify classification.
- Snapshot test for generated distribution template ensuring label guards present.
- Periodic cleanup job test ensuring old preview-* directories pruned.

---

## 12. Sign-off Template
Before release:
- [ ] All categories A–I checked.
- [ ] At least one large-dataset preview succeeded with progress events.
- [ ] Error classification triggers verified (≥ 4 distinct categories).
- [ ] No critical warnings in logs for last 3 runs.
- [ ] Artifacts persisted and accessible via /static/.

Reviewer Name: ____________________  Date: _______________

---

End of checklist.