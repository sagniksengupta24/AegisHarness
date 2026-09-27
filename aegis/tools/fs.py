"""Filesystem tools for Aegis: view_tree, read_file, write_patch, search."""

import os
import re
from pathlib import Path
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from aegis.diff.engine import compute_unified_diff, request_interactive_approval
from aegis.errors import PathGuardError, PolicyViolationError
from aegis.models import PolicyDecision, ToolResult
from aegis.tools.base import BaseTool, ToolContext, ToolPermission


# --- 1. view_tree ---

class ViewTreeArgs(BaseModel):
    directory: str = Field(default=".", description="Relative directory path to inspect")
    max_depth: int = Field(default=3, description="Maximum directory depth to traverse")
    max_entries: int = Field(default=100, description="Maximum number of files/directories to list")


class ViewTreeTool(BaseTool):
    name = "view_tree"
    description = "Inspect repository file structure while strictly respecting denied and protected paths."
    permission = ToolPermission.READ
    args_schema = ViewTreeArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = ViewTreeArgs.model_validate(arguments)
        target_dir = args.directory

        path_eval = context.gateguard.path_guard.evaluate_path(target_dir)
        if path_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Access denied: {path_eval.reason}",
            )

        resolved_dir = Path(path_eval.metadata["resolved_path"])
        if not resolved_dir.is_dir():
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"'{target_dir}' is not a directory",
            )

        lines: list[str] = []
        entries_count = 0

        for root, dirs, files in os.walk(resolved_dir):
            rel_root = Path(root).relative_to(context.repo_root)
            depth = len(rel_root.parts) if str(rel_root) != "." else 0
            if depth >= args.max_depth:
                dirs.clear()
                continue

            # Filter dirs in-place to respect PathGuard
            safe_dirs = []
            for d in list(dirs):
                dir_path = Path(root) / d
                if context.gateguard.path_guard.evaluate_path(dir_path).decision == PolicyDecision.ALLOW:
                    safe_dirs.append(d)
            dirs[:] = safe_dirs

            indent = "  " * depth
            folder_name = Path(root).name if str(rel_root) != "." else "."
            lines.append(f"{indent}[DIR] {folder_name}/")

            for f in files:
                file_path = Path(root) / f
                if context.gateguard.path_guard.evaluate_path(file_path).decision == PolicyDecision.ALLOW:
                    lines.append(f"{indent}  {f}")
                    entries_count += 1
                    if entries_count >= args.max_entries:
                        lines.append(f"{indent}  ... (truncated at {args.max_entries} entries)")
                        dirs.clear()
                        break

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output="\n".join(lines),
            metadata={"entries_count": entries_count},
        )


# --- 2. read_file ---

class ReadFileArgs(BaseModel):
    file_path: str = Field(description="Relative path of file to read")
    start_line: Optional[int] = Field(default=None, description="1-indexed line to start reading from")
    end_line: Optional[int] = Field(default=None, description="1-indexed line to stop reading at")


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read file contents safely with line range support and secret protection."
    permission = ToolPermission.READ
    args_schema = ReadFileArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = ReadFileArgs.model_validate(arguments)
        
        path_eval = context.gateguard.path_guard.evaluate_path(args.file_path)
        if path_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Access denied: {path_eval.reason}",
            )

        resolved_file = Path(path_eval.metadata["resolved_path"])
        if not resolved_file.is_file():
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"File not found: {args.file_path}",
            )

        try:
            raw_text = resolved_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Failed to read file: {e}",
            )

        # SecretGuard check on file content
        secret_eval = context.gateguard.secret_guard.scan_content(raw_text, context=f"file '{args.file_path}'")
        if secret_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Read blocked by security policy: {secret_eval.reason}",
            )

        lines = raw_text.splitlines()
        total_lines = len(lines)

        s_line = max(1, args.start_line) if args.start_line is not None else 1
        e_line = min(total_lines, args.end_line) if args.end_line is not None else total_lines

        selected_lines = lines[s_line - 1 : e_line]
        numbered_lines = [f"{s_line + idx}: {l}" for idx, l in enumerate(selected_lines)]
        output_content = "\n".join(numbered_lines)

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output=output_content,
            metadata={"total_lines": total_lines, "returned_lines": len(selected_lines)},
        )


# --- 3. write_patch ---

class WritePatchArgs(BaseModel):
    file_path: str = Field(description="Relative path of file to create or update")
    content: str = Field(description="New full content or patched content for the target file")
    original_snippet: Optional[str] = Field(default=None, description="Optional substring to replace in existing file")


class WritePatchTool(BaseTool):
    name = "write_patch"
    description = "Apply a controlled patch or write file with path validation, rollback tracking, and diff generation."
    permission = ToolPermission.WRITE
    args_schema = WritePatchArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = WritePatchArgs.model_validate(arguments)
        rel_path = args.file_path

        path_eval = context.gateguard.path_guard.evaluate_path(rel_path)
        if path_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Write denied: {path_eval.reason}",
            )

        resolved_file = Path(path_eval.metadata["resolved_path"])

        # Secret scan
        secret_eval = context.gateguard.secret_guard.scan_content(args.content, context="proposed write")
        if secret_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Write blocked: {secret_eval.reason}",
            )

        # Existing content
        orig_content = ""
        if resolved_file.exists():
            if not resolved_file.is_file():
                return ToolResult(
                    tool_name=self.name,
                    call_id=call_id,
                    success=False,
                    output="",
                    error=f"Target path '{rel_path}' exists and is not a regular file",
                )
            orig_content = resolved_file.read_text(encoding="utf-8", errors="replace")

        # Determine new content
        if args.original_snippet is not None:
            if args.original_snippet not in orig_content:
                return ToolResult(
                    tool_name=self.name,
                    call_id=call_id,
                    success=False,
                    output="",
                    error=f"Target snippet not found in '{rel_path}'",
                )
            new_content = orig_content.replace(args.original_snippet, args.content, 1)
        else:
            new_content = args.content

        # Compute diff
        diff_str = compute_unified_diff(orig_content, new_content, file_path=rel_path)

        # Interactive approval gate
        if context.interactive:
            approved = request_interactive_approval(
                diff_str,
                file_path=rel_path,
                prompt_callback=context.approval_callback,
            )
            if not approved:
                return ToolResult(
                    tool_name=self.name,
                    call_id=call_id,
                    success=False,
                    output="",
                    error="Change rejected during interactive approval",
                )

        # Session checkpoint backup before modifying
        context.checkpoint.backup_before_write(resolved_file)

        # Write file atomically
        try:
            resolved_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = resolved_file.with_suffix(resolved_file.suffix + ".aegis_tmp")
            temp_file.write_text(new_content, encoding="utf-8")
            temp_file.replace(resolved_file)
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Failed to write file '{rel_path}': {e}",
            )

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output=f"Successfully updated '{rel_path}'.\n\nDiff:\n{diff_str or '[No changes]'}",
            metadata={"diff": diff_str, "file_path": rel_path},
        )


# --- 4. search ---

class SearchArgs(BaseModel):
    query: str = Field(description="Search term or regex pattern")
    directory: str = Field(default=".", description="Directory to search in")
    max_results: int = Field(default=30, description="Maximum matches to return")


class SearchTool(BaseTool):
    name = "search"
    description = "Search repository files for matching text or regex pattern safely."
    permission = ToolPermission.READ
    args_schema = SearchArgs

    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        args = SearchArgs.model_validate(arguments)

        path_eval = context.gateguard.path_guard.evaluate_path(args.directory)
        if path_eval.decision != PolicyDecision.ALLOW:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Access denied: {path_eval.reason}",
            )

        resolved_dir = Path(path_eval.metadata["resolved_path"])
        try:
            pattern = re.compile(args.query, re.IGNORECASE)
        except re.error as e:
            return ToolResult(
                tool_name=self.name,
                call_id=call_id,
                success=False,
                output="",
                error=f"Invalid regex query '{args.query}': {e}",
            )

        matches: list[str] = []
        count = 0

        for root, dirs, files in os.walk(resolved_dir):
            # Prune protected dirs
            safe_dirs = []
            for d in dirs:
                dp = Path(root) / d
                if context.gateguard.path_guard.evaluate_path(dp).decision == PolicyDecision.ALLOW:
                    safe_dirs.append(d)
            dirs[:] = safe_dirs

            for f in files:
                fp = Path(root) / f
                if context.gateguard.path_guard.evaluate_path(fp).decision != PolicyDecision.ALLOW:
                    continue

                try:
                    rel_f = fp.relative_to(context.repo_root)
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                    for idx, line in enumerate(text.splitlines(), start=1):
                        if pattern.search(line):
                            matches.append(f"{rel_f}:{idx}: {line.strip()[:150]}")
                            count += 1
                            if count >= args.max_results:
                                matches.append(f"... (truncated at {args.max_results} results)")
                                return ToolResult(
                                    tool_name=self.name,
                                    call_id=call_id,
                                    success=True,
                                    output="\n".join(matches),
                                    metadata={"match_count": count},
                                )
                except Exception:
                    continue

        return ToolResult(
            tool_name=self.name,
            call_id=call_id,
            success=True,
            output="\n".join(matches) if matches else "No matching files found.",
            metadata={"match_count": count},
        )
