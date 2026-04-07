# Transm — Agent Instructions

## Repository Workflow

This repo uses a **fork-based contribution model** for security isolation.

- **Upstream** (TeeYum): `https://github.com/TeeYum/transm` — the canonical repo, owned by TeeYum
- **Fork** (chryst-monode): `https://github.com/chryst-monode/transm` — the working fork on the dev machine

### How commits flow

1. All work happens on the chryst-monode fork (`origin`)
2. Push feature branches to `origin`, never directly to `upstream`
3. Open PRs from `chryst-monode/transm` → `TeeYum/transm`
4. TeeYum reviews and merges — no agent can merge to upstream

### Why this exists

The dev machine (Mac Mini) runs AI agents (NanoClaw, Claude Code, experiments). Only chryst-monode credentials exist on this machine. The fork model ensures agents can propose changes but never unilaterally modify TeeYum's repos.

### Commit identity

- **Author**: chryst-monode (global git identity on this machine)
- **Co-authors**: TeeYum + Claude (auto-added by global `prepare-commit-msg` hook via `.co-authors`)
- Do NOT override the local git user.name/user.email — the global identity and hook handle everything

### Syncing with upstream

```sh
git fetch upstream
git merge upstream/main
```

## Agent Coordination Protocol

**This is mandatory for every agent session.** Follow these steps in order:

### 1. READ `agent-updates.md`
Before writing any code, read `agent-updates.md` at the repo root. Understand what other agents have changed recently, what state they left things in, and whether any work is marked WIP or blocked.

### 2. RECONCILE your plan
Compare what you intend to do against what `agent-updates.md` says. If another agent's changes overlap with your task, or the repo state doesn't match what you expected, stop and resolve the discrepancy before proceeding. Do not silently overwrite or undo another agent's work.

### 3. WRITE your intent to `agent-updates.md`
Add an entry at the top of the changelog with `State: in-progress` describing what you are about to do. Commit and push this before starting implementation. This signals to other agents that the work is claimed.

### 4. EXECUTE your plan
Do the work. Commit to a feature branch on `origin` (the chryst-monode fork), not directly to `main`.

### 5. UPDATE `agent-updates.md` with results
When done, update your entry: change `State` to `clean` (or `blocked` with reason), fill in the final list of files changed, and summarize what was actually done (not just what was planned). Commit and push.

## Project Details

- **License**: GPL-3.0 (required by pedalboard and matchering dependencies)
- **Language**: Python (planned)
- **Status**: Pre-alpha / Research Phase
