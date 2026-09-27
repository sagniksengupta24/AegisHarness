"""Centralized PathGuard for filesystem security and traversal rejection."""

import fnmatch
from pathlib import Path
from typing import List, Optional, Union

from aegis.errors import PathGuardError
from aegis.models import PolicyDecision, PolicyResult


class PathGuard:
    """Enforces repository containment and protected path denial rules."""

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
        raw_path = Path(target_path)
        
        # Check containment
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

        # Check repository containment (no ../ traversal outside repo root)
        try:
            resolved.relative_to(self.repo_root)
        except ValueError:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Path traversal blocked: '{target_path}' resolves outside repository root '{self.repo_root}'",
                rule_name="repository_containment",
                metadata={"resolved_path": str(resolved), "repo_root": str(self.repo_root)},
            )

        rel_path_str = str(resolved.relative_to(self.repo_root))
        rel_posix = rel_path_str.replace("\\", "/")
        path_name = resolved.name

        # Check against deny patterns
        for pattern in self.deny_patterns:
            clean_pat = pattern.strip()
            # If pattern ends with /** or /*
            if clean_pat.endswith("/**"):
                dir_prefix = clean_pat[:-3]
                if rel_posix == dir_prefix or rel_posix.startswith(dir_prefix + "/"):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Access denied: path '{rel_posix}' matches protected directory pattern '{pattern}'",
                        rule_name="deny_paths",
                    )
            elif clean_pat.endswith("/*"):
                dir_prefix = clean_pat[:-2]
                if rel_posix == dir_prefix or rel_posix.startswith(dir_prefix + "/"):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Access denied: path '{rel_posix}' matches protected directory pattern '{pattern}'",
                        rule_name="deny_paths",
                    )
            else:
                if fnmatch.fnmatch(rel_posix, clean_pat) or fnmatch.fnmatch(path_name, clean_pat):
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
