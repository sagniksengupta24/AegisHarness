"""Inspection tools: remember, recall, run_verification."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from aegis.models import ToolResult
from aegis.tools.base import BaseTool, ToolContext, ToolPermission


class RememberArgs(BaseModel):
    lesson: str = Field(description="Actionable lesson learned about this repository or workflow")
    context_tags: list[str] = Field(default_factory=list, description="Keywords/tags classifying the lesson")
    files: list[str] = Field(default_factory=list, description="Files associated with this lesson")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0")


class RememberTool(BaseTool):
    name = "remember"
    description = "Persist an approved project lesson or operational insight into repository episodic memory."
    permission = ToolPermission.WRITE
    args_schema = RememberArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = RememberArgs.model_validate(arguments)
        if not context.memory_manager:
            return ToolResult(tool_name=self.name, call_id=call_id, success=False, output="", error="Memory manager is not available in context")

        # Guard against storing obvious secrets in memory
        sec_eval = context.gateguard.secret_guard.scan_content(args.lesson, context="memory lesson")
        if sec_eval.decision != sec_eval.decision.ALLOW:
            return ToolResult(tool_name=self.name, call_id=call_id, success=False, output="", error=f"Memory save blocked: {sec_eval.reason}")

        lesson_entry = context.memory_manager.save_lesson(
            lesson=args.lesson,
            context=args.context_tags,
            files=args.files,
            confidence=args.confidence,
        )

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output=f"Successfully remembered lesson (ID: {lesson_entry.id}): '{lesson_entry.lesson}'",
            metadata={"lesson_id": lesson_entry.id},
        )


class RecallArgs(BaseModel):
    query: str = Field(description="Search terms or keywords to query repository memory")
    context_tags: Optional[list[str]] = Field(default=None, description="Optional tag filters")


class RecallTool(BaseTool):
    name = "recall"
    description = "Retrieve relevant historical lessons and repository memory."
    permission = ToolPermission.READ
    args_schema = RecallArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = RecallTool.args_schema.model_validate(arguments)
        if not context.memory_manager:
            return ToolResult(tool_name=self.name, call_id=call_id, success=False, output="", error="Memory manager is not available")

        from aegis.memory.retrieval import MemoryRetriever
        retriever = MemoryRetriever(top_k=5)
        all_lessons = context.memory_manager.load_lessons()
        relevant = retriever.retrieve(
            lessons=all_lessons,
            query=args.query,
            context_tags=args.context_tags,
        )

        untrusted_text = retriever.format_untrusted_context(relevant)
        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output=untrusted_text if untrusted_text else "No relevant memory entries found.",
            metadata={"count": len(relevant)},
        )


class RunVerificationArgs(BaseModel):
    timeout_seconds: Optional[int] = Field(default=None, description="Optional timeout for verification run")


class RunVerificationTool(BaseTool):
    name = "run_verification"
    description = "Execute configured verification gates (lint, test, build) and receive structured feedback."
    permission = ToolPermission.EXECUTE
    args_schema = RunVerificationArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = RunVerificationArgs.model_validate(arguments)
        if not context.verifier:
            return ToolResult(tool_name=self.name, call_id=call_id, success=False, output="", error="Verifier is not configured in context")

        report = context.verifier.run_all(timeout_override=args.timeout_seconds)
        is_pass = (report.status == "PASS")

        output_lines = [
            f"Verification Status: {report.status}",
            f"Summary: {report.summary}",
        ]
        for g in report.gates:
            output_lines.append(f"\n--- Gate: {g.gate_name} ({g.status}) ---")
            output_lines.append(f"Command: {g.command} (exit {g.exit_code}, {g.duration_ms}ms)")
            if g.stdout:
                output_lines.append(f"STDOUT:\n{g.stdout[:2000]}")
            if g.stderr:
                output_lines.append(f"STDERR:\n{g.stderr[:2000]}")

        if report.actionable_instruction:
            output_lines.append(f"\nActionable Instruction:\n{report.actionable_instruction}")

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=is_pass,
            output="\n".join(output_lines),
            error=None if is_pass else f"Verification failed on one or more gates: {report.summary}",
            metadata={"status": report.status, "report": report.model_dump()},
        )
