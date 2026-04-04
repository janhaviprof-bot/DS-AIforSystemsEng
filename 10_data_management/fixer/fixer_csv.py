# fixer_csv.py
# Batched CSV repair — one Ollama round per N rows + ThreadPoolExecutor chunk parallelism
# Tim Fraser

from __future__ import annotations

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from functions import (
    ollama_chat_once,
    parse_function_arguments,
    split_df_into_row_chunks,
)

# 0. SETUP ###################################

print()
print("=================================================================")
print("📋 fixer_csv.py — batched tool calls + ThreadPoolExecutor (Ollama Cloud)")
print("=================================================================\n")

print("📦 Loading Python packages (pandas, httpx, dotenv) ...")
print("   ✅ Packages ready.\n")

FIXER_ROOT = Path(__file__).resolve().parent
os.chdir(FIXER_ROOT)
print("📁 Resolving fixer folder and paths ...")
print(f"   📍 FIXER_ROOT: {FIXER_ROOT}")

RAW_PATH = FIXER_ROOT / "data" / "messy_inventory_raw.csv"
WORK_PATH = FIXER_ROOT / "output" / "messy_inventory_working.csv"
LOG_PATH = FIXER_ROOT / "output" / "fix_audit.jsonl"
print(f"   📄 Raw data:     {RAW_PATH}")
print(f"   💾 Working copy: {WORK_PATH}")
print(f"   📝 Audit log:    {LOG_PATH}\n")

env_path = FIXER_ROOT / ".env"
print("🔐 Loading .env ...")
if env_path.is_file():
    load_dotenv(env_path)
else:
    raise SystemExit(
        "No .env in fixer folder; create one with OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL."
    )
print("   ✅ .env read from fixer folder.\n")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com").strip()
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "nemotron-3-nano:30b-cloud").strip()
print(f"☁️  Ollama: host = {OLLAMA_HOST}")
print(f"   model  = {OLLAMA_MODEL}")
if OLLAMA_API_KEY:
    ak_show = f"{OLLAMA_API_KEY[:4]}...{OLLAMA_API_KEY[-1]}"
else:
    ak_show = "(empty)"
print(f"   API key (masked): {ak_show}\n")


def read_env_digits(name: str, default: int) -> int:
    s = os.environ.get(name, str(default)).strip()
    if s.isdigit():
        v = int(s)
        if v >= 1:
            return v
    return default


ROWS_PER_BATCH = read_env_digits("ROWS_PER_BATCH", 10)
FIXER_CHUNK_WORKERS = read_env_digits("FIXER_CHUNK_WORKERS", 1)
print(f"📊 ROWS_PER_BATCH = {ROWS_PER_BATCH} (env ROWS_PER_BATCH)")
print(f"📊 FIXER_CHUNK_WORKERS = {FIXER_CHUNK_WORKERS} (env FIXER_CHUNK_WORKERS)\n")

print("🔌 Importing fixer/functions.py ...")
print("   ✅ Helpers loaded.\n")

et = os.environ.get("FIXER_MAX_OUTPUT_TOKENS", "").strip()
MAX_OUT: int | None = int(et) if et.isdigit() else None

DATA_QUALITY_BLURB = (
    "## What this table is\n"
    "Each row is one **SKU** line in a **store inventory**: how many units are on hand, when it was last restocked, and a high-level **category** (electronics vs food). "
    "Columns are **not interchangeable**—do not move dates into qty, or category words into qty, or invent numbers.\n\n"
    "## Column meanings (edit only the cell that matches the column’s meaning)\n"
    "- **row_id**: stable row key. **Never** call set_cell on row_id.\n"
    "- **sku**: product code. **Do not** edit unless an obvious duplicate typo is requested (default: leave sku unchanged).\n"
    "- **qty_on_hand**: **stock count** as **digits only**—**positive** integers or **empty**; **`0` counts as missing** → empty. "
    "This is **not** a date column, **not** a category column, **not** a free-text field.\n"
    "- **last_restock**: calendar date of last restock, **YYYY-MM-DD** only, OR **empty** if invalid/unknown.\n"
    "- **category**: **exactly** one of **`Electronics`** or **`Food`** (those spellings, title case).\n\n"
    "## Missing values (critical)\n"
    "The tool only accepts text. For “missing / NA / unknown / invalid after cleaning”, set **new_value to an empty string** `\"\"` (nothing between the quotes). "
    "**Forbidden** as new_value: the literal text **NaN**, **nan**, **NULL**, **null**, **N/A**, or the two letters **NA**—those are wrong; use **empty string** instead. "
    "Examples: messy **N/A**, **n/a**, **unknown** in **qty_on_hand** → **empty string**, not \"NaN\". Sentinel **-99999** in qty → **empty string**. For this inventory table, **`0` in qty_on_hand is a placeholder / unknown count**—set **empty string**, do **not** leave `\"0\"`.\n\n"
    "## qty_on_hand rules\n"
    "- Allowed: **positive** integer as digits (`1`,`12`,…) OR **empty**. (**`0` → empty** for this exercise.)\n"
    "- Strip unit words: `\"3 units\"`→`\"3\"`, `\"12 pcs\"`→`\"12\"`.\n"
    "- **Spaced digits = concatenate only, in order**—remove spaces between digit characters and **nothing else**: `\"1 1\"`→`\"11\"`; `\"1 2 3\"`→`\"123\"`; `\"2 0\"`→`\"20\"`; `\"1 5 0\"`→`\"150\"`. "
    "The new digits must be **exactly** the digits you see, left to right. **Forbidden**: inventing a different number (e.g. `\"2 0\"` **must not** become `\"150\"` or any value not equal to that concatenation).\n"
    "- Collapsed qty is **one integer**, **not** a date, **not** last_restock.\n"
    "- English number words → digits: **two**→`\"2\"`, **three**→`\"3\"`—use the **correct** digit, do not guess.\n"
    "- If the cell already contains something that is **clearly a date** (e.g. `2025-01-15`) or **clearly belongs in last_restock**, **clear qty** with **empty string**—do **not** invent a substitute number like `123`.\n"
    "- If qty is nonsense for a stock count, use **empty string** rather than fabricating a plausible digit.\n\n"
    "## last_restock rules\n"
    "- Valid: **YYYY-MM-DD** only. **If the cell already looks like a real ISO date** (e.g. `2025-01-01`, `2024-12-15`) with a **plausible** month/day, **leave it as-is**—do **not** blank good dates. Only set **empty** when the value is **not** ISO-shaped, is **impossible** (e.g. month 13), or is junk text (`not-a-date`, `32/01/2024`, slash formats you cannot normalize safely, etc.).\n"
    "- **Never** write a restock date into **qty_on_hand**, and **never** put a quantity into **last_restock**.\n\n"
    "## category rules (Electronics vs Food only)\n"
    "- **Food**: anything about **food retail, dining, grocery, cafeteria, café, food_service, kitchen, meal** → **`Food`**. "
    "Examples: `food_service`, `grocery`, `cafeteria`, `food_retail`, `FOOD` → **`Food`**. **Cafeteria is Food, not Electronics.**\n"
    "- **Electronics**: consumer/tech retail variants → **`Electronics`**. Examples: `electronics`, `ELEC`, `elec`, `ELECTRONICS`, trailing space on `Electronics ` → **`Electronics`**.\n"
    "- Ambiguous **Retail** alone: if the row is clearly food-related, **`Food`**; if clearly tech, **`Electronics`**; if still unclear, prefer **`Food`** only when name/sku hints at food, else **`Electronics`**.\n"
    "- Trim leading/trailing spaces on category.\n\n"
    "## Anti-hallucination\n"
    "- Do **not** copy a value from **column A** into **column B** unless B’s definition says it belongs there.\n"
    "- Do **not** output **JSON null** or **NaN** as text in cells—use **empty string** for missing.\n"
    "- Prefer **fewer, correct** set_cell calls over creative guesses.\n"
    "- **No-op edits**: do **not** call **set_cell** if **new_value** would equal the current cell (wastes audit lines)."
)

# Mutable tool state (main thread only)
tool_state: dict[str, Any] = {
    "df": None,
    "audit_path": str(LOG_PATH),
    "api_round": 0,
}


def append_audit(obj: dict[str, Any]) -> None:
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with open(tool_state["audit_path"], "a", encoding="utf-8") as f:
        f.write(line)


def run_set_cell(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    rid = args.get("row_id")
    col = str(args.get("column_name") or "")
    nv = str(args.get("new_value") or "")
    ev = args.get("expected_old_value")
    if rid is None:
        return "Error: row_id required."
    try:
        rid = int(rid)
    except (TypeError, ValueError):
        return "Error: row_id must be integer-like."
    if not col:
        return "Error: column_name required."
    if col == "row_id":
        return "Error: row_id column cannot be edited."
    df: pd.DataFrame = tool_state["df"]
    if col not in df.columns:
        return f"Error: unknown column {col}"
    rids = pd.to_numeric(df["row_id"], errors="coerce")
    idx = df.index[rids == rid]
    if len(idx) == 0:
        return f"Error: no row with row_id={rid}"
    i = idx[0]
    old = df.at[i, col]
    old = "" if pd.isna(old) else str(old)
    if ev is not None:
        evs = "" if pd.isna(ev) else str(ev)
        if old != evs:
            return (
                f'Skipped: expected_old_value mismatch for row_id={rid} col={col} '
                f'(current="{old}" expected="{evs}")'
            )
    df.at[i, col] = nv
    append_audit(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "set_cell",
            "row_id": rid,
            "column": col,
            "old_value": old,
            "new_value": nv,
        }
    )
    return f"OK: row_id={rid} {col} updated."


def run_write_checkpoint() -> str:
    df: pd.DataFrame = tool_state["df"]
    df.to_csv(WORK_PATH, index=False, na_rep="")
    return f"Checkpoint written: {len(df)} rows to {WORK_PATH}\n"


def fixer_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "set_cell",
                "description": (
                    "Set one cell in the working inventory row (identified by row_id). "
                    "Pass expected_old_value when possible. Do not edit row_id or sku unless instructed. "
                    "For missing/invalid cleaned values use an empty string for new_value—never the literals NaN, NA, null, or N/A as text."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "row_id": {"type": "integer", "description": "Stable row_id from the CSV."},
                        "column_name": {
                            "type": "string",
                            "description": "One of: qty_on_hand, last_restock, category (not row_id).",
                        },
                        "new_value": {
                            "type": "string",
                            "description": (
                                "New cell text. qty_on_hand: positive digits or empty; 0→empty; spaced digits concatenate in order only (2 0→20, never 150). "
                                "last_restock: keep valid YYYY-MM-DD; empty only if invalid. category: Electronics or Food. "
                                "Empty string means missing—do not write NaN."
                            ),
                        },
                        "expected_old_value": {
                            "type": "string",
                            "description": "If set, update only when current value equals this string.",
                        },
                    },
                    "required": ["row_id", "column_name", "new_value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_checkpoint",
                "description": f"Write the current working table to disk ({WORK_PATH.name}).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


def dispatch_fixer_tool(name: str, args: dict[str, Any], api_round: int) -> str:
    if name == "set_cell":
        rid = args.get("row_id", "?")
        col = args.get("column_name", "?")
        print(f"      ✏️  set_cell row_id={rid} col={col}")
        return run_set_cell(args, api_round)
    if name == "write_checkpoint":
        print("      💾 write_checkpoint")
        return run_write_checkpoint()
    print(f"      ❓ unknown tool: {name}")
    return f"Unknown tool: {name}"


def call_chunk_ollama(
    chunk_index: int,
    n_chunks: int,
    chunk_csv_text: str,
    ollama_host: str,
    ollama_key: str,
    ollama_model: str,
    system_prompt: str,
    data_blurb: str,
    tools: list[dict[str, Any]],
    max_output_tokens: int | None,
) -> dict[str, Any]:
    user_msg = (
        "Data dictionary + cleaning rules:\n\n"
        f"{data_blurb}\n\n---\nChunk "
        f"{chunk_index} of {n_chunks} (inventory CSV; columns must keep their semantics):\n\n"
        f"{chunk_csv_text}\n\n---\n"
        "Emit **set_cell** only where the rules require a change (skip if new_value would equal current). "
        "Use **expected_old_value** when possible (match the cell text exactly as shown in the CSV). "
        "Remember: **missing** = **new_value \"\"** (empty). Never **NaN** / **NA** / **null** as text. "
        "**qty_on_hand**: **`0` → `\"\"`**; spaced digits = **concatenate in order** (`2 0`→`20`), **never** a made-up number like **150**. Must never hold a date; if you see a date there, clear qty to **\"\"** (do not guess **123**). "
        "**\"1 2 3\"** in qty → **\"123\"** (concatenation only), not a date string. "
        "**last_restock**: **do not blank** plausible **YYYY-MM-DD** dates (e.g. **2025-01-01**); blank only invalid/junk. "
        "**cafeteria** / food-service labels → category **Food**. "
        "You may call **write_checkpoint** once after edits. "
        "Reply with tool calls only (minimal prose)."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    try:
        out = ollama_chat_once(
            ollama_host,
            ollama_key,
            ollama_model,
            messages,
            tools=tools,
            format=None,
            max_output_tokens=max_output_tokens,
        )
    except Exception as e:
        return {
            "chunk_index": chunk_index,
            "tool_calls": [],
            "error": str(e),
            "content": "",
        }
    msg = out.get("message") or {}
    return {
        "chunk_index": chunk_index,
        "tool_calls": msg.get("tool_calls") or [],
        "error": None,
        "content": out.get("content") or "",
    }


print("🧰 Initializing tool_state + tool definitions ...")
print("   ✅ Tool helpers ready.\n")

# 1. PREPARE FILES AND DATA ###################################

print("-----------------------------------------------------------------")
print("📂 Step 1 — Prepare files and load working copy")
print("-----------------------------------------------------------------\n")

print("📁 Ensuring output/ exists ...")
(FIXER_ROOT / "output").mkdir(parents=True, exist_ok=True)
print("   ✅ output/ OK.\n")

print("📥 Copying raw CSV ➡️ working copy ...")
shutil.copy2(RAW_PATH, WORK_PATH)
print("   ✅ Copied.\n")

print("📊 Reading working CSV (all columns as character) ...")
tool_state["df"] = pd.read_csv(WORK_PATH, dtype=str, keep_default_na=False)
df = tool_state["df"]
print(f"   ✅ Loaded {len(df)} rows × {len(df.columns)} cols.")
print("🔍 Preview:")
print(df.head(3))

print("🗑️  Resetting audit log ...")
if LOG_PATH.is_file():
    LOG_PATH.unlink()
print("   ✅ Audit log fresh.\n")

chunks = split_df_into_row_chunks(tool_state["df"], ROWS_PER_BATCH)
n_chunks = len(chunks)
chunk_csv_texts = [c.to_csv(index=False) for c in chunks]
print(f"✂️  Split into {n_chunks} chunk(s) of up to {ROWS_PER_BATCH} rows.\n")

SYSTEM_BATCH = (
    "You are a **batch** CSV cleaning assistant for a **retail inventory** table (SKU stock counts, restock dates, Electronics vs Food). "
    "Each user message is one row chunk plus a data dictionary. Fix cells using **set_cell** only (plus optional **write_checkpoint**). "
    "Prefer **expected_old_value** on each set_cell. "
    "**qty_on_hand** = positive digits or **empty**; **`0` → empty** (placeholder). Spaced digits: **concatenate in order only** (`2 0`→`20`), **never** invent unrelated numbers (`2 0`≠`150`). "
    "**last_restock** = keep **valid YYYY-MM-DD** unchanged; blank **only** invalid/junk dates. **category** = Electronics or Food only. "
    "Never put dates in qty_on_hand or invent numbers when qty is wrong—use **empty string** for missing. "
    "Never write the text **NaN**, **NA**, or **null** as a cell value—use **empty string** for missing. "
    "**Cafeteria / grocery / food_service** → category **Food**, not Electronics. "
    "\"1 2 3\" in qty → **\"123\"** (concatenation), never a date. "
    "Skip set_cell when new_value would equal the current value. Do not invent row_ids."
)

tools = fixer_tool_definitions()

# 3. PARALLEL CHUNK API CALLS ###################################

print("-----------------------------------------------------------------")
print(f"🔄 Step 2 — Ollama /api/chat per chunk (workers = {FIXER_CHUNK_WORKERS})")
print("-----------------------------------------------------------------\n\n")

chunk_results: list[dict[str, Any]] = []


def _run_one(i: int) -> dict[str, Any]:
    return call_chunk_ollama(
        chunk_index=i,
        n_chunks=n_chunks,
        chunk_csv_text=chunk_csv_texts[i - 1],
        ollama_host=OLLAMA_HOST,
        ollama_key=OLLAMA_API_KEY,
        ollama_model=OLLAMA_MODEL,
        system_prompt=SYSTEM_BATCH,
        data_blurb=DATA_QUALITY_BLURB,
        tools=tools,
        max_output_tokens=MAX_OUT,
    )


with ThreadPoolExecutor(max_workers=FIXER_CHUNK_WORKERS) as ex:
    futs = {ex.submit(_run_one, i): i for i in range(1, n_chunks + 1)}
    tmp: dict[int, dict[str, Any]] = {}
    for fut in as_completed(futs):
        cr = fut.result()
        tmp[cr["chunk_index"]] = cr
    chunk_results = [tmp[i] for i in range(1, n_chunks + 1)]

for cr in chunk_results:
    if cr.get("error"):
        print(f"   ❌ Chunk {cr['chunk_index']} API error: {cr['error']}")

# 4. APPLY TOOL CALLS ON MAIN PROCESS (ORDERED) ###################################

print("\n-----------------------------------------------------------------")
print("🔧 Step 3 — Execute tool calls on main process (chunk order)")
print("-----------------------------------------------------------------\n\n")

api_round_counter = 0
n_tools_executed = 0

for cr in chunk_results:
    ci = cr["chunk_index"]
    tcalls = cr.get("tool_calls") or []
    if not tcalls:
        tail = ""
        c = cr.get("content") or ""
        if c:
            tail = f" (assistant text: {c[:80]}...)"
        print(f"   ⚠️  Chunk {ci}: no tool calls{tail}")
        continue
    print(f"   📦 Chunk {ci}: {len(tcalls)} tool call(s)")
    for tc in tcalls:
        if not isinstance(tc, dict):
            continue
        api_round_counter += 1
        tool_state["api_round"] = api_round_counter
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        args = parse_function_arguments(fn.get("arguments"))
        dispatch_fixer_tool(name, args, api_round_counter)
        n_tools_executed += 1

# 5. WRITE FINAL TABLE ###################################

print("\n-----------------------------------------------------------------")
print("💾 Step 4 — Writing final working table")
print("-----------------------------------------------------------------")
tool_state["df"].to_csv(WORK_PATH, index=False, na_rep="")
print(f"   ✅ Saved {len(tool_state['df'])} rows ➡️ {WORK_PATH}\n")

# 6. SUMMARY ###################################

n_audit = 0
if LOG_PATH.is_file():
    with open(LOG_PATH, encoding="utf-8") as f:
        n_audit = sum(1 for line in f if line.strip())

print("=================================================================")
print("📊 Summary")
print("=================================================================")
print(f"📦 Chunks (API calls):     {n_chunks}")
print(f"🔧 Tool calls executed:   {n_tools_executed}")
print(f"✏️  Audit lines (set_cell): {n_audit}")
print(f"👷 Chunk workers used:    {FIXER_CHUNK_WORKERS}")
print(f"💾 Working file:          {WORK_PATH}")
print(f"📝 Audit log:             {LOG_PATH}")
print("=================================================================")
