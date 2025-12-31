# Agent Workflow Guide

This repository uses a **Git Worktree** based workflow to allow multiple Claude Code agents (or human developers) to work on different features simultaneously without conflicts.

## Why this approach?

Standard git branches are great, but switching branches updates the working directory. This means:
1.  You can't run the app on Branch A and Branch B at the same time.
2.  Database schemas might conflict (sqlite file lock).
3.  Dependencies might differ.

By using **Worktrees**, we create a separate folder for each branch. Our custom `scripts/worktree-manager.py` enhances this by:
- **Allocating unique ports** (8001, 8002...) so multiple servers can run.
- **Isolating databases** (`data/articles-branch-name.db`) so data doesn't conflict.
- **Sharing the virtual environment** to save disk space and setup time.
- **Propagating configuration** (`.env`, `.claude/`) automatically.

## Quick Start

### 1. Create a Worktree
To start a new task:

```powershell
python scripts/worktree-manager.py create feature/my-new-task
```

This will:
1.  Create a branch `feature/my-new-task`.
2.  Create a folder `../lolstonksrss-feature-my-new-task`.
3.  Assign a port (e.g., 8001).
4.  Copy your `.env` and inject `WORKTREE_PORT=8001`.

### 2. Switch to the Worktree
```powershell
cd ../lolstonksrss-feature-my-new-task
```

### 3. Work & Run
Now you can run the app as usual. It will use its own isolated DB and port.

```powershell
uv run main.py
```

### 4. Cleanup
When the task is merged or abandoned:

```powershell
# From the main repo folder
python scripts/worktree-manager.py cleanup feature/my-new-task
```

## Security & Configuration

The `.claude` directory contains configuration for the Claude CLI.
- **Public:** `CLAUDE.md`, `.claude/settings.json` (Project defaults)
- **Private:** `.claude/settings.local.json` (Personal overrides, API keys)

The worktree manager automatically copies these to new worktrees so you (or the agent) have the same context everywhere.
