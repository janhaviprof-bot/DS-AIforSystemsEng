# testme.py
# Smoke test Ollama Cloud chat from the fixer folder (no tools)
# Tim Fraser

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

from pathlib import Path

_FIXER_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_FIXER_ROOT))


def resolve_fixer_root() -> Path:
    r = os.environ.get("FIXER_ROOT", "").strip()
    if r and Path(r).is_dir():
        return Path(r).resolve()
    wd = Path.cwd().resolve()
    if (wd / "functions.py").is_file() or (wd / "functions.R").is_file():
        return wd
    cand = wd / "10_data_management" / "fixer"
    if (cand / "functions.py").is_file():
        return cand.resolve()
    raise SystemExit("Run from fixer/, dsai repo root, or set FIXER_ROOT.")


from functions import ollama_chat_once

FIXER_ROOT = resolve_fixer_root()
env_path = FIXER_ROOT / ".env"
if env_path.is_file():
    load_dotenv(env_path)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com").strip()
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "").strip()
if not OLLAMA_MODEL:
    OLLAMA_MODEL = "gpt-oss:120b"

if not OLLAMA_API_KEY:
    raise SystemExit("Set OLLAMA_API_KEY in fixer/.env (copy from .env.example).")

messages = [
    {"role": "user", "content": "Reply with exactly one word: pong"},
]

print(f"Test query: POST {OLLAMA_HOST}/api/chat")
print(f"Model: {OLLAMA_MODEL}\n")

try:
    out = ollama_chat_once(
        OLLAMA_HOST,
        OLLAMA_API_KEY,
        OLLAMA_MODEL,
        messages,
        tools=None,
        format=None,
        max_output_tokens=None,
    )
except Exception as e:
    try:
        # httpx stores last response on exception in some cases
        if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
            print("HTTP status:", e.response.status_code)
            print("Response body:\n", e.response.text)
    except Exception:
        pass
    raise SystemExit(str(e)) from e

print("Assistant content:\n", out.get("content", ""), "\n", sep="")
print("Smoke test OK.")
