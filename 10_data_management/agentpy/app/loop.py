# loop.py
# Multi-turn disaster situational brief loop against Ollama — tools, guardrails, AGENT.md
# Tim Fraser

import json
import logging
import os
import re
import uuid
from typing import Any

import httpx

from .context import build_system_prompt
from .guardrails import (
    MAX_AUTONOMOUS_TURNS,
    MAX_SKILL_READS_PER_REQUEST,
    MAX_WEB_SEARCHES_PER_REQUEST,
    clamp_turns,
    min_completion_turns,
    task_size_ok,
)
from .logging_setup import configure_agent_logging
from .tools import (
    ollama_tool_definitions,
    parse_function_arguments,
    run_read_skill,
    run_web_search,
)

log = logging.getLogger("agent")

# Strip common secret shapes from strings before writing to the agent log file (defense in depth).
# Server env API keys are never passed into log calls; this covers user/model text and error messages.
_BEARER_RE = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-~+/=]{12,}")
_SK_RE = re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b")
_KV_SECRET_RE = re.compile(
    r"(?i)\b(apikey|api_key|authorization|secret|password|token)\s*[=:]\s*\S{8,}"
)

END_MARKER = "END_BRIEF"

# Injected when the model emits END_BRIEF before min LLM rounds (see min_completion_turns()).
_VERIFICATION_NUDGE = (
    "Do **not** finish yet: the server requires more **model rounds** before it accepts END_BRIEF. "
    "Compare **Key points** to **Retrieved URLs for References** (and any **web_search** tool output). "
    "Revise or soften claims that are not clearly supported; call **web_search** again if you need to check a fact. "
    "Then output the **complete** brief again (all sections) and end with a line containing only END_BRIEF."
)


def _redact_for_log(text: object) -> str:
    """Remove likely secrets from text before logging (user task, tool I/O previews, exceptions)."""
    s = str(text) if text is not None else ""
    if not s:
        return s
    s = _BEARER_RE.sub("Bearer [REDACTED]", s)
    s = _SK_RE.sub("[REDACTED]", s)
    s = _KV_SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", s)
    return s


def _preview(text: str, limit: int = 200) -> str:
    s = (text or "").replace("\n", " ").strip()
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def _args_preview(args: dict[str, Any]) -> str:
    try:
        return _preview(json.dumps(args, ensure_ascii=False), 300)
    except (TypeError, ValueError):
        return _preview(str(args), 300)


def _maybe_prefetch_web(task: str, search_left: list[int]) -> str | None:
    """
    One automatic Serper query before the first model call (counts against search cap).
    Disabled when AGENT_PREFETCH_WEB_SEARCH is 0/false/no/off.
    """
    flag = os.getenv("AGENT_PREFETCH_WEB_SEARCH", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return None
    if search_left[0] <= 0:
        return None
    search_left[0] -= 1
    q = (task or "").strip()
    if len(q) > 800:
        q = q[:800]
    return run_web_search(q if q else "disaster emergency situational update")


def _wrap_task_with_prefetch(task: str, prefetch: str | None) -> str:
    if prefetch is None:
        return task
    return (
        "=== Server web preflight (one automatic search for this request) ===\n"
        "Ground **Key points** only in what this block and later **read_skill** / **web_search** "
        "outputs actually contain. Use **`### Retrieved URLs for References`** below to build **`## References`** "
        "(numbered list, verbatim URLs only). "
        "If search is disabled or no URLs are listed, **`## References`** must state that no URLs were retrieved.\n\n"
        f"{prefetch}\n\n"
        "=== Task ===\n"
        f"{task}"
    )


def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    search_left: list[int],
    skill_left: list[int],
) -> str:
    """Run one tool; enforce per-request caps via mutable single-element lists."""
    if name == "web_search":
        if search_left[0] <= 0:
            return (
                "web_search: per-request limit reached; stop calling web_search. "
                "Finish the brief without new URLs or state that search was capped."
            )
        search_left[0] -= 1
        return run_web_search(str(args.get("query", "")))
    if name == "read_skill":
        if skill_left[0] <= 0:
            return (
                "read_skill: per-request limit reached; stop calling read_skill. "
                "Complete the brief from context already in the thread."
            )
        skill_left[0] -= 1
        return run_read_skill(str(args.get("filename", "")))
    return f"Unknown tool {name!r}; use read_skill or web_search only."


def _inject_forced_read_skill_round(
    messages: list[dict[str, Any]],
    search_left: list[int],
    skill_left: list[int],
) -> bool:
    """
    Append a synthetic assistant tool_calls + tool turn so the first LLM call always
    follows a real read_skill execution (counts against MAX_SKILL_READS_PER_REQUEST).

    Ollama may ignore tool_choice; this path is reliable. Disable with AGENT_FORCE_FIRST_TOOL=0.
    """
    flag = os.getenv("AGENT_FORCE_FIRST_TOOL", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    fn = (os.getenv("AGENT_FORCE_FIRST_SKILL") or "disaster_situational_brief.md").strip()
    if not fn:
        fn = "disaster_situational_brief.md"
    if skill_left[0] <= 0:
        return False

    result = _dispatch_tool("read_skill", {"filename": fn}, search_left, skill_left)
    tid = f"forced_read_skill_{uuid.uuid4().hex[:12]}"
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tid,
                    "type": "function",
                    "function": {
                        "name": "read_skill",
                        "arguments": {"filename": fn},
                    },
                }
            ],
        }
    )
    tool_msg: dict[str, Any] = {
        "role": "tool",
        "content": result,
        "name": "read_skill",
        "tool_name": "read_skill",
        "tool_call_id": tid,
    }
    messages.append(tool_msg)
    return True


def _chat_once(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """Single non-streaming /api/chat call (optionally with tools)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "tools": tools,
    }
    if max_tokens is not None:
        body["options"] = {"num_predict": max_tokens}
    url = base_url.rstrip("/") + "/api/chat"
    resp = client.post(url, headers=headers, json=body, timeout=120.0)
    resp.raise_for_status()
    data = resp.json()
    msg = data.get("message") or {}
    content = (msg.get("content") or "")
    if isinstance(content, str):
        content = content.strip()
    else:
        content = str(content).strip()
    return {"content": content, "message": msg, "raw": data}


def run_research_loop(
    task: str,
    *,
    ollama_host: str,
    ollama_api_key: str,
    model: str,
    max_turns: int | None = None,
    max_output_tokens: int | None = None,
    existing_messages: list[dict[str, Any]] | None = None,
    continue_thread: bool = False,
) -> dict[str, Any]:
    """
    Run the disaster situational brief loop until END_BRIEF, turn budget exhausted, or error.

    Each POST /api/chat counts toward the same turn budget (including tool follow-ups).
    `turns_used` is only those LLM calls—not the optional server-side Serper preflight
    (see `prefetch_search_used`) nor the optional forced read_skill injection (see `forced_tool_round`).
    `min_completion_turns` (see guardrails) is the minimum LLM rounds before `END_BRIEF` is accepted; the loop
    may inject a verification user message if the model tries to finish early.
    Web search uses CrewAI SerperDevTool; Ollama handles function calling for read_skill and web_search.
    """
    configure_agent_logging()
    if not task_size_ok(task):
        log.info("run_research_loop rejected task (size/empty)")
        return {
            "status": "error",
            "reply": "",
            "turns_used": 0,
            "prefetch_search_used": False,
            "forced_tool_round": False,
            "min_completion_turns": 1,
            "detail": "Task missing, invalid, or too long (see AGENT_MAX_TASK_CHARS).",
        }

    turns_budget = clamp_turns(max_turns)
    min_done = min(min_completion_turns(), turns_budget)
    fresh_start = existing_messages is None
    system_text = build_system_prompt()

    tools = ollama_tool_definitions()
    search_left = [MAX_WEB_SEARCHES_PER_REQUEST]
    skill_left = [MAX_SKILL_READS_PER_REQUEST]

    prefetch_search_used = False

    if existing_messages is None:
        prefetch_block = _maybe_prefetch_web(task, search_left)
        prefetch_search_used = prefetch_block is not None
        user_content = _wrap_task_with_prefetch(task, prefetch_block)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_content},
        ]
    else:
        messages = [dict(m) for m in existing_messages]
        if continue_thread:
            cont_prefetch = _maybe_prefetch_web(task, search_left)
            prefetch_search_used = cont_prefetch is not None
            user_content = _wrap_task_with_prefetch(task, cont_prefetch)
            messages.append({"role": "user", "content": user_content})

    forced_tool_round = False
    if fresh_start:
        forced_tool_round = _inject_forced_read_skill_round(messages, search_left, skill_left)

    if max_output_tokens is None:
        env_tok = os.getenv("AGENT_MAX_OUTPUT_TOKENS")
        max_output_tokens = int(env_tok) if env_tok and env_tok.isdigit() else 1024

    log.info(
        "loop start task_preview=%s turns_budget=%s min_done=%s prefetch=%s forced_read_skill=%s "
        "search_slots_left=%s skill_slots_left=%s",
        _redact_for_log(_preview(task)),
        turns_budget,
        min_done,
        prefetch_search_used,
        forced_tool_round,
        search_left[0],
        skill_left[0],
    )

    turns_used = 0
    last_content = ""

    with httpx.Client() as client:
        while turns_used < turns_budget:
            turns_used += 1
            log.info("turn %s/%s calling Ollama model=%s", turns_used, turns_budget, model)
            try:
                out = _chat_once(
                    client,
                    ollama_host,
                    ollama_api_key,
                    model,
                    messages,
                    max_output_tokens,
                    tools,
                )
            except Exception as exc:  # noqa: BLE001 — surface model/HTTP errors to API layer
                log.warning("turn %s Ollama error: %s", turns_used, _redact_for_log(exc))
                return {
                    "status": "error",
                    "reply": last_content,
                    "turns_used": turns_used,
                    "prefetch_search_used": prefetch_search_used,
                    "forced_tool_round": forced_tool_round,
                    "min_completion_turns": min_done,
                    "detail": str(exc),
                }

            msg = out.get("message") or {}
            # Shallow copy so later edits to messages do not mutate response object quirks
            assistant_msg = dict(msg)
            messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls") or []
            if tool_calls:
                log.info("turn %s assistant tool_calls count=%s", turns_used, len(tool_calls))
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function")
                    if not isinstance(fn, dict):
                        fn = {}
                    name = str(fn.get("name") or "")
                    args = parse_function_arguments(fn.get("arguments"))
                    log.info(
                        "turn %s tool %s args=%s",
                        turns_used,
                        name,
                        _redact_for_log(_args_preview(args)),
                    )
                    result = _dispatch_tool(name, args, search_left, skill_left)
                    log.info(
                        "turn %s tool %s result_len=%s preview=%s",
                        turns_used,
                        name,
                        len(result),
                        _redact_for_log(_preview(result, 120)),
                    )
                    tool_message: dict[str, Any] = {"role": "tool", "content": result}
                    if name:
                        tool_message["name"] = name
                    tid = tc.get("id")
                    if tid:
                        tool_message["tool_call_id"] = tid
                    if name:
                        tool_message["tool_name"] = name
                    messages.append(tool_message)
                continue

            last_content = out["content"]
            log.info(
                "turn %s assistant text_len=%s end_brief=%s preview=%s",
                turns_used,
                len(last_content),
                END_MARKER in last_content,
                _redact_for_log(_preview(last_content, 160)),
            )
            if END_MARKER in last_content:
                if turns_used < min_done:
                    log.info(
                        "turn %s END_BRIEF before min_done (%s); injecting verification nudge",
                        turns_used,
                        min_done,
                    )
                    messages.append({"role": "user", "content": _VERIFICATION_NUDGE})
                    continue
                cleaned = last_content.replace(END_MARKER, "").strip()
                log.info("loop finished ok turns_used=%s", turns_used)
                return {
                    "status": "ok",
                    "reply": cleaned,
                    "turns_used": turns_used,
                    "prefetch_search_used": prefetch_search_used,
                    "forced_tool_round": forced_tool_round,
                    "min_completion_turns": min_done,
                    "messages": messages,
                }

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Continue and complete the disaster situational brief. "
                        "When finished, end with a line containing only END_BRIEF."
                    ),
                }
            )

    resume_token = str(uuid.uuid4())
    log.info("loop paused_for_human turns_used=%s budget=%s", turns_used, turns_budget)
    return {
        "status": "paused_for_human",
        "reply": last_content,
        "turns_used": turns_used,
        "prefetch_search_used": prefetch_search_used,
        "forced_tool_round": forced_tool_round,
        "min_completion_turns": min_done,
        "resume_token": resume_token,
        "messages": messages,
        "detail": (
            f"Model did not finish within {turns_budget} turns in this request; "
            "send the same session_id with resume_token and a short continuation task."
        ),
    }
