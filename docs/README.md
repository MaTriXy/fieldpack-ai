# FieldPack AI — Docs Index

Start here. This page is the map to every other doc in the repo. If you're a new human (or a fresh Claude session) looking for something specific, use the table below.

## Which doc when

| If you're doing… | Read… |
|---|---|
| **First-time setup (Docker, recommended)** | Repo root [`README.md`](../README.md) §"For Judges — One-Command Setup" |
| **Native dev setup on Windows** | [`QUICKSTART_POWERSHELL.md`](./QUICKSTART_POWERSHELL.md) |
| **Understanding the codebase end-to-end (as an AI or new contributor)** | Repo root [`CLAUDE.md`](../CLAUDE.md) |
| **Understanding *why* decisions were made** | [`PHILOSOPHY.md`](./PHILOSOPHY.md) |
| **Understanding *how* the system is built (architecture, stack, pipeline)** | [`TECH_FRAMEWORK.md`](./TECH_FRAMEWORK.md) |
| **Day-to-day development (env vars, APK build, provider config, code style)** | [`DEVELOPER_NOTES.md`](./DEVELOPER_NOTES.md) |
| **Debugging a specific failure (garbled output, phone can't connect, pull fails, etc.)** | [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) |
| **The writeup that ships on Kaggle** | [`KAGGLE_WRITEUP.md`](./KAGGLE_WRITEUP.md) |
| **Submission prep, video script, notebook copy** | [`archive/`](./archive/) (internal scaffolding) |

## Categories

**Onboarding (start here)**
- [`README.md`](../README.md) — project overview, Docker one-command setup, phone demo
- [`CLAUDE.md`](../CLAUDE.md) — comprehensive map of the repo for AI assistants and new contributors
- [`QUICKSTART_POWERSHELL.md`](./QUICKSTART_POWERSHELL.md) — Windows native dev setup

**Reference (how the system works)**
- [`PHILOSOPHY.md`](./PHILOSOPHY.md) — strategy, product vision, competition analysis
- [`TECH_FRAMEWORK.md`](./TECH_FRAMEWORK.md) — architecture, technology decisions, pipeline details
- [`DEVELOPER_NOTES.md`](./DEVELOPER_NOTES.md) — dev environment, APK build, config gotchas

**Operations**
- [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) — one-stop guide for common setup/runtime failures

**Submission (hackathon)**
- [`KAGGLE_WRITEUP.md`](./KAGGLE_WRITEUP.md) — the public writeup that ships on Kaggle
- Submission prep, video script, notebook-description text → [`archive/`](./archive/) (internal scaffolding, kept for history)

**Archive**
- [`archive/`](./archive/) — point-in-time working docs (audits, handoffs, punch lists). Kept for history, not read by default. See [`archive/README.md`](./archive/README.md).

## Conventions

- Dated audits / point-in-time snapshots → `archive/<NAME>_YYYY-MM-DD.md`.
- Cross-session handoff notes (written by one Claude session for the next) → `archive/` once the handoff is complete.
- Anything referenced from the root `README.md` or `CLAUDE.md` must stay at `docs/<NAME>.md` (not in a subfolder) to keep links stable.
- No emojis in doc content unless a specific doc (video script, writeup) needs them for tone.
