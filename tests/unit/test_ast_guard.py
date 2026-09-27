"""Unit tests for AST risk scanner."""

from aegis.guard.ast import scan_python_code
from aegis.models import PolicyDecision


def test_clean_python_code():
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    res = scan_python_code(code)
    assert res.decision == PolicyDecision.ALLOW


def test_eval_detected():
    code = """
def run_expr(expr):
    return eval(expr)
"""
    res = scan_python_code(code)
    assert res.decision == PolicyDecision.REVIEW
    assert "eval" in res.reason


def test_exec_detected():
    code = """
exec("import os; os.system('ls')")
"""
    res = scan_python_code(code)
    assert res.decision == PolicyDecision.REVIEW
    assert "exec" in res.reason


def test_builtins_tampering_detected():
    code = """
__builtins__["print"] = lambda x: None
"""
    res = scan_python_code(code)
    assert res.decision == PolicyDecision.REVIEW
    assert "__builtins__" in res.reason
