"""Bounded agent loop orchestrator enforcing fail-closed lifecycle transitions and security gates."""

import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aegis.client import ModelClient, ModelResponse
from aegis.config import AegisConfig
from aegis.diff.engine import compute_unified_diff
from aegis.errors import LoopBudgetExceeded, PolicyViolationError, RollbackError, VerificationFailed
from aegis.execution.sandbox import get_executor
from aegis.guard import GateGuard
from aegis.logging import get_logger
from aegis.memory.episodic import EpisodicMemoryManager
from aegis.memory.retrieval import MemoryRetriever
from aegis.memory.schema import WorkingMemory
from aegis.models import (
    AgentState,
    AgentStatus,
    MemoryLesson,
    PolicyDecision,
    TaskResult,
    ToolCallRequest,
    VerificationReport,
)
from aegis.session.checkpoint import SessionCheckpoint
from aegis.skills.detector import SkillDetector
from aegis.skills.loader import SkillLoader
from aegis.state import StateMachine
from aegis.telemetry.tracer import TelemetryTracer
from aegis.tools.base import ToolContext
from aegis.tools.registry import ToolRegistry, create_default_registry
from aegis.verifier.runner import VerificationRunner

logger = get_logger("aegis.orchestrator")


def normalize_failure_fingerprint(text: str) -> str:
    """Normalizes error messages by stripping dynamic timestamps, addresses, durations, and PIDs."""
    if not text:
        return ""
    # Strip ISO and bracketed timestamps
    res = re.sub(r"\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b", "<TIMESTAMP>", text)
    res = re.sub(r"\[?\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b\]?", "<TIME>", res)
    # Strip memory hex addresses
    res = re.sub(r"0x[0-9a-fA-F]{4,16}\b", "<HEXADDR>", res)
    # Strip execution durations
    res = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds)\b", "<DURATION>", res, flags=re.IGNORECASE)
    # Strip PIDs
    res = re.sub(r"\bpid[:\s=]+\d+\b", "pid <PID>", res, flags=re.IGNORECASE)
    # Collapse multiple whitespace
    return re.sub(r"\s+", " ", res).strip()


class Orchestrator:
    """Core Aegis orchestrator managing the Plan -> Implement -> Verify -> Complete/Rollback lifecycle."""

    def __init__(
        self,
        repo_root: Path,
        config: AegisConfig,
        model_client: ModelClient,
        tool_registry: Optional[ToolRegistry] = None,
        interactive: bool = False,
        approval_callback: Optional[Callable[[str, str], bool]] = None,
    ):
        self.repo_root = repo_root.resolve()
        self.config = config
        self.client = model_client
        self.interactive = interactive or config.guardrails.interactive_by_default
        self.approval_callback = approval_callback
        self._cancel_requested = threading.Event()

        # Core subsystems
        self.gateguard = GateGuard(
            repo_root=self.repo_root,
            deny_paths=self.config.guardrails.deny_paths,
            blocked_commands=self.config.guardrails.blocked_commands,
            allow_network=self.config.guardrails.allow_network,
        )

        self.executor = get_executor(
            repo_root=self.repo_root,
            backend=self.config.execution.backend,
            timeout_seconds=self.config.execution.timeout_seconds,
            network=self.config.execution.network,
        )

        self.verifier = VerificationRunner(
            repo_root=self.repo_root,
            executor=self.executor,
            config=self.config.verification,
        )

        self.registry = tool_registry or create_default_registry()
        self.memory_manager = EpisodicMemoryManager(self.repo_root, memory_path=self.config.memory.path)
        self.retriever = MemoryRetriever(top_k=self.config.memory.top_k)
        self.skill_loader = SkillLoader(self.repo_root)
        self.skill_detector = SkillDetector(self.repo_root)
        self.tracer = TelemetryTracer(self.repo_root, traces_dir_rel=self.config.telemetry.path, enabled=self.config.telemetry.enabled)

    def cancel(self) -> None:
        """Signals the running orchestrator to cancel execution safely."""
        self._cancel_requested.set()

    def _build_system_instruction(
        self,
        task: str,
        relevant_memory_text: str,
        active_skills_text: str,
    ) -> str:
        """Assembles bounded system instructions."""
        rules = [
            "You are Aegis, a deterministic, verification-first local coding agent harness.",
            "You operate within strict repository boundaries under GateGuard policy control.",
            "",
            "Core Execution Lifecycle:",
            "1. PLAN: Analyze the task and propose a structured plan before making modifications.",
            "2. IMPLEMENT: Read files, inspect directory structures, and apply surgical patches.",
            "3. VERIFY: Execute required verification gates (lint, test, build).",
            "4. DIAGNOSE & REPAIR: If verification fails, inspect the failure, locate the root cause, patch, and verify again.",
            "",
            "MANDATORY INVARIANTS:",
            "- Your claim of success does NOT finalize a task. Only passing all required verification gates achieves COMPLETE.",
            "- Never touch protected paths (.git, .env, secrets, *.pem, *.key, id_rsa, credentials).",
            "- Do not run destructive deletion commands or spawn interactive editors.",
            "- When modifying files, prefer targeted patches.",
            "- If you believe you are done, call 'run_verification' or propose task completion.",
        ]

        if active_skills_text:
            rules.append(active_skills_text)

        if relevant_memory_text:
            rules.append(relevant_memory_text)

        return "\n".join(rules)

    def run_task(self, task: str) -> TaskResult:
        """Executes the full agent loop for the given user task."""
        start_time = time.perf_counter()
        checkpoint = SessionCheckpoint(self.repo_root)
        state_machine = StateMachine(AgentState.IDLE)
        
        logger.info(f"Starting Aegis session {checkpoint.session_id} for task: '{task}'")

        # Discover skills and memory
        available_skills = self.skill_loader.load_all_skills()
        active_skills = self.skill_detector.detect_active_skills(
            available_skills=available_skills,
            task=task,
            stack=self.config.project.stack,
        )
        skills_text = self.skill_detector.format_skills_instructions(active_skills)

        all_lessons = self.memory_manager.load_lessons() if self.config.memory.enabled else []
        relevant_lessons = self.retriever.retrieve(all_lessons, query=task) if all_lessons else []
        memory_text = self.retriever.format_untrusted_context(relevant_lessons)

        system_instruction = self._build_system_instruction(task, memory_text, skills_text)

        tool_context = ToolContext(
            repo_root=self.repo_root,
            gateguard=self.gateguard,
            executor=self.executor,
            checkpoint=checkpoint,
            verifier=self.verifier,
            memory_manager=self.memory_manager,
            interactive=self.interactive,
            approval_callback=self.approval_callback,
        )

        gemini_tools = self.registry.get_gemini_tool_declarations()

        # Conversation history
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"TASK: {task}"}
        ]

        # Tracking variables
        turn = 0
        repair_count = 0
        total_tool_calls = 0
        consecutive_failures = 0
        last_failure_snippet = ""
        last_verification_report: Optional[VerificationReport] = None
        newly_learned_lessons: list[MemoryLesson] = []

        # Start lifecycle: IDLE -> PLAN
        state_machine.transition(AgentState.PLAN, reason="Task initialized")

        final_status = AgentStatus.FAILED
        failure_error_message = None

        while turn < self.config.agent.max_turns:
            turn += 1
            state_machine.turn = turn
            logger.debug(f"[Turn {turn}] Current state: {state_machine.current_state.value}")

            # Check explicit cancellation request
            if self._cancel_requested.is_set():
                failure_error_message = "Task execution was cancelled."
                final_status = AgentStatus.ABORTED
                if not state_machine.is_terminal():
                    state_machine.transition(AgentState.ABORTED, reason="Cancellation requested")
                break

            # Check maximum execution time limit
            elapsed_time = time.perf_counter() - start_time
            if elapsed_time > getattr(self.config.agent, "max_execution_time_seconds", 300):
                failure_error_message = f"Agent execution time limit ({getattr(self.config.agent, 'max_execution_time_seconds', 300)}s) exceeded."
                final_status = AgentStatus.FAILED
                break

            # Check overall tool call budget
            if total_tool_calls >= self.config.agent.max_tool_calls:
                failure_error_message = f"Tool call budget exceeded ({total_tool_calls} calls)."
                final_status = AgentStatus.FAILED
                break

            # 1. Generate model response
            try:
                model_resp: ModelResponse = self.client.generate(
                    messages=messages,
                    tools=gemini_tools,
                    system_instruction=system_instruction,
                )
            except Exception as e:
                logger.error(f"Model generation error on turn {turn}: {e}")
                failure_error_message = f"Model provider error: {e}"
                final_status = AgentStatus.FAILED
                break

            # Append model turn to conversation history
            messages.append({
                "role": "model",
                "content": model_resp.text or "",
                "tool_calls": model_resp.tool_calls,
                "raw_parts": model_resp.raw_parts,
            })

            # Handle transition from PLAN to IMPLEMENT
            if state_machine.current_state == AgentState.PLAN:
                state_machine.transition(AgentState.IMPLEMENT, reason="Plan established, beginning implementation")

            # 2. Process tool calls proposed by model
            has_tool_calls = bool(model_resp.tool_calls)
            ran_verification_in_turn = False

            if has_tool_calls:
                for tcall in model_resp.tool_calls:
                    # Check cancellation before tool execution
                    if self._cancel_requested.is_set():
                        failure_error_message = "Task execution was cancelled."
                        final_status = AgentStatus.ABORTED
                        if not state_machine.is_terminal():
                            state_machine.transition(AgentState.ABORTED, reason="Cancellation requested")
                        break

                    total_tool_calls += 1
                    logger.info(f"Dispatching tool '{tcall.name}' (id: {tcall.id})")

                    tool_res = self.registry.dispatch(tcall, tool_context)

                    # Detect repeated identical tool failures to prevent infinite loops
                    tool_sig = f"{tcall.name}:{sorted(str(v) for v in tcall.arguments.items())}"
                    norm_tool_err = normalize_failure_fingerprint(tool_res.error or "")
                    combined_sig = f"{tool_sig}|err={norm_tool_err}"

                    if not tool_res.success:
                        if combined_sig == getattr(self, "_last_failing_tool_sig", None):
                            self._failing_tool_count = getattr(self, "_failing_tool_count", 1) + 1
                            if self._failing_tool_count >= 3:
                                failure_error_message = f"Repeated identical tool failure 3 times for '{tcall.name}'. Terminating loop."
                                final_status = AgentStatus.FAILED
                                break
                        else:
                            self._last_failing_tool_sig = combined_sig
                            self._failing_tool_count = 1
                    else:
                        self._last_failing_tool_sig = None
                        self._failing_tool_count = 0

                    # Append structured tool result to conversation
                    t_result_msg = (
                        f"TOOL RESULT ({tcall.name}):\n"
                        f"Success: {tool_res.success}\n"
                        f"Output: {tool_res.output}\n"
                    )
                    if tool_res.error:
                        t_result_msg += f"Error: {tool_res.error}\n"

                    messages.append({
                        "role": "tool",
                        "tool_name": tcall.name,
                        "call_id": tcall.id,
                        "content": t_result_msg,
                        "output": tool_res.output,
                        "success": tool_res.success,
                        "error": tool_res.error,
                    })

                    if tcall.name == "run_verification":
                        ran_verification_in_turn = True
                        if "report" in tool_res.metadata:
                            last_verification_report = VerificationReport.model_validate(tool_res.metadata["report"])

                if final_status in (AgentStatus.FAILED, AgentStatus.ABORTED) and failure_error_message:
                    break

            # 3. Check for verification need
            # If the model proposes completion OR ran verification OR no tool calls in IMPLEMENT state:
            needs_verification_check = (
                model_resp.is_proposing_completion or
                ran_verification_in_turn or
                (not has_tool_calls and state_machine.current_state == AgentState.IMPLEMENT)
            )

            if needs_verification_check:
                state_machine.transition(AgentState.VERIFY, reason="Triggering verification gate evaluation")

                if not ran_verification_in_turn:
                    # Run verifier explicitly
                    last_verification_report = self.verifier.run_all()

                if last_verification_report and last_verification_report.status == "PASS":
                    logger.info("Verification gates PASSED! Transitioning to COMPLETE.")
                    state_machine.transition(AgentState.COMPLETE, reason="All required verification gates passed")
                    final_status = AgentStatus.COMPLETED
                    break
                else:
                    # Verification failed
                    repair_count += 1
                    fail_summary = last_verification_report.summary if last_verification_report else "Unknown failure"
                    logger.warning(f"Verification gates FAILED (repair attempt {repair_count}/{self.config.agent.max_repairs}): {fail_summary}")

                    # Check repeated failure loop using normalized failure fingerprint
                    raw_err = last_verification_report.actionable_instruction if last_verification_report else ""
                    cur_err = normalize_failure_fingerprint(raw_err)
                    if cur_err and cur_err == last_failure_snippet:
                        consecutive_failures += 1
                        if consecutive_failures >= 3:
                            failure_error_message = "Repeated identical verification failure detected 3 times. Terminating loop to prevent endless cycle."
                            final_status = AgentStatus.FAILED
                            break
                    else:
                        consecutive_failures = 1
                        last_failure_snippet = cur_err

                    if repair_count > self.config.agent.max_repairs:
                        failure_error_message = f"Max repair attempts ({self.config.agent.max_repairs}) reached without verification passing."
                        final_status = AgentStatus.FAILED
                        break

                    state_machine.transition(AgentState.DIAGNOSE, reason="Verification failed; initiating diagnosis")
                    messages.append({
                        "role": "user",
                        "content": (
                            f"VERIFICATION FAILED:\n{fail_summary}\n\n"
                            f"Actionable instructions:\n{last_verification_report.actionable_instruction if last_verification_report else 'Fix the errors.'}\n"
                            "Inspect the failure, identify the cause, patch the code, and verify again."
                        ),
                    })
                    state_machine.transition(AgentState.IMPLEMENT, reason="Proceeding with repair patch")

        # End of loop processing
        duration_seconds = time.perf_counter() - start_time
        all_touched_files = sorted(list(checkpoint.touched_files | checkpoint.created_files))

        if final_status == AgentStatus.COMPLETED:
            logger.info(f"Task completed successfully in {round(duration_seconds, 2)}s.")
        else:
            if not failure_error_message:
                failure_error_message = f"Agent turn limit ({self.config.agent.max_turns}) exceeded."
            logger.warning(f"Task stopped ({final_status.value}): {failure_error_message}. Executing transactional rollback.")

            # Rollback only Aegis changes
            try:
                checkpoint.rollback()
            except Exception as re:
                logger.error(f"Rollback failure: {re}")

            if not state_machine.is_terminal():
                try:
                    target_state = AgentState.ABORTED if final_status == AgentStatus.ABORTED else AgentState.FAILED
                    state_machine.transition(target_state, reason=failure_error_message)
                except Exception:
                    pass

        task_result = TaskResult(
            status=final_status,
            session_id=checkpoint.session_id,
            task=task,
            turns=turn,
            changed_files=all_touched_files if final_status == AgentStatus.COMPLETED else [],
            verification=last_verification_report,
            lessons_learned=newly_learned_lessons,
            error=failure_error_message,
            duration_seconds=duration_seconds,
        )

        # Write telemetry trace
        self.tracer.write_trace(
            session_id=checkpoint.session_id,
            task=task,
            model_name=getattr(self.client, "model_name", "model"),
            turns=turn,
            tool_audit=self.registry.audit_log,
            task_result=task_result,
        )

        return task_result
