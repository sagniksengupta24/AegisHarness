"""Live integration smoke test for Gemini API using google-genai SDK.

Executed ONLY when GEMINI_API_KEY is configured in the environment.
Strictly skipped when credentials are absent (not live-tested).
"""

import os
import time
from pathlib import Path
import pytest

from aegis.client import GeminiModelClient
from aegis.tools.fs import ViewTreeTool
from aegis.tools.base import ToolContext
from aegis.guard import GateGuard
from aegis.session.checkpoint import SessionCheckpoint


def test_gemini_live_tool_calling_smoke(tmp_path: Path):
    """Executes a real live request to Gemini API with tool declaration and multi-turn execution."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("GEMINI_API_KEY not configured in environment; live Gemini test skipped (classified: NOT LIVE-TESTED)")

    start_time = time.perf_counter()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    # 1. Initialize client
    client = GeminiModelClient(api_key=api_key, model_name=model_name)

    # 2. Setup safe tool
    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(repo_root=tmp_path, gateguard=gateguard, executor=None, checkpoint=checkpoint)
    tree_tool = ViewTreeTool()

    tools_decl = [
        {
            "name": "view_tree",
            "description": "Inspect repository file structure",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Relative directory path"},
                },
            },
        }
    ]

    # 3. Reach Gemini with tool declaration
    prompt = "Please use the view_tree tool to inspect the current repository directory."
    messages = [{"role": "user", "content": prompt}]

    resp1 = client.generate(messages, tools=tools_decl)
    req1_latency = time.perf_counter() - start_time

    assert resp1 is not None, "Failed to receive response from Gemini"
    assert len(resp1.tool_calls) >= 1, "Gemini did not return requested tool call"

    tc = resp1.tool_calls[0]
    assert tc.name == "view_tree"

    # 4. Execute the safe Aegis tool
    tool_exec_start = time.perf_counter()
    tool_res = tree_tool.execute(tc.arguments, ctx, tc.id)
    assert tool_res.success is True

    # 5. Return tool result back to Gemini in second turn
    messages.append({
        "role": "model",
        "content": resp1.text or "",
        "tool_calls": [tc],
        "raw_parts": resp1.raw_parts,
    })
    messages.append({
        "role": "tool",
        "tool_name": tc.name,
        "output": tool_res.output,
        "success": True,
    })

    t2_start = time.perf_counter()
    resp2 = client.generate(messages, tools=tools_decl)
    total_latency = time.perf_counter() - start_time

    assert resp2 is not None
    assert resp2.text is not None and len(resp2.text) > 0

    # 6. Record metadata without printing API key
    record = {
        "model": model_name,
        "request_success": True,
        "tool_call_success": True,
        "first_turn_latency_ms": int(req1_latency * 1000),
        "total_latency_ms": int(total_latency * 1000),
        "final_status": "VERIFIED_LIVE",
    }
    print(f"\n[Gemini Live Smoke Test Metrics]: {record}")
