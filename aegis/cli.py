"""Aegis Command Line Interface (CLI)."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

from aegis import __version__
from aegis.client import GeminiModelClient
from aegis.config import AegisConfig, find_repo_root, load_config
from aegis.daemon.client import DaemonClient
from aegis.daemon.server import DaemonServer
from aegis.diff.engine import colorize_diff, compute_unified_diff
from aegis.errors import AegisError, ConfigurationError, DaemonError
from aegis.execution.sandbox import get_executor, is_docker_available
from aegis.logging import get_logger
from aegis.memory.episodic import EpisodicMemoryManager
from aegis.models import AgentStatus
from aegis.orchestrator import Orchestrator
from aegis.session.checkpoint import SessionCheckpoint
from aegis.verifier.runner import VerificationRunner

logger = get_logger("aegis.cli")


def detect_repository_stack(root: Path) -> dict[str, Any]:
    """Detects repository technologies and returns recommended configuration parameters."""
    stack_info = {
        "name": root.name,
        "stack": "generic",
        "pre_flight": None,
        "lint": None,
        "test_cmd": "pytest tests/ -q",
        "build_cmd": None,
    }

    # Python detection
    pytest_bin = ".venv/bin/pytest" if (root / ".venv" / "bin" / "pytest").exists() else "pytest"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
        stack_info["stack"] = "python"
        stack_info["test_cmd"] = f"{pytest_bin} tests/ -q"
        stack_info["lint"] = "ruff check ." if shutil.which("ruff") else None

    # Node / Next / React detection
    elif (root / "package.json").exists():
        pkg_data = {}
        try:
            pkg_data = json.loads((root / "package.json").read_text(encoding="utf-8"))
        except Exception:
            pass

        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
        if "next" in deps:
            stack_info["stack"] = "nextjs"
            stack_info["build_cmd"] = "npm run build"
        elif "react" in deps:
            stack_info["stack"] = "react"
        elif (root / "tsconfig.json").exists():
            stack_info["stack"] = "typescript"
        else:
            stack_info["stack"] = "node"

        scripts = pkg_data.get("scripts", {})
        if "test" in scripts:
            stack_info["test_cmd"] = "npm test"
        if "lint" in scripts:
            stack_info["lint"] = "npm run lint"

    # Go detection
    elif (root / "go.mod").exists():
        stack_info["stack"] = "go"
        stack_info["test_cmd"] = "go test ./..."
        stack_info["build_cmd"] = "go build ./..."

    # Rust detection
    elif (root / "Cargo.toml").exists():
        stack_info["stack"] = "rust"
        stack_info["test_cmd"] = "cargo test"
        stack_info["build_cmd"] = "cargo check"

    return stack_info


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffolds Aegis configuration, directory structure, and IDE tasks."""
    root = Path.cwd().resolve()
    target_config = root / ".aegis.yaml"

    if target_config.exists() and not args.force:
        print(f"[!] Configuration file '{target_config.name}' already exists. Use --force to overwrite.")
        return 1

    detected = detect_repository_stack(root)
    print(f"[*] Detected repository stack: {detected['stack']} (project: {detected['name']})")

    # Generate .aegis.yaml content with clear documentation comments
    config_yaml = f"""# Aegis Configuration File
version: 1

project:
  name: "{detected['name']}"
  stack: "{detected['stack']}"

model:
  provider: "gemini"
  model: null  # Defaults to GEMINI_MODEL or gemini-2.5-flash
  temperature: 0.2

agent:
  max_turns: 24
  max_repairs: 5
  max_tool_calls: 100
  max_command_runtime_seconds: 60
  max_output_size_bytes: 100000

verification:
  pre_flight: {f'"{detected["pre_flight"]}"' if detected["pre_flight"] else 'null'}
  lint: {f'"{detected["lint"]}"' if detected["lint"] else 'null'}
  test_cmd: {f'"{detected["test_cmd"]}"' if detected["test_cmd"] else 'null'}
  build_cmd: {f'"{detected["build_cmd"]}"' if detected["build_cmd"] else 'null'}
  timeout_seconds: 60
  required_gates:
    - "test_cmd"

guardrails:
  deny_paths:
    - ".git/**"
    - ".env"
    - ".env.*"
    - "secrets/**"
    - "*.pem"
    - "*.key"
    - "id_rsa*"
    - "credentials*"
    - ".ssh/**"
  fail_closed: true
  interactive_by_default: false
  blocked_commands:
    - "rm -rf /"
    - "sudo"
    - "su"
    - "mkfs"
  allow_network: false

execution:
  backend: "auto"  # auto | local | docker
  network: "none"
  timeout_seconds: 60

memory:
  enabled: true
  path: ".aegis/memory.json"
  top_k: 5

telemetry:
  enabled: true
  path: ".aegis/traces"
"""
    target_config.write_text(config_yaml, encoding="utf-8")
    print(f"[✓] Created '{target_config.name}'")

    # Setup directories
    aegis_dir = root / ".aegis"
    skills_dir = aegis_dir / "skills"
    traces_dir = aegis_dir / "traces"
    skills_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    # Create example skill manifest
    example_skill = skills_dir / "testing_guidance.yaml"
    if not example_skill.exists():
        skill_content = """name: "testing_guidance"
description: "Guidelines for writing robust test suites"
triggers:
  files:
    - "test_*.py"
    - "*_test.go"
    - "*.test.ts"
  keywords:
    - "test"
    - "pytest"
    - "verify"
  stacks:
    - "python"
    - "typescript"
instructions: |
  Always ensure test fixtures are cleaned up.
  Do not mock external verification gates.
  Prefer deterministic assertion values over random inputs.
tools: []
enabled: true
"""
        example_skill.write_text(skill_content, encoding="utf-8")
        print(f"[✓] Created example skill manifest at '{example_skill.relative_to(root)}'")

    # Setup VS Code tasks.json integration if .vscode exists or requested
    vscode_dir = root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = vscode_dir / "tasks.json"
    if not tasks_file.exists() or args.force:
        tasks_json = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "Aegis: Run Task",
                    "type": "shell",
                    "command": "aegis run --task \"${input:taskPrompt}\"",
                    "problemMatcher": [],
                    "group": "build"
                },
                {
                    "label": "Aegis: Strict Verify",
                    "type": "shell",
                    "command": "aegis verify",
                    "problemMatcher": [],
                    "group": "test"
                },
                {
                    "label": "Aegis: Diff",
                    "type": "shell",
                    "command": "aegis diff",
                    "problemMatcher": [],
                    "group": "none"
                },
                {
                    "label": "Aegis: Doctor",
                    "type": "shell",
                    "command": "aegis doctor",
                    "problemMatcher": [],
                    "group": "none"
                }
            ],
            "inputs": [
                {
                    "id": "taskPrompt",
                    "type": "promptString",
                    "description": "Enter coding task for Aegis"
                }
            ]
        }
        tasks_file.write_text(json.dumps(tasks_json, indent=2), encoding="utf-8")
        print(f"[✓] Created VS Code integration at '{tasks_file.relative_to(root)}'")

    print("\n[+] Aegis initialized successfully. Run 'aegis doctor' to verify system readiness.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Executes an agent task through the deterministic orchestrator."""
    root = find_repo_root()
    config = load_config(root)

    if not args.task:
        print("[-] Error: --task argument is required.", file=sys.stderr)
        return 2

    print(f"[*] Starting Aegis task: '{args.task}'")
    print(f"[*] Repository root: {root}")
    print(f"[*] Verification gate: {config.verification.test_cmd or 'none'}")

    try:
        model_client = GeminiModelClient(
            model_name=args.model or config.model.resolved_model,
            temperature=config.model.temperature,
        )
    except Exception as e:
        print(f"[-] Model initialization error: {e}", file=sys.stderr)
        print("[-] Hint: ensure GEMINI_API_KEY is set in your environment.", file=sys.stderr)
        return 1

    orchestrator = Orchestrator(
        repo_root=root,
        config=config,
        model_client=model_client,
        interactive=args.interactive,
    )

    result = orchestrator.run_task(args.task)

    print("\n" + "=" * 50)
    print(f"AEGIS TASK RESULT: {result.status.value}")
    print(f"Session ID: {result.session_id}")
    print(f"Turns: {result.turns}")
    print(f"Duration: {round(result.duration_seconds, 2)}s")

    if result.status == AgentStatus.COMPLETED:
        print(f"Changed Files ({len(result.changed_files)}):")
        for f in result.changed_files:
            print(f"  • {f}")
        print("\n[✓] Task COMPLETED and verified.")
        return 0
    else:
        print(f"Error: {result.error}")
        print("\n[!] Task FAILED or fail-closed. Unverified changes were automatically rolled back.")
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Runs configured verification gates directly without model intervention."""
    root = find_repo_root()
    config = load_config(root)

    print(f"[*] Running verification gates for '{config.project.name}'...")
    executor = get_executor(root, backend=config.execution.backend)
    runner = VerificationRunner(root, executor, config.verification)
    report = runner.run_all()

    print("\n=== Verification Report ===")
    for gate in report.gates:
        symbol = "[✓]" if gate.status == "PASS" else "[✗]"
        print(f"{symbol} Gate '{gate.gate_name}': {gate.status} (exit {gate.exit_code}, {gate.duration_ms}ms)")
        print(f"    Command: {gate.command}")
        if gate.status != "PASS":
            if gate.stdout:
                print(f"    STDOUT:\n{gate.stdout.strip()[:1000]}")
            if gate.stderr:
                print(f"    STDERR:\n{gate.stderr.strip()[:1000]}")

    print("-" * 30)
    print(f"OVERALL STATUS: {report.status}")
    if report.status == "PASS":
        print("[✓] All required gates passed.")
        return 0
    else:
        print(f"[✗] Verification failed: {report.actionable_instruction}")
        return 1


def cmd_diff(args: argparse.Namespace) -> int:
    """Displays diff of changes made during the latest Aegis session or git diff."""
    root = find_repo_root()
    sessions_dir = root / ".aegis" / "sessions"

    if sessions_dir.exists():
        # Find newest session dir
        subdirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        if subdirs:
            subdirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            latest_session = subdirs[0]
            checkpoint = SessionCheckpoint(root, session_id=latest_session.name)
            diff_text = checkpoint.get_session_diff()
            if diff_text:
                print(f"=== Session Diff: {latest_session.name} ===")
                print(colorize_diff(diff_text))
                return 0

    # Fallback to git diff
    try:
        res = subprocess.run(["git", "diff"], cwd=str(root), capture_output=True, text=True)
        if res.stdout:
            print(colorize_diff(res.stdout))
            return 0
        print("[No changes detected]")
        return 0
    except Exception as e:
        print(f"[-] Failed to get diff: {e}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Displays current repository, session, and daemon status."""
    root = find_repo_root()
    config = load_config(root)

    print(f"AegisHarness v{__version__}")
    print(f"Repository Root: {root}")
    print(f"Stack: {config.project.stack} | Model: {config.model.resolved_model}")

    # Daemon status
    client = DaemonClient(root)
    daemon_running = client.is_running()
    print(f"Daemon: {'RUNNING [✓]' if daemon_running else 'STOPPED [✗]'}")

    # Memory entries count
    mem_manager = EpisodicMemoryManager(root, memory_path=config.memory.path)
    lessons = mem_manager.load_lessons()
    print(f"Memory Lessons: {len(lessons)}")

    # Sessions count
    sessions_dir = root / ".aegis" / "sessions"
    session_count = len(list(sessions_dir.glob("*"))) if sessions_dir.exists() else 0
    print(f"Recorded Sessions: {session_count}")
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    """Manages repository episodic memory."""
    root = find_repo_root()
    config = load_config(root)
    manager = EpisodicMemoryManager(root, memory_path=config.memory.path)

    if args.memory_action == "list":
        lessons = manager.load_lessons()
        if not lessons:
            print("[No memory lessons found.]")
            return 0
        print(f"=== Project Lessons ({len(lessons)}) ===")
        for idx, l in enumerate(lessons, 1):
            tags = f" [{', '.join(l.context)}]" if l.context else ""
            print(f"{idx}. (ID: {l.id}) {l.lesson}{tags}")
            print(f"   Created: {l.created_at} | Confidence: {l.confidence}")
        return 0

    elif args.memory_action == "add":
        if not args.lesson:
            print("[-] Error: --lesson text is required.", file=sys.stderr)
            return 2
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
        files = [f.strip() for f in args.files.split(",")] if args.files else []
        item = manager.save_lesson(args.lesson, context=tags, files=files, confidence=args.confidence)
        print(f"[✓] Saved memory lesson (ID: {item.id}): '{item.lesson}'")
        return 0

    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Manages the background Aegis IPC daemon."""
    root = find_repo_root()
    action = args.daemon_action

    if action == "start":
        client = DaemonClient(root)
        if client.is_running():
            print("[!] Aegis daemon is already running.")
            return 0

        if args.foreground:
            print(f"[*] Starting Aegis daemon in foreground...")
            server = DaemonServer(root)
            server.start(foreground=True)
            return 0
        else:
            # Fork daemon into background
            print("[*] Launching Aegis daemon in background...")
            proc = subprocess.Popen(
                [sys.executable, "-m", "aegis", "daemon", "start", "--foreground"],
                cwd=str(root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Wait up to 3s for daemon to become responsive
            time.sleep(0.5)
            for _ in range(6):
                if client.is_running():
                    print(f"[✓] Daemon started successfully (PID: {proc.pid}).")
                    return 0
                time.sleep(0.5)

            print("[-] Daemon launched but did not respond to ping within 3s.", file=sys.stderr)
            return 1

    elif action == "stop":
        client = DaemonClient(root)
        if not client.is_running():
            print("[!] Aegis daemon is not running.")
            return 0
        try:
            resp = client.send_request("stop")
            print("[✓] Daemon stop requested.")
            return 0
        except Exception as e:
            print(f"[-] Failed to stop daemon: {e}", file=sys.stderr)
            return 1

    elif action == "status":
        client = DaemonClient(root)
        if client.is_running():
            resp = client.send_request("status")
            print("[✓] Aegis daemon is RUNNING.")
            print(f"    Details: {resp.result}")
            return 0
        else:
            print("[✗] Aegis daemon is NOT running.")
            return 1

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Performs system diagnostic checks across runtime, tools, git, config, and models."""
    root = find_repo_root()
    print("=== Aegis Diagnostic Doctor ===\n")
    missing_deps: list[str] = []
    config_error: Optional[str] = None
    optional_limitations: list[str] = []

    # 1. Python version check
    py_ver = sys.version_info
    py_ok = (py_ver.major == 3 and py_ver.minor >= 12)
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ok:
        print(f"[✓] Python version: {py_str} (>= 3.12)")
    else:
        print(f"[✗] Python version: {py_str} (Requires Python >= 3.12)")
        missing_deps.append(f"Python >= 3.12 (current: {py_str})")

    # 2. Git check
    git_bin = shutil.which("git")
    if git_bin:
        try:
            git_ver = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
            print(f"[✓] Git: {git_ver}")
        except Exception:
            print("[✗] Git is installed but not responding.")
            missing_deps.append("Git installed but not responding")
    else:
        print("[✗] Git executable not found in PATH.")
        missing_deps.append("Git executable in PATH")

    # 3. Config check
    config_file = root / ".aegis.yaml"
    if config_file.exists():
        try:
            cfg = load_config(root)
            print(f"[✓] Configuration: Valid (.aegis.yaml, stack={cfg.project.stack})")
        except Exception as ce:
            print(f"[✗] Configuration invalid: {ce}")
            config_error = str(ce)
    else:
        print("[!] Configuration: .aegis.yaml not found (run 'aegis init' to scaffold)")
        optional_limitations.append(".aegis.yaml not found (run 'aegis init' to scaffold)")

    # 4. Workspace permissions
    test_file = root / ".aegis_perm_test"
    try:
        test_file.write_text("perm_check", encoding="utf-8")
        test_file.unlink()
        print("[✓] Workspace permissions: Read and write verified")
    except Exception as e:
        print(f"[✗] Workspace permission error: {e}")
        missing_deps.append(f"Workspace write permission: {e}")

    # 5. Gemini configuration
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        print(f"[✓] Gemini API Key: Configured ({masked})")
    else:
        print("[!] Gemini API Key: Not set in GEMINI_API_KEY (required for live model runs)")
        optional_limitations.append("GEMINI_API_KEY unset (live Gemini requests unavailable)")

    # 6. Docker availability
    docker_ok = is_docker_available()
    if docker_ok:
        print("[✓] Docker: Daemon is running (container isolation available)")
    else:
        print("[!] Docker: Daemon not running (falling back to secure LocalExecutor)")
        optional_limitations.append("Docker daemon offline (falling back to LocalExecutor)")

    # 7. Daemon status
    daemon_client = DaemonClient(root)
    if daemon_client.is_running():
        print("[✓] Background Daemon: Running")
    else:
        print("[!] Background Daemon: Stopped (CLI operates in standalone mode)")
        optional_limitations.append("Daemon stopped (CLI operates in standalone mode)")

    print("\n" + ("=" * 40))
    if missing_deps:
        print("STATUS: MISSING REQUIRED DEPENDENCY")
        for dep in missing_deps:
            print(f"  - Missing: {dep}")
        return 1
    elif config_error:
        print("STATUS: CONFIGURATION ERROR")
        print(f"  - Error: {config_error}")
        return 1
    elif optional_limitations:
        print("STATUS: READY WITH OPTIONAL LIMITATIONS")
        for lim in optional_limitations:
            print(f"  - Limitation: {lim}")
        return 0
    else:
        print("STATUS: READY - All required and optional capabilities verified.")
        return 0


def cmd_commit(args: argparse.Namespace) -> int:
    """Executes the Commit & Remember workflow.

    1. Inspects Aegis session changes / uncommitted git changes.
    2. Runs strict verification gates (cannot commit if gates fail).
    3. Summarizes validated changes.
    4. Extracts and saves a lesson to episodic memory if one exists.
    5. Prepares a conventional commit message.
    6. Does NOT automatically commit without human approval.
    """
    root = find_repo_root()
    config = load_config(root)

    print("=== Aegis Commit & Remember Workflow ===\n")

    # 1. Verification gate check
    if not getattr(args, "skip_verify", False):
        print("[*] Running strict verification gates before commit...")
        executor = get_executor(root, backend=config.execution.backend)
        runner = VerificationRunner(root, executor, config.verification)
        report = runner.run_all()
        if report.status != "PASS":
            print(f"[✗] Verification failed ({report.actionable_instruction}). Cannot commit broken changes.", file=sys.stderr)
            return 1
        print("[✓] All required verification gates passed.")
    else:
        print("[!] Warning: Verification gates bypassed via --skip-verify.")

    # 2. Inspect session changes and git status
    sessions_dir = root / ".aegis" / "sessions"
    session_touched: list[str] = []
    if sessions_dir.exists():
        subdirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        if subdirs:
            subdirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            latest_session = subdirs[0]
            checkpoint = SessionCheckpoint(root, session_id=latest_session.name)
            session_touched = sorted(list(checkpoint.touched_files.union(checkpoint.created_files)))

    # Also check git status
    git_status_lines: list[str] = []
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            git_status_lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    except Exception as e:
        logger.debug(f"Git status query failed: {e}")

    if not git_status_lines and not session_touched:
        untracked = [str(p.relative_to(root)) for p in root.glob("*") if not p.name.startswith(".")]
        if untracked:
            session_touched = untracked
        else:
            print("[!] No modified, untracked, or session changes detected to commit.")
            return 0

    print(f"\n[*] Validated changes detected:")
    if session_touched:
        print(f"    Session files ({len(session_touched)}):")
        for f in session_touched[:10]:
            print(f"      - {f}")
        if len(session_touched) > 10:
            print(f"      ... and {len(session_touched) - 10} more")

    if git_status_lines:
        print(f"    Git working tree changes ({len(git_status_lines)}):")
        for l in git_status_lines[:10]:
            print(f"      {l}")
        if len(git_status_lines) > 10:
            print(f"      ... and {len(git_status_lines) - 10} more")

    # 3. Lesson extraction and saving
    lesson_text = getattr(args, "lesson", None)
    if not lesson_text and not getattr(args, "dry_run", False) and not getattr(args, "yes", False):
        try:
            prompt_input = input("\n[?] Lesson learned to remember (optional, press Enter to skip): ").strip()
            if prompt_input:
                lesson_text = prompt_input
        except (EOFError, KeyboardInterrupt):
            pass

    if lesson_text:
        mem_manager = EpisodicMemoryManager(root, memory_path=config.memory.path)
        relevant_files = session_touched or [l.split()[-1] for l in git_status_lines]
        saved_entry = mem_manager.save_lesson(
            lesson=lesson_text,
            context=["commit", config.project.stack],
            files=relevant_files[:5],
            confidence=1.0,
            source="commit_and_remember",
        )
        print(f"[✓] Lesson remembered (ID: {saved_entry.id}): '{saved_entry.lesson}'")

    # 4. Prepare conventional commit message
    if getattr(args, "message", None):
        commit_msg = args.message
    else:
        # Determine prefix based on changed paths
        all_touched = session_touched or [l.split()[-1] for l in git_status_lines]
        if all("test" in f.lower() for f in all_touched):
            prefix = "test"
        elif any("fix" in f.lower() or "guard" in f.lower() for f in all_touched):
            prefix = "fix"
        elif any("doc" in f.lower() or f.endswith(".md") for f in all_touched):
            prefix = "docs"
        else:
            prefix = "feat"

        sample = all_touched[0].split("/")[-1] if all_touched else "workspace"
        commit_msg = f"{prefix}: validate and update {sample}"

    print(f"\n=== Prepared Conventional Commit ===")
    print(f"Commit message: {commit_msg}")

    # 5. Guard: Human approval check (NEVER commit automatically)
    if getattr(args, "dry_run", False):
        print("\n[✓] Dry run: commit prepared and validated. No git commit executed.")
        return 0

    if not getattr(args, "yes", False):
        try:
            confirm = input("\n[?] Execute git commit with this message? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("[!] Commit cancelled by human operator. Working tree preserved.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\n[!] Commit cancelled. Working tree preserved.")
            return 0

    # User explicitly confirmed execution
    try:
        res = subprocess.run(
            ["git", "commit", "-am", commit_msg],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            print(f"[✓] Committed successfully: {res.stdout.strip()}")
            return 0
        else:
            print(f"[✗] Git commit failed: {res.stderr.strip()}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"[✗] Git commit execution error: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point parser and router."""
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="AegisHarness: Deterministic verification-first local coding agent harness.",
    )
    parser.add_argument("--version", action="version", version=f"aegis {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize Aegis in current repository")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing configuration")

    # run
    p_run = subparsers.add_parser("run", help="Run an agent task loop")
    p_run.add_argument("--task", "-t", required=True, help="Task description for the agent")
    p_run.add_argument("--interactive", "-i", action="store_true", help="Prompt before applying file patches")
    p_run.add_argument("--model", "-m", help="Gemini model override")

    # verify
    p_verify = subparsers.add_parser("verify", help="Execute verification gates")

    # diff
    p_diff = subparsers.add_parser("diff", help="Show changes introduced by Aegis")

    # status
    p_status = subparsers.add_parser("status", help="Show system and session status")

    # commit & remember
    p_commit = subparsers.add_parser("commit", help="Commit validated changes & remember lessons learned")
    p_commit.add_argument("--message", "-m", help="Conventional commit message override")
    p_commit.add_argument("--lesson", "-l", help="Project lesson to store in episodic memory")
    p_commit.add_argument("--dry-run", action="store_true", help="Prepare commit and save lesson without running git commit")
    p_commit.add_argument("--yes", "-y", action="store_true", help="Bypass interactive confirmation prompt")
    p_commit.add_argument("--skip-verify", action="store_true", help="Bypass strict verification check")

    # memory
    p_mem = subparsers.add_parser("memory", help="Inspect and manage episodic memory")
    mem_sub = p_mem.add_subparsers(dest="memory_action", help="Memory actions")
    mem_sub.add_parser("list", help="List stored memory lessons")
    p_mem_add = mem_sub.add_parser("add", help="Add a new lesson")
    p_mem_add.add_argument("--lesson", "-l", required=True, help="Lesson text to save")
    p_mem_add.add_argument("--tags", help="Comma-separated context tags")
    p_mem_add.add_argument("--files", help="Comma-separated relevant files")
    p_mem_add.add_argument("--confidence", type=float, default=1.0, help="Confidence rating (0.0 - 1.0)")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Manage background daemon")
    daemon_sub = p_daemon.add_subparsers(dest="daemon_action", help="Daemon actions")
    p_d_start = daemon_sub.add_parser("start", help="Start background daemon")
    p_d_start.add_argument("--foreground", action="store_true", help="Run in foreground")
    daemon_sub.add_parser("stop", help="Stop running daemon")
    daemon_sub.add_parser("status", help="Check daemon running state")

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Run system diagnostics")

    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    handler_map = {
        "init": cmd_init,
        "run": cmd_run,
        "verify": cmd_verify,
        "diff": cmd_diff,
        "status": cmd_status,
        "commit": cmd_commit,
        "memory": cmd_memory,
        "daemon": cmd_daemon,
        "doctor": cmd_doctor,
    }

    handler = handler_map.get(args.subcommand)
    if handler:
        try:
            return handler(args)
        except AegisError as ae:
            print(f"[-] Aegis error ({ae.__class__.__name__}): {ae.message}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[-] Unexpected error: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0
