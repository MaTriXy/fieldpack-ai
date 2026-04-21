# Archive

Point-in-time working docs. Kept for history and for any Claude session that wants context on how the project got to its current state. **Not** part of the normal onboarding path — if you're new, start at [`../README.md`](../README.md).

## Contents

**Point-in-time audits and handoffs:**
- **`FINAL_SHIP_AUDIT_2026-04-21.md`** — pre-ship audit produced without modifying code. Ranked P0/P1/P2 findings with reproduction paths. Frozen at commit `2080b7d`.
- **`HANDOFF_WAVE_B2_B3.md`** — session-to-session handoff note from Wave B1 → Wave B2/B3 of the final ship phase. Written by one Claude session for the next.
- **`SHIP_PUNCH_LIST.md`** — ranked correctness/polish/distribution issues found during the 2026-04-21 audit run. Superseded as fixes land; kept to show what was considered and why.

**Submission scaffolding (internal — the shipped artifacts are on Kaggle / YouTube):**
- **`SUBMISSION_PLAYBOOK.md`** — internal playbook for producing the submission: what to build, what judges look for, sequencing. Companion to `PHILOSOPHY.md` and `TECH_FRAMEWORK.md`, but targeted at the author not the reader.
- **`VIDEO_SCRIPT.md`** — 3-minute demo video production bible. Every frame, every word. The video itself is the shipped artifact.
- **`KAGGLE_NOTEBOOK_DESCRIPTION.md`** — copy-paste source for the Kaggle notebook description field. Once pasted, the canonical copy lives on Kaggle.

## Why archive instead of delete

These docs encode *reasoning* that isn't in git history — what was considered and why, trade-offs between options, issues that were deliberately deferred. Deleting them loses that. But they're stale snapshots, so they don't belong alongside the living reference docs either.

## Rule for adding to archive

A doc belongs here once it's a snapshot of a moment (dated audit, session handoff, punch list) rather than an evergreen reference. If you find yourself about to write "as of \<date\>" at the top of a doc in `docs/`, consider putting it here instead.
