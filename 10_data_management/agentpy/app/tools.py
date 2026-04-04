# tools.py
# CrewAI SerperDevTool for web search + read_skill helpers for Ollama tool calling
# Tim Fraser

import json
import os
import re
from typing import Any

from crewai_tools import SerperDevTool

from .guardrails import read_skill_file

# Keep tool payloads small so the chat context stays bounded.
MAX_TOOL_OUTPUT_CHARS = 4000

_URL_IN_TEXT = re.compile(r"https?://[^\s\)\]\"'<>]+", re.I)


def _extract_urls_from_text(text: str) -> list[str]:
    """Ordered unique URLs from free text (fallback when result is not JSON)."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _URL_IN_TEXT.finditer(text or ""):
        u = m.group(0).rstrip(".,;)]>\"'")
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= 10:
            break
    return out


def _title_url_pairs_from_raw(raw: str) -> list[tuple[str, str]]:
    """
    Build (title, url) from Serper-style JSON if present; else one tuple per URL found in text.
    """
    text = (raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            organic = data.get("organic")
            if isinstance(organic, list):
                pairs: list[tuple[str, str]] = []
                for item in organic[:10]:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("link", "")).strip()
                    if not url:
                        continue
                    title = str(item.get("title", "")).strip() or url
                    pairs.append((title, url))
                if pairs:
                    return pairs
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    urls = _extract_urls_from_text(text)
    return [(u, u) for u in urls]


def _reference_block_for_model(pairs: list[tuple[str, str]]) -> str:
    """Explicit block the model must mirror under ## References."""
    lines = [
        "### Retrieved URLs for References",
        "",
        "_Every URL below is safe to cite. Copy each **URL** exactly into your `## References` section "
        "(numbered list). Do not add URLs that are not listed here or in another search block in this thread._",
        "",
    ]
    if not pairs:
        lines.append(
            "_No URLs were extracted from this search output. In `## References` write exactly one line: "
            "**No URLs retrieved from search results.** Do not invent links._"
        )
        return "\n".join(lines)
    for i, (title, url) in enumerate(pairs, 1):
        lines.append(f"{i}. **{title}**")
        lines.append(f"   - URL (verbatim): `{url}`")
    lines.append("")
    lines.append("_In the brief: `## References` must list the same URLs (markdown links or bare URLs)._")
    return "\n".join(lines)


def _assemble_search_payload(ref_block: str, body: str) -> str:
    """Put the reference block first so truncation keeps URLs when possible."""
    body = (body or "").strip()
    if not body:
        return _truncate(ref_block)
    combined = ref_block + "\n\n### Search tool output (raw)\n\n" + body
    return _truncate(combined)


def ollama_tool_definitions() -> list[dict[str, Any]]:
    """OpenAI-style tool specs for Ollama /api/chat."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_skill",
                "description": (
                    "Load a markdown skill from the skills/ folder (disaster briefs, sourcing rules). "
                    "Exact basename only (e.g. disaster_situational_brief.md, references_section.md)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename only, must end with .md",
                        },
                    },
                    "required": ["filename"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the web for current disaster or incident reporting. "
                    "If search is disabled, the result explains that—do not invent URLs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Focused query: event name, location, date or 'today', "
                                "optional keywords (evacuation, outage, shelter, OEM)."
                            ),
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    ]


def parse_function_arguments(raw: Any) -> dict[str, Any]:
    """Ollama may return function.arguments as a dict or a JSON string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _truncate(s: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 20] + "\n...[truncated]"


def run_read_skill(filename: str) -> str:
    """Return skill markdown or a short error string (never raises)."""
    try:
        text = read_skill_file(filename.strip())
    except ValueError as exc:
        return f"read_skill error: {exc}"
    return _truncate(text)


def run_web_search(query: str) -> str:
    """
    Web search via CrewAI **SerperDevTool** (Serper API). Requires **SERPER_API_KEY**.
    Prepends a **Retrieved URLs for References** block so the model can copy real links.
    """
    key = (os.getenv("SERPER_API_KEY") or "").strip()
    if not key:
        return (
            "Web search is disabled: SERPER_API_KEY is not set on the server. "
            "Do not invent URLs; use your training data and state low confidence.\n\n"
            "### Retrieved URLs for References\n\n"
            "_Search is **disabled**. In `## References` write exactly one numbered item: "
            "**No URLs retrieved from live search in this session (search disabled).** "
            "Do not add any http(s) links._\n"
        )
    q = (query or "").strip()
    if not q:
        return "web_search error: empty query."

    try:
        tool = SerperDevTool(n_results=5)
        raw = tool.run(search_query=q)
    except Exception as exc:  # noqa: BLE001 — tool output is user-facing text
        return f"web_search error: {exc}"

    body = (str(raw).strip() if raw is not None else "") or "(No results.)"
    pairs = _title_url_pairs_from_raw(body)
    ref_block = _reference_block_for_model(pairs)
    return _assemble_search_payload(ref_block, body)
