"""Static AST Risk Scanner for Python code modifications."""

import ast
from typing import Optional

from aegis.models import PolicyDecision, PolicyResult


class ASTRiskScanner(ast.NodeVisitor):
    """Inspects Python Abstract Syntax Trees for high-risk dynamic primitives."""

    def __init__(self):
        self.findings: list[tuple[str, int, str]] = []  # (risk_type, lineno, detail)

    def visit_Call(self, node: ast.Call):
        # Check direct calls: eval, exec, compile, __import__
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ("eval", "exec"):
                self.findings.append(("HIGH_RISK_CALL", node.lineno, f"Dynamic code execution via '{func_name}'"))
            elif func_name == "__import__":
                self.findings.append(("HIGH_RISK_CALL", node.lineno, "Dynamic import via '__import__'"))

        # Check os.system, subprocess calls
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name == "system" and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                self.findings.append(("HIGH_RISK_CALL", node.lineno, "Shell execution via 'os.system'"))

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Check access to __builtins__ manipulation
        if node.attr == "__builtins__":
            self.findings.append(("SUSPICIOUS_ACCESS", node.lineno, "Direct manipulation of '__builtins__'"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id == "__builtins__":
            self.findings.append(("SUSPICIOUS_ACCESS", node.lineno, "Access or modification of '__builtins__'"))
        self.generic_visit(node)


def scan_python_code(code_str: str, file_path: Optional[str] = None) -> PolicyResult:
    """Scans Python code string for high-risk AST patterns."""
    try:
        tree = ast.parse(code_str, filename=file_path or "<patch>")
    except SyntaxError:
        # Non-Python or syntax error in patch (could be unified diff or snippet)
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Syntax not parseable as standalone Python AST (skipped AST scan)",
            rule_name="ast_skip_non_python",
        )

    scanner = ASTRiskScanner()
    scanner.visit(tree)

    if scanner.findings:
        details = [f"Line {lineno}: {msg}" for _, lineno, msg in scanner.findings]
        reason = f"AST risk detector flagged suspicious constructs: {'; '.join(details)}"
        return PolicyResult(
            decision=PolicyDecision.REVIEW,
            reason=reason,
            rule_name="ast_risk_detected",
            metadata={"findings": details},
        )

    return PolicyResult(
        decision=PolicyDecision.ALLOW,
        reason="No high-risk AST patterns detected",
        rule_name="ast_scan_passed",
    )
