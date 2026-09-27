# AegisHarness (Aegis)

A deterministic, verification-first local coding-agent harness for Gemini and Antigravity.

---

## 1. What Aegis Is

**AegisHarness (Aegis)** is a local coding-agent runtime built on the principle of **fail-closed verification**. 

Traditional AI coding assistants rely on fragile natural-language claims (e.g. model outputting `"I am done!"`) to conclude work. Aegis rejects this paradigm:
```
MODEL SAYS SUCCESS ≠ AEGIS SUCCESS
```

In Aegis, completion is an application-level state transition requiring:
$$\text{Pass Required Gates} + \text{No Policy Violations} + \text{Zero Active Errors} = \mathbf{COMPLETED}$$

If a verification gate fails or the agent loops without solving the problem, Aegis performs a **surgical transactional rollback**, reverting only the files touched during that session while preserving all pre-existing user modifications and untracked files.

---

## 2. Architecture

```text
                                  +-----------------------------+
                                  |         User / CLI          |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |      Aegis Orchestrator     |
                                  |     (Typed State Machine)   |
                                  +-------+--------------+------+
                                          |              |
                      +-------------------+              +--------------------+
                      v                                                       v
+---------------------------------------+                   +-----------------------------------+
|              Model Client             |                   |             GateGuard             |
|  (Gemini 2.5 / Scriptable Test Fake)  |                   | (Path, Secret, Command, AST)      |
+---------------------------------------+                   +-----------------+-----------------+
                      |                                                       |
                      +-------------------+              +--------------------+
                                          v              v
                                  +-----------------------------+
                                  |           Tool Bus          |
                                  | (fs, shell, git, mem, ver)  |
                                  +--------------+--------------+
                                                 |
                       +-------------------------+-------------------------+
                       v                                                   v
+-----------------------------------------------+   +-----------------------------------------------+
|               Execution Backend               |   |              Verification Engine              |
|        (Local Process Group / Docker)         |   |         (Pre-flight, Lint, Test, Build)       |
+-----------------------------------------------+   +-----------------------------------------------+
                       |                                                   |
                       +-------------------------+-------------------------+
                                                 v
                                  +-----------------------------+
                                  |      Session Checkpoint     |
                                  | (Surgical Transaction Backup|
                                  |   & Fail-Closed Rollback)   |
                                  +-----------------------------+
```

### Core Lifecycle States
```text
IDLE → PLAN → IMPLEMENT → VERIFY → PASS → COMPLETE
                               ↓
                              FAIL → DIAGNOSE → REPAIR → IMPLEMENT
```

---

## 3. Installation

### Requirements
- Python 3.12+
- Git 2.0+
- macOS or Linux

### Install in Virtual Environment
```bash
# Clone or navigate to repository
cd /path/to/repo

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Aegis in editable mode
pip install -e .
```

Verify installation:
```bash
aegis --help
```

---

## 4. `aegis init`

Initialize Aegis inside any repository:
```bash
aegis init
```

The initializer:
1. Automatically detects project stack (Python, Node, React, Next.js, TypeScript, Go, Rust).
2. Generates documented `.aegis.yaml`.
3. Creates `.aegis/skills/` and `.aegis/traces/`.
4. Creates `.vscode/tasks.json` with ready-to-run IDE tasks.

---

## 5. API Key Configuration

Aegis uses the modern `google-genai` SDK. Configure your key via environment variable:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

Optional model override:
```bash
export GEMINI_MODEL="gemini-2.5-flash"
export AEGIS_LOG_LEVEL="INFO"
```

API keys are **never** stored in repository files and are actively scrubbed from child process environments, logs, and telemetry traces.

---

## 6. First Agent Task

Run a task with full verification:
```bash
aegis run --task "Add input validation to the API endpoints and write tests"
```

Interactive mode (shows unified diff and prompts for confirmation before writing):
```bash
aegis run --task "Refactor authentication flow" --interactive
```

---

## 7. Verification Loop

The verification engine runs configured gates in order:
- `pre_flight`: Initial syntax checks (e.g. `python3 -m py_compile`)
- `lint`: Code quality (e.g. `ruff check .` or `npm run lint`)
- `test_cmd`: Automated tests (e.g. `pytest tests/ -q` or `npm test`)
- `build_cmd`: Build validation (e.g. `npm run build` or `cargo check`)

Run verification manually at any time without calling LLM:
```bash
aegis verify
```

---

## 8. Memory System

Aegis maintains two tiers of memory:
1. **Working Memory**: In-memory ephemeral session state (turn count, touched files, repair attempts).
2. **Episodic Memory (`.aegis/memory.json`)**: Persistent repository lessons.

### Untrusted Memory Invariant
Persisted memory is strictly treated as **untrusted data**. Memory may inform the agent but can never override security rules or execute arbitrary instructions.

Manage memory:
```bash
# List lessons
aegis memory list

# Add lesson manually
aegis memory add --lesson "Always run pytest with -q flag" --tags "pytest,tests"
```

---

## 9. Dynamic Skills

Skills live in `.aegis/skills/*.yaml`. They are loaded progressively when repository files or task keywords trigger them:
```yaml
name: "pytest_testing"
description: "Pytest conventions"
triggers:
  files: ["test_*.py"]
  keywords: ["test", "pytest"]
  stacks: ["python"]
instructions: |
  Follow arrange-act-assert pattern.
  Do not mock verification gates.
```

---

## 10. Guardrails & Security

Aegis implements a centralized **GateGuard** pipeline:
1. **PathGuard**: Blocks directory traversal (`../`) and protects sensitive paths (`.git/**`, `.env*`, `secrets/**`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`).
2. **SecretGuard**: Sanitizes subprocess environments, strips API keys, and detects high-entropy credentials.
3. **CommandGuard**: Safe tokenization (`shlex`), blocks destructive commands (`rm -rf /`, `mkfs`, fork bombs), and blocks privilege escalation (`sudo`, `su`).
4. **ASTRiskScanner**: Static inspection of Python files for dynamic code execution (`eval`, `exec`, `__import__`).

---

## 11. Daemon & IPC

Run Aegis as a background daemon communicating via Unix domain sockets (mode `0600`):
```bash
# Start background daemon
aegis daemon start

# Check status
aegis daemon status

# Stop daemon
aegis daemon stop
```

---

## 12. Antigravity Integration

Aegis complies with current Antigravity workspace conventions:
- Workspace rules: `.agents/rules/aegis_verification_rules.md`
- Workspace skills: `.agents/skills/aegis-harness/SKILL.md`
- IDE tasks: `.vscode/tasks.json`

---

## 13. Docker Execution

When Docker is running, Aegis supports containerized execution with workspace mounts and restricted networking (`--network none`):
```yaml
execution:
  backend: "docker"  # or "auto"
  network: "none"
```
If Docker is not running, Aegis safely falls back to `LocalExecutor`.

---

## 14. Troubleshooting

Run the built-in diagnostic doctor:
```bash
aegis doctor
```
Checks Python version, Git root, config validity, API key setup, workspace permissions, Docker status, and daemon responsiveness.

---

## 15. Security Limitations

- **Local Process Boundary**: Local subprocess isolation does not constitute an operating system virtualization sandbox.
- **Untrusted Repositories**: Run untrusted code in Docker containers or isolated VMs.

---

## 16. Development & Testing

Run full test suite:
```bash
pytest tests/ -v
```

Run security-specific tests:
```bash
pytest tests/security/ -v
```

---

## 17. Packaging

Build distributable wheel and sdist:
```bash
python -m build
```
Produces artifacts in `dist/`.
