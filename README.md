<div align="center">

# ⚔ AegisHarness

**A deterministic, verification-first AI coding agent for Gemini.**  
It doesn't claim to be done. It *proves* it.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-112%20passing-22c55e)](tests/)
[![Live E2E](https://img.shields.io/badge/live%20E2E-verified-22c55e)](tests/integration/)
[![Security](https://img.shields.io/badge/security-GateGuard-f97316)](aegis/guard/)

</div>

---

## The Problem With Every Other AI Coding Agent

Every AI coding agent on the market (Cursor, Copilot, Claude Code, Aider) terminates a task when the **model says it's done**:

```
Model: "I've added the validation logic and tests. Everything looks good!"
← task marked complete, changes written, session closed
```

This is fundamentally broken. The model hallucinates correctness. Tests might fail. Files might not exist. Security violations might have gone undetected.

**Aegis refuses this paradigm entirely.**

```
MODEL SAYS SUCCESS  ≠  AEGIS SUCCESS
```

Aegis completion is a **hard application-level state transition** that requires:

```
Gate: pre_flight → PASS
Gate: lint       → PASS
Gate: test_cmd   → PASS   ← actual test runner, real exit code
Gate: build_cmd  → PASS
Security: GateGuard → NO VIOLATIONS
───────────────────────────────────────
                           ↓
                      COMPLETED ✓
```

If anything fails, Aegis **diagnoses → repairs → re-verifies** in a bounded loop. If the loop exhausts, it performs a **surgical transactional rollback** — reverting only what it touched, preserving everything else.

---

## Quickstart (60 seconds)

```bash
# 1. Clone and set up
git clone <repo-url> && cd Agehesi
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Set your Gemini API key
export GEMINI_API_KEY="your-key-here"

# 3. Initialize inside any project
cd /path/to/your/project
aegis init

# 4. Run your first agent task
aegis run --task "Add input validation to the signup endpoint and write tests for it"
```

Aegis will plan, implement, run your test suite, and only declare success when all gates pass.

---

## How It Works

### The Lifecycle

```
          ┌──────────────────────────────────────────────────────────┐
          │                    Aegis Orchestrator                     │
          │               (Typed Finite State Machine)                │
          └───────────────┬──────────────────────┬───────────────────┘
                          │                      │
              ┌───────────▼──────────┐  ┌────────▼──────────────────┐
              │  GeminiModelClient   │  │        GateGuard           │
              │  (google-genai SDK)  │  │  PathGuard · SecretGuard   │
              │  6-attempt backoff   │  │  CommandGuard · ASTScanner │
              │  503/429 resilient   │  └────────┬──────────────────┘
              └───────────┬──────────┘           │
                          ▼                      │
          ┌───────────────────────────────────────────────────────────┐
          │                         Tool Bus                          │
          │   write_patch · read_file · run_shell · run_verification  │
          │   view_tree · search_files · git_status · memory_recall   │
          └───────────────────────┬───────────────┬───────────────────┘
                                  │               │
              ┌───────────────────▼──┐  ┌─────────▼────────────────┐
              │   Execution Backend  │  │   Verification Engine     │
              │  LocalExecutor       │  │  pre_flight → lint        │
              │  DockerExecutor      │  │  test_cmd → build_cmd     │
              │  (auto-select)       │  │  (configurable gates)     │
              └──────────────────┬───┘  └─────────┬────────────────┘
                                 └───────┬─────────┘
                                         ▼
                          ┌───────────────────────────┐
                          │    Session Checkpoint      │
                          │  Surgical Rollback on Fail │
                          │  Preserves pre-existing    │
                          │  files and untracked work  │
                          └───────────────────────────┘
```

### The State Machine

```
IDLE ──► PLAN ──► IMPLEMENT ──► VERIFY ──► COMPLETED
                                   │
                                 FAIL
                                   │
                              DIAGNOSE ──► REPAIR ──► IMPLEMENT
                                   │
                          (max_repairs exceeded)
                                   │
                               ROLLBACK ──► ABORTED
```

Every arrow is a **checked transition**. The orchestrator cannot skip a state. It cannot declare success from `IMPLEMENT`. The only path to `COMPLETED` goes through a verified `VERIFY → PASS`.

---

## Installation

### Requirements

| Requirement | Version |
|---|---|
| Python | 3.12+ |
| Git | 2.0+ |
| OS | macOS or Linux |
| Docker *(optional)* | any — enables container isolation |

### Install

```bash
git clone <repo-url>
cd Agehesi
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Verify
aegis --help
```

### Install from PyPI *(when published)*

```bash
pip install aegis-harness
```

---

## CLI Reference

### `aegis init`

Initialize Aegis inside any repository:

```bash
aegis init
```

- Auto-detects project stack: **Python, Node.js, TypeScript, React, Next.js, Go, Rust**
- Generates documented `.aegis.yaml`
- Creates `.aegis/skills/` and `.aegis/traces/` directories
- Generates `.vscode/tasks.json` with IDE-ready run/verify/commit tasks

### `aegis run`

```bash
# Run a task with full verification
aegis run --task "Refactor the auth module and ensure all tests pass"

# Interactive mode — shows unified diff, requires approval before any write
aegis run --task "Migrate database schema" --interactive

# Override model for this run
GEMINI_MODEL="gemini-3.5-flash" aegis run --task "..."
```

### `aegis verify`

Run the full verification suite without invoking the LLM:

```bash
aegis verify
```

Shows each gate's exit code, duration, and captured stdout/stderr on failure.

### `aegis commit`

```bash
# Preview what would be committed (dry run)
aegis commit --dry-run

# Commit with a stored lesson for future sessions
aegis commit \
  -m "feat: add token bucket rate limiter" \
  --lesson "Rate limiters must handle zero burst; always test edge cases"
```

**Invariant**: All gates must pass before committing. Aegis **never** auto-commits — a confirmation prompt or explicit `-y` flag is always required.

### `aegis memory`

```bash
aegis memory list
aegis memory add --lesson "Always run pytest with -q flag in CI" --tags "pytest,ci"
```

### `aegis daemon`

```bash
aegis daemon start   # Unix socket (mode 0600) or TCP fallback
aegis daemon status
aegis daemon stop
```

Daemon commands: `ping`, `status`, `verify`, `run`, `cancel`, `stop`.

---

## Configuration

Aegis is configured via `.aegis.yaml` in your repository root. All fields are optional — Aegis works with zero configuration using safe defaults.

```yaml
# .aegis.yaml
version: 1

project:
  name: "my-service"
  stack: "python"          # python | node | typescript | go | rust | generic

model:
  provider: "gemini"
  model: null              # null → GEMINI_MODEL env var → gemini-3.8-flash
  temperature: 0.2

agent:
  max_turns: 24            # Hard cap on LLM turns per session
  max_repairs: 5           # Max repair attempts before rollback
  max_tool_calls: 100
  max_command_runtime_seconds: 60
  max_output_size_bytes: 100_000
  max_files_touched: 20

verification:
  pre_flight: "python3 -m py_compile src/**/*.py"   # Syntax check
  lint: "ruff check ."                               # Linter
  test_cmd: "pytest tests/ -q"                       # Required gate by default
  build_cmd: null                                    # e.g. "npm run build"
  timeout_seconds: 60
  required_gates:
    - test_cmd                                       # Must pass to reach COMPLETED

guardrails:
  deny_paths:
    - ".git/**"
    - ".env*"
    - "secrets/**"
    - "*.pem"
    - "*.key"
    - "id_rsa*"
    - ".ssh/**"
  fail_closed: true                                  # Any guard failure = blocked
  interactive_by_default: false
  blocked_commands:
    - "rm -rf /"
    - "sudo"
    - "su"
    - "mkfs"
  allow_network: false

execution:
  backend: "auto"          # auto | local | docker
  network: "none"          # none | allowlist | unrestricted
  timeout_seconds: 60

memory:
  enabled: true
  path: ".aegis/memory.json"
  top_k: 5                 # Lessons injected into each session prompt

telemetry:
  enabled: true
  path: ".aegis/traces"    # JSONL trace files per session
```

### Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Your Gemini API key. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Override active model. |
| `AEGIS_LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`. |

**Keys are never stored in files.** They are actively scrubbed from subprocess environments, logs, and telemetry traces before any output is written.

---

## Security Architecture

Aegis implements a centralized **GateGuard** pipeline that intercepts every tool call before execution.

### PathGuard

Blocks:
- Directory traversal: `../`, URL-encoded `%2e%2e`, case variants (`..%2F`)
- Symlink escapes — resolves real path before checking
- Writes to protected paths: `.git/**`, `.env*`, `secrets/**`, `*.pem`, `*.key`, `id_rsa*`, `.ssh/**`

### SecretGuard

- Strips API keys, tokens, and high-entropy credentials from subprocess environments
- Scrubs stdout, stderr, logs, and JSONL telemetry traces on output
- Detects credentials even when embedded mid-string

### CommandGuard

- Safe tokenization via `shlex` — prevents shell injection
- Blocks chaining: `&&`, `;`, `|`, `||`, `&`
- Blocks substitution: `$()`, backticks
- Blocks destructive patterns: `rm -rf /`, `mkfs`, `dd if=/dev`, fork bombs `:(){ :|:& };:`
- Blocks privilege escalation: `sudo`, `su`

### ASTRiskScanner

- Statically inspects Python patches before writing to disk
- Blocks dynamic execution: `eval()`, `exec()`, `__import__()`

### MCP Policy Proxy

The built-in MCP adapter enforces the same GateGuard pipeline on every external MCP tool call. No external MCP server can bypass Aegis policy — all parameters are inspected before dispatch, all outputs scrubbed before return.

### Execution Isolation

| Backend | Process isolation | Filesystem isolation | Network isolation |
|---|---|---|---|
| `LocalExecutor` | Process group, signals, timeout | Checked via PathGuard | Environment scrubbed |
| `DockerExecutor` | Full container | Volume mount only | `--network none` |

When Docker is unavailable, Aegis automatically falls back to `LocalExecutor` and logs the boundary clearly.

---

## Dynamic Skills

Skills are YAML files in `.aegis/skills/` that auto-activate based on repository context, task keywords, or detected stack:

```yaml
# .aegis/skills/pytest_conventions.yaml
name: "pytest_testing"
description: "Project pytest conventions"
triggers:
  files: ["test_*.py", "conftest.py"]
  keywords: ["test", "pytest", "fixture"]
  stacks: ["python"]
instructions: |
  Follow the arrange-act-assert pattern.
  Use pytest fixtures, not unittest setUp/tearDown.
  Do not mock verification gates.
  All new test modules must import from src/, not aegis/ directly.
```

Skills are loaded progressively — the agent only sees skills relevant to the current task context.

---

## Episodic Memory

Aegis maintains persistent project memory in `.aegis/memory.json`. Lessons learned from past sessions are retrieved and injected into new session prompts automatically.

```bash
aegis memory list

aegis memory add \
  --lesson "DB connection pool exhausts under load; set pool_size=10 in tests" \
  --tags "database,testing,performance"
```

**Untrusted Memory Invariant**: Memory informs the agent — it can never override security rules, path guards, or command guards. Memory is sanitized before injection to prevent prompt injection attacks.

---

## Verification Matrix

Everything in this table was verified by running the actual code against real systems. No simulations.

| Component | Status | Evidence |
|:---|:---:|:---|
| Core state machine & lifecycle | ✅ VERIFIED | `IDLE→PLAN→IMPLEMENT→VERIFY→COMPLETE/ABORT` unit tests |
| Fail-closed verification engine | ✅ VERIFIED | Gate evaluation, non-zero exits, timeouts, error snippets |
| Surgical rollback & checkpointing | ✅ VERIFIED | Reverts session changes; preserves pre-existing user files |
| Interactive diff approval | ✅ VERIFIED | Diff display + prompt before any filesystem write |
| CommandGuard & chaining | ✅ VERIFIED | `;`, `&&`, `\|\|`, `\|`, `&`, `$()`, backtick, fork bomb blocked |
| PathGuard & traversal | ✅ VERIFIED | Symlinks, nested links, `%2e%2e`, case variants blocked |
| Secret sanitization | ✅ VERIFIED | Scrubbing across stdout, stderr, logs, traces, memory |
| Episodic memory deduplication | ✅ VERIFIED | 20× dedup, prompt injection sanitization, corrupt JSON handling |
| Task cancellation & abort | ✅ VERIFIED | Threaded + daemon cancel → `ABORTED` + rollback |
| Daemon & IPC concurrency | ✅ VERIFIED | Unix socket/TCP, real task dispatch, cancel, malformed requests |
| MCP tool adapter & policy proxy | ✅ VERIFIED | Schema wrapping, GateGuard enforcement, output scrubbing |
| Antigravity workspace integration | ✅ CONFIG VERIFIED | Rules frontmatter, skill structure, VS Code tasks verified |
| Packaging & clean install | ✅ VERIFIED | Wheel built with `python -m build`, installed in clean venv |
| Live Gemini API (multi-turn) | ✅ **LIVE VERIFIED** | Real `gemini-3.5-flash` → tool calls → file creation → verify PASS |
| Live E2E success path | ✅ **LIVE VERIFIED** | Gemini → Orchestrator → `write_patch` → `run_verification` → `COMPLETED` |
| Live E2E repair loop | ✅ **LIVE VERIFIED** | Bug seeded → verify FAIL → Gemini diagnoses → patches → verify PASS → `COMPLETED` |
| 503 overload resilience | ✅ **LIVE VERIFIED** | Exponential backoff (15s base + jitter) fired, recovered, session completed |
| Live Docker container | ✅ **LIVE VERIFIED** | Container exec, volume mount, timeout, `--network none` isolation |

**112 tests** across `unit/`, `security/`, `e2e/`, and `integration/`.

---

## Running the Test Suite

```bash
source .venv/bin/activate

# All unit, security, and scenario tests — no API key needed (~3s)
pytest tests/ --ignore=tests/integration -v

# Live Gemini E2E (requires GEMINI_API_KEY, ~3 min)
GEMINI_API_KEY="..." GEMINI_MODEL="gemini-3.5-flash" \
  pytest tests/integration/test_gemini_live_e2e.py -v -s

# Security adversarial tests only
pytest tests/security/ -v

# Live Docker tests (requires Docker daemon)
pytest tests/integration/test_docker_live.py -v -s
```

---

## Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| `LocalExecutor` has no kernel-level sandboxing | Aggressive code could escape process boundary | Use `DockerExecutor` (`execution.backend: docker`) for untrusted tasks |
| Filesystem TOCTOU on local mounts | Concurrent host process could swap symlinks between PathGuard check and write | Use containerized runners in hostile environments |
| Free-tier Gemini quota (20 req/day/model) | Live sessions may hit `429 RESOURCE_EXHAUSTED` | Backoff built-in; switch models (`GEMINI_MODEL`); use paid tier for production |

---

## Project Structure

```
aegis/
├── cli.py              # Click CLI: run, verify, commit, memory, daemon, init
├── orchestrator.py     # Bounded agent loop & typed state machine
├── client.py           # GeminiModelClient + FakeModelClient (deterministic test double)
├── config.py           # Pydantic config schema + YAML loader
├── models.py           # Shared data models (TaskResult, AgentStatus, Plan, …)
├── state.py            # Finite state machine with checked transitions
├── guard/              # GateGuard: PathGuard, SecretGuard, CommandGuard, ASTRiskScanner
├── verifier/           # VerificationRunner: multi-gate evaluation engine
├── session/            # SessionCheckpoint: surgical transactional rollback
├── execution/          # LocalExecutor + DockerExecutor (auto-select)
├── tools/              # Tool registry: write_patch, read_file, run_shell, view_tree, …
├── memory/             # EpisodicMemoryManager + WorkingMemory + deduplication
├── skills/             # SkillDetector + SkillLoader (context-aware activation)
├── mcp/                # MCPToolAdapter + policy proxy
├── daemon/             # Background daemon + IPC (Unix socket / TCP)
├── diff/               # Unified diff engine for interactive approval
├── telemetry/          # TelemetryTracer: JSONL trace files per session
└── logging.py          # Structured logging with secret scrubbing

tests/
├── unit/               # Isolated component tests (no I/O, no LLM)
├── security/           # Adversarial GateGuard and guard-bypass tests
├── e2e/                # Scripted FakeModelClient scenario tests
└── integration/        # Live API + Docker tests (require external services)
```

---

## Building & Packaging

```bash
pip install build
python -m build
# → dist/aegis_harness-0.1.0-py3-none-any.whl
# → dist/aegis_harness-0.1.0.tar.gz
```

Verify the wheel installs cleanly:

```bash
python3 -m venv /tmp/aegis-test-env
source /tmp/aegis-test-env/bin/activate
pip install dist/aegis_harness-*.whl
aegis --help
```

---

## Contributing

1. Fork and clone the repository.
2. Set up: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
3. Verify baseline: `pytest tests/ --ignore=tests/integration`
4. Make your changes — new features require unit tests and must pass all security guards.
5. Open a pull request describing what changed and why.

**Do not commit failing tests. Do not weaken guards. Do not add secrets to files.**

---

## License

[MIT](LICENSE) — use freely, attribute honestly.

---

<div align="center">
<sub>Built on the principle that <em>a model claiming success is not a success.</em></sub>
</div>
