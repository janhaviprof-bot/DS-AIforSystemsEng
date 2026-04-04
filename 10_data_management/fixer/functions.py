# functions.py
# Shared fixer helpers: Ollama /api/chat (httpx) + tool-call JSON parsing + table chunking.
# Imported by fixer_csv.py, fixer_parcels.py, fixer_pois.py, fixer_spatial_context.py, testme.py.
# Tim Fraser

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pandas as pd


def resolve_fixer_root() -> Path:
    """Match testme.R: FIXER_ROOT env, else cwd if helpers exist, else cwd/10_data_management/fixer."""
    r = os.environ.get("FIXER_ROOT", "").strip()
    if r and Path(r).is_dir():
        return Path(r).resolve()
    wd = Path.cwd().resolve()
    if (wd / "functions.py").is_file() or (wd / "functions.R").is_file():
        return wd
    cand = wd / "10_data_management" / "fixer"
    if (cand / "functions.py").is_file():
        return cand.resolve()
    raise RuntimeError("Run from fixer/, dsai repo root, or set FIXER_ROOT.")


def split_df_into_row_chunks(df: pd.DataFrame, n_rows: int) -> list[pd.DataFrame]:
    """Split into consecutive row slices of size n_rows (same semantics as functions.R)."""
    nr = len(df)
    if nr == 0:
        return []
    try:
        n = int(n_rows)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    out: list[pd.DataFrame] = []
    s = 0
    while s < nr:
        e = min(s + n, nr)
        out.append(df.iloc[s:e].copy())
        s = e
    return out


def ollama_chat_once(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    format: str | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Single chat completion. Pass tools for tool-calling; pass format='json' for JSON mode."""
    url = base_url.rstrip("/") + "/api/chat"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools is not None and len(tools) > 0:
        body["tools"] = tools
    if format is not None and str(format).strip():
        body["format"] = str(format)
    if max_output_tokens is not None:
        body["options"] = {"num_predict": int(max_output_tokens)}

    headers = {"Content-Type": "application/json"}
    ak = (api_key or "").strip()
    if ak:
        headers["Authorization"] = f"Bearer {ak}"

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    msg = data.get("message") or {}
    content = msg.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = str(content)
    content = content.strip()
    return {"content": content, "message": msg, "raw": data}


def parse_function_arguments(raw: Any) -> dict[str, Any]:
    """Parse tool function.arguments (string JSON or dict) into a dict."""
    if raw is None:
        return {}
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


def truncate_tool_output(s: Any, limit: int = 12000) -> str:
    """Shorten long tool outputs for the model thread."""
    t = "" if s is None else str(s)
    lim = int(limit)
    if len(t) <= lim:
        return t
    return t[: max(0, lim - 30)] + "\n...[truncated]"
