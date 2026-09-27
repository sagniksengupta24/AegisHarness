"""Model provider abstraction, Gemini client adapter, and deterministic test double."""

import json
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field

from aegis.errors import ModelError
from aegis.logging import get_logger
from aegis.models import FailureDiagnosis, Plan, ToolCallRequest

logger = get_logger("aegis.client")


class ModelResponse(BaseModel):
    """Normalized response produced by any ModelClient implementation."""
    text: Optional[str] = None
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    plan: Optional[Plan] = None
    diagnosis: Optional[FailureDiagnosis] = None
    is_proposing_completion: bool = False
    raw_response: Optional[Any] = None
    raw_parts: Optional[Any] = None


class ModelClient(Protocol):
    """Protocol for LLM providers communicating with Aegis orchestrator."""

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> ModelResponse:
        """Generates the next model turn given conversation history and available tools."""
        ...


class GeminiModelClient:
    """Production Gemini adapter utilizing the official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ModelError(
                "Gemini API key is required. Set the GEMINI_API_KEY environment variable "
                "or configure it in .aegis.yaml."
            )
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self.temperature = temperature

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise ModelError(f"Failed to initialize google-genai Client: {e}") from e

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> ModelResponse:
        """Sends generation request to Gemini with tool definitions."""
        from google.genai import types

        # Build tools config
        genai_tools = []
        if tools:
            function_declarations = []
            for t in tools:
                function_declarations.append(types.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=t.get("parameters"),
                ))
            genai_tools.append(types.Tool(function_declarations=function_declarations))

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            system_instruction=system_instruction,
            tools=genai_tools if genai_tools else None,
        )

        # Convert generic message structure to Gemini contents
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content_text = msg.get("content", "")
            if role == "system":
                continue

            parts = []
            if role == "tool":
                tool_name = msg.get("tool_name", "tool")
                output_val = msg.get("output", content_text)
                parts.append(types.Part.from_function_response(
                    name=tool_name,
                    response={"result": output_val, "success": msg.get("success", True)},
                ))
                contents.append(types.Content(role="user", parts=parts))
            elif role == "model":
                raw_parts = msg.get("raw_parts")
                if raw_parts:
                    contents.append(types.Content(role="model", parts=list(raw_parts)))
                else:
                    if content_text:
                        parts.append(types.Part.from_text(text=str(content_text)))
                    for tc in msg.get("tool_calls", []):
                        tc_name = getattr(tc, "name", tc.get("name") if isinstance(tc, dict) else "")
                        tc_args = getattr(tc, "arguments", tc.get("arguments") if isinstance(tc, dict) else {})
                        if tc_name:
                            parts.append(types.Part.from_function_call(name=tc_name, args=tc_args))
                    if parts:
                        contents.append(types.Content(role="model", parts=parts))
            else:
                if content_text:
                    parts.append(types.Part.from_text(text=str(content_text)))
                contents.append(types.Content(role="user", parts=parts or [types.Part.from_text(text="")]))

        resp = None
        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
                break
            except Exception as e:
                import re
                import time
                err_msg = str(e).lower()
                is_quota = any(k in err_msg for k in ("429", "resource_exhausted", "rate limit", "quota"))
                is_overload = any(k in err_msg for k in ("503", "unavailable", "high demand", "temporarily"))
                is_transient = is_quota or is_overload
                if is_transient and attempt < max_attempts:
                    if is_quota:
                        # Use API-provided retryDelay hint when available
                        m = re.search(r"retry(?:\s+in)?\s+([0-9]+(?:\.[0-9]+)?)s?", err_msg)
                        base_delay = float(m.group(1)) if m else (2.0 ** attempt)
                        delay = min(base_delay + 1.0, 60.0)
                    else:
                        # 503 overload: exponential backoff with jitter (15s base)
                        import random
                        delay = min(15.0 * (2 ** (attempt - 1)) + random.uniform(0, 5), 90.0)
                    logger.warning(
                        "Transient API error on attempt %d/%d (%s). Retrying in %.1fs.",
                        attempt, max_attempts, "quota" if is_quota else "overload", delay,
                    )
                    time.sleep(delay)
                    continue
                raise ModelError(f"Gemini API error during generate_content: {e}") from e

        # Parse response
        parsed_text = resp.text if hasattr(resp, "text") else ""
        tool_calls: list[ToolCallRequest] = []
        raw_parts = None
        if hasattr(resp, "candidates") and resp.candidates:
            cand = resp.candidates[0]
            if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                raw_parts = cand.content.parts

        if hasattr(resp, "function_calls") and resp.function_calls:
            for fc in resp.function_calls:
                call_id = f"call_{uuid.uuid4().hex[:8]}"
                tool_calls.append(ToolCallRequest(
                    id=call_id,
                    name=fc.name,
                    arguments=dict(fc.args) if fc.args else {},
                ))

        is_proposing_completion = False
        if parsed_text and any(w in parsed_text.upper() for w in ("TASK_COMPLETE", "TASK COMPLETED", "VERIFICATION PASSED")):
            is_proposing_completion = True

        return ModelResponse(
            text=parsed_text,
            tool_calls=tool_calls,
            is_proposing_completion=is_proposing_completion,
            raw_response=resp,
            raw_parts=raw_parts,
        )


class FakeModelClient:
    """Deterministic scriptable model client for automated testing and scenario simulation."""

    def __init__(self, responses: Optional[list[ModelResponse]] = None):
        self.responses: list[ModelResponse] = list(responses or [])
        self.call_history: list[dict[str, Any]] = []
        self.script_handler: Optional[Callable[[list[dict[str, Any]]], ModelResponse]] = None

    def add_response(self, response: ModelResponse) -> None:
        self.responses.append(response)

    def set_script_handler(self, handler: Callable[[list[dict[str, Any]]], ModelResponse]) -> None:
        self.script_handler = handler

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> ModelResponse:
        self.call_history.append({
            "messages": messages,
            "tools": tools,
            "system_instruction": system_instruction,
        })

        if self.script_handler:
            return self.script_handler(messages)

        if not self.responses:
            # Fallback response
            return ModelResponse(
                text="Default fake model response (no scripted response remaining)",
                is_proposing_completion=True,
            )

        return self.responses.pop(0)


# Provider-neutral architectural aliases
ModelProvider = ModelClient
GeminiProvider = GeminiModelClient
FakeProvider = FakeModelClient
