---
name: aegis-harness
description: "Operate and troubleshoot the Aegis deterministic verification-first agent harness and CLI."
---

# AegisHarness Skill Guide

This skill documents how to interact with and operate the Aegis local agent harness within Antigravity.

## Architecture Distinction
- **Antigravity Skills (`.agents/skills/`)**: Human-facing and IDE-facing instruction sets loaded by Antigravity IDE during pairing.
- **Aegis Dynamic Skills (`.aegis/skills/`)**: Runtime capabilities and progressive guidance activated dynamically by Aegis's internal orchestrator based on repository files and task keywords.

## CLI Usage

### 1. Initialize Aegis
Detects repository characteristics (Python, Node, Go, Rust), scaffolds `.aegis.yaml`, and creates VS Code task integrations:
```bash
aegis init
```

### 2. Run Verification-First Agent Tasks
Executes the Plan → Implement → Verify → Diagnose & Repair agent loop:
```bash
aegis run --task "Implement input validation on the auth endpoint"
```
Interactive approval mode (prompts before applying each write patch):
```bash
aegis run --task "Refactor database models" --interactive
```

### 3. Direct Gate Verification
Runs configured verification gates (lint, test, build) without invoking the model:
```bash
aegis verify
```

### 4. Diff Inspection
Inspects surgical changes introduced by the active or latest Aegis session:
```bash
aegis diff
```

### 5. Commit & Remember
Inspects session changes, verifies strict gates, saves an optional project lesson to episodic memory, prepares a conventional commit message, and requires human approval before committing:
```bash
# Prepare and preview commit without running git commit:
aegis commit --dry-run

# Commit validated changes with lesson:
aegis commit -m "feat: add user authentication" --lesson "Remember to validate token expiration on auth middleware"
```

### 6. Memory Management
```bash
# List persistent repository lessons
aegis memory list

# Add an approved lesson
aegis memory add --lesson "Always run pytest with -q flag" --tags "tests,pytest"
```

### 7. Background Daemon
```bash
aegis daemon start
aegis daemon status
aegis daemon stop
```

### 8. Diagnostics
```bash
aegis doctor
```
