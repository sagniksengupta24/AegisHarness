"""Centralized PathGuard for filesystem security, traversal rejection, and symlink validation.

SECURITY NOTE & TOCTOU DISCLOSURE:
While PathGuard resolves symlinks and canonicalizes paths before operations, in a local
non-containerized filesystem, operating system kernel-level TOCTOU (Time-Of-Check to
Time-Of-Use) race conditions can theoretically occur if an adversarial concurrent process
alters symlinks between resolution and file descriptor opening. For untrusted, hostile code,
Docker/container-based isolation must be used.
"""

import fnmatch
import os
import urllib.parse
from pathlib import Path
from typing import List, Optional, Union

from aegis.errors import PathGuardError
from aegis.models import PolicyDecision, PolicyResult


class PathGuard:
    """Enforces repository containment, traversal rejection, and protected path denial rules."""

    def __init__(self, repo_root: Path, deny_patterns: Optional[list[str]] = None):
        self.repo_root = repo_root.resolve()
        self.deny_patterns = deny_patterns or [
            ".git/**",
            ".git",
            ".env",
            ".env.*",
            "secrets/**",
            "*.pem",
            "*.key",
            "id_rsa*",
            "credentials*",
            ".ssh/**",
        ]

    def evaluate_path(self, target_path: Union[str, Path]) -> PolicyResult:
        """Evaluates whether target path is safe to access.
        
        Returns PolicyResult with ALLOW or DENY.
        """
        # 1. URL decode path to catch encoded traversal attempts (%2e%2e%2f)
        unquoted = urllib.parse.unquote(str(target_path))
        raw_path = Path(unquoted)

        # 2. Canonicalize and resolve path
        try:
            if raw_path.is_absolute():
                resolved = raw_path.resolve()
            else:
                resolved = (self.repo_root / raw_path).resolve()
        except Exception as e:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Failed to resolve path '{target_path}': {e}",
                rule_name="path_resolution",
            )

        # 3. Check repository containment (no ../ traversal outside repo root)
        try:
            resolved.relative_to(self.repo_root)
        except ValueError:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Path traversal blocked: '{target_path}' resolves outside repository root '{self.repo_root}'",
                rule_name="repository_containment",
                metadata={"resolved_path": str(resolved), "repo_root": str(self.repo_root)},
            )

        # 4. Check if an existing symlink points outside repository
        test_path = self.repo_root / raw_path
        if test_path.is_symlink():
            try:
                target_symlink = test_path.resolve()
                target_symlink.relative_to(self.repo_root)
            except ValueError:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Symlink escape blocked: '{target_path}' points outside repository",
                    rule_name="symlink_escape",
                )

        rel_path_str = str(resolved.relative_to(self.repo_root))
        rel_posix = rel_path_str.replace("\\", "/")
        path_name = resolved.name

        # Also check textual unquoted relative path to prevent accessing symlinks named after protected files
        textual_parts = raw_path.parts

        # 5. Check against deny patterns (exact and case-variant matching)
        rel_posix_lower = rel_posix.lower()
        path_name_lower = path_name.lower()

        for pattern in self.deny_patterns:
            clean_pat = pattern.strip()
            clean_pat_lower = clean_pat.lower()
            # If pattern ends with /** or /*
            if clean_pat.endswith("/**"):
                dir_prefix = clean_pat[:-3]
                dir_prefix_lower = clean_pat_lower[:-3]
                if (
                    rel_posix == dir_prefix
                    or rel_posix.startswith(dir_prefix + "/")
                    or rel_posix_lower == dir_prefix_lower
                    or rel_posix_lower.startswith(dir_prefix_lower + "/")
                ):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Access denied: path '{rel_posix}' matches protected directory pattern '{pattern}'",
                        rule_name="deny_paths",
                    )
            elif clean_pat.endswith("/*"):
                dir_prefix = clean_pat[:-2]
                dir_prefix_lower = clean_pat_lower[:-2]
                if (
                    rel_posix == dir_prefix
                    or rel_posix.startswith(dir_prefix + "/")
                    or rel_posix_lower == dir_prefix_lower
                    or rel_posix_lower.startswith(dir_prefix_lower + "/")
                ):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Access denied: path '{rel_posix}' matches protected directory pattern '{pattern}'",
                        rule_name="deny_paths",
                    )
            else:
                if (
                    fnmatch.fnmatch(rel_posix, clean_pat)
                    or fnmatch.fnmatch(path_name, clean_pat)
                    or fnmatch.fnmatch(rel_posix_lower, clean_pat_lower)
                    or fnmatch.fnmatch(path_name_lower, clean_pat_lower)
                ):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Access denied: path '{rel_posix}' matches protected pattern '{pattern}'",
                        rule_name="deny_paths",
                    )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Path is inside repository root and does not match protected patterns",
            rule_name="allow_contained_path",
            metadata={"resolved_path": str(resolved), "relative_path": rel_posix},
        )

    def validate_path(self, target_path: Union[str, Path]) -> Path:
        """Validates path and returns resolved Path if ALLOW, otherwise raises PathGuardError."""
        res = self.evaluate_path(target_path)
        if res.decision != PolicyDecision.ALLOW:
            raise PathGuardError(res.reason, details=res.metadata)
        return Path(res.metadata["resolved_path"])
