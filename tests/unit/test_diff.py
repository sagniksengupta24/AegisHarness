"""Unit tests for diff computation and colorization."""

from aegis.diff.engine import colorize_diff, compute_unified_diff


def test_unified_diff_generation():
    orig = "line 1\nline 2\nline 3\n"
    new = "line 1\nline 2 modified\nline 3\n"
    diff = compute_unified_diff(orig, new, file_path="sample.py")
    assert "--- a/sample.py" in diff
    assert "+++ b/sample.py" in diff
    assert "-line 2" in diff
    assert "+line 2 modified" in diff


def test_colorize_diff():
    diff = "--- a/sample.py\n+++ b/sample.py\n-old\n+new\n"
    colored = colorize_diff(diff)
    assert "\033[31m-old\033[0m" in colored
    assert "\033[32m+new\033[0m" in colored
