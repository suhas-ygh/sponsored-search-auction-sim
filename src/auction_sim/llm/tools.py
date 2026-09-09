"""Minimal provider-agnostic tool loop.

Instead of relying on any provider's function-calling API, the model speaks a
tiny JSON protocol: each turn it returns exactly one JSON object, either
{"call": {"tool": name, "arguments": {...}}} or {"answer": "..."}.
Malformed output and tool errors are fed back so the model can self-correct.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON-schema-ish, shown to the model
    func: Callable[..., dict]


@dataclass
class Step:
    kind: str  # "assistant" | "tool"
    text: str = ""
    tool_name: str | None = None
    arguments: dict | None = None
    result: dict | None = None


@dataclass
class LoopResult:
    steps: list[Step] = field(default_factory=list)
    answer: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # {"tool","arguments","result"}


PROTOCOL = """\
You communicate in JSON only. Every message you send must be exactly one JSON
object, no other text, in one of these two shapes:

1. To call a tool:
   {"call": {"tool": "<tool name>", "arguments": {<args matching the schema>}}}
2. When you are done:
   {"answer": "<your final response>"}

If a tool returns {"error": ...}, fix your arguments and retry. Never invent \
tool results."""


def _describe_tools(tools: list[Tool]) -> str:
    lines = []
    for t in tools:
        lines.append(
            f"- {t.name}: {t.description}\n  parameters: {json.dumps(t.parameters)}"
        )
    return "\n".join(lines)


def _parse_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        return json.loads(raw[start:end + 1])
    raise ValueError("no JSON object found")


def run_tool_loop(client: Any, tools: list[Tool], system: str,
                  user_message: str, max_steps: int = 8) -> LoopResult:
    tool_map = {t.name: t for t in tools}
    full_system = (f"{system}\n\n## Available tools\n{_describe_tools(tools)}"
                   f"\n\n## Protocol\n{PROTOCOL}")
    messages = [{"role": "user", "content": user_message}]
    result = LoopResult()

    for _ in range(max_steps):
        raw = client.complete(messages, system=full_system)
        result.steps.append(Step(kind="assistant", text=raw))

        try:
            obj = _parse_json(raw)
        except (ValueError, json.JSONDecodeError):
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                             "That was not valid JSON. Reply with exactly one "
                             "JSON object using the protocol."})
            continue

        if isinstance(obj, dict) and "answer" in obj:
            result.answer = str(obj["answer"])
            messages.append({"role": "assistant", "content": raw})
            return result

        call = obj.get("call") if isinstance(obj, dict) else None
        if not isinstance(call, dict) or "tool" not in call:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                             'Use {"call": {...}} to call a tool or '
                             '{"answer": "..."} to finish.'})
            continue

        name, args = call["tool"], call.get("arguments", {}) or {}
        tool = tool_map.get(name)
        if tool is None:
            tool_result: dict = {"error": f"unknown tool {name!r}"}
        elif not isinstance(args, dict):
            tool_result = {"error": "arguments must be a JSON object"}
        else:
            try:
                tool_result = tool.func(**args)
                if not isinstance(tool_result, dict):
                    tool_result = {"result": tool_result}
            except Exception as e:  # noqa: BLE001 - fed back to the model
                tool_result = {"error": f"{type(e).__name__}: {e}"}

        result.tool_calls.append({"tool": name, "arguments": args,
                                  "result": tool_result})
        result.steps.append(Step(kind="tool", tool_name=name,
                                 arguments=args, result=tool_result))
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content":
                         f"Tool {name} returned:\n{json.dumps(tool_result)}"})

    raise RuntimeError(f"Tool loop did not finish within {max_steps} steps")
