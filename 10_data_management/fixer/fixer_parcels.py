# fixer_parcels.py
# Batched parcel zoning enrichment — one Ollama round per N rows + ThreadPoolExecutor (Ollama tools)
# Tim Fraser

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv

from functions import ollama_chat_once, parse_function_arguments, split_df_into_row_chunks

print()
print("=================================================================")
print("🏘️  fixer_parcels.py — batched zoning tools + polygons (Ollama Cloud)")
print("=================================================================\n")

print("📦 Loading Python packages (pandas, geopandas, matplotlib, httpx, dotenv) ...")
print("   ✅ Packages ready.\n")

FIXER_ROOT = Path(__file__).resolve().parent
os.chdir(FIXER_ROOT)
print("📁 Resolving fixer folder and paths ...")
print(f"   📍 FIXER_ROOT: {FIXER_ROOT}")

PARCELS_PATH = FIXER_ROOT / "data" / "parcels_zoning_raw.csv"
OUT_CSV = FIXER_ROOT / "output" / "parcels_enriched.csv"
AUDIT_PATH = FIXER_ROOT / "output" / "parcels_enrich_audit.jsonl"
OUT_DIR = FIXER_ROOT / "output"
print(f"   📄 Parcels: {PARCELS_PATH}")
print(f"   💾 Output:  {OUT_CSV}\n")

env_path = FIXER_ROOT / ".env"
print("🔐 Loading .env ...")
if not env_path.is_file():
    raise SystemExit("No .env in fixer folder; create one with OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL.")
load_dotenv(env_path)
print("   ✅ .env read from fixer folder.\n")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com").strip()
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "nemotron-3-nano:30b-cloud").strip()
print(f"☁️  Ollama: host = {OLLAMA_HOST}")
print(f"   model  = {OLLAMA_MODEL}\n")


def read_env_digits(name: str, default: int) -> int:
    s = os.environ.get(name, str(default)).strip()
    if s.isdigit():
        v = int(s)
        if v >= 1:
            return v
    return default


ROWS_PER_BATCH = read_env_digits("ROWS_PER_BATCH", 10)
FIXER_CHUNK_WORKERS = read_env_digits("FIXER_CHUNK_WORKERS", 1)
print(f"📊 ROWS_PER_BATCH = {ROWS_PER_BATCH}")
print(f"📊 FIXER_CHUNK_WORKERS = {FIXER_CHUNK_WORKERS}\n")

et = os.environ.get("FIXER_MAX_OUTPUT_TOKENS", "").strip()
MAX_OUT: int | None = int(et) if et.isdigit() else None

print("🔌 Importing fixer/functions.py ...")
print("   ✅ Helpers loaded.\n")

WGS84_CRS = 4326

ZONING_DATA_BLURB = (
    "## Parcel table\n"
    "Each row is one **parcel polygon** (column **wkt**). **parcel_id** is the stable key. "
    "**zone_code** is a short label; **zoning_excerpt** is ordinance-style prose to interpret.\n\n"
    "## Output fields (one tool call per row)\n"
    "- **primary_land_use**: exactly one of "
    '"residential", "commercial", "industrial", "mixed", "open_space", "institutional", "other".\n'
    "- **allows_residential**, **allows_commercial**, **parking_mentioned**: booleans true/false.\n"
    "- **notes**: <= 120 characters summarizing uncertainty or key cues.\n"
)

SYSTEM_PARCELS = (
    "You extract structured zoning attributes from short ordinance excerpts for a **batch** of parcel rows. "
    "Reply using **record_parcel_zoning** tool calls only (one per parcel_id in the chunk). "
    "Booleans must be true/false. primary_land_use must be one of the allowed values. "
    "Do not invent parcel_id values. Do not modify **wkt** geometry."
)

tool_state: dict[str, Any] = {"df": None, "audit_path": str(AUDIT_PATH), "api_round": 0}


def append_audit_parcel(obj: dict[str, Any]) -> None:
    with open(tool_state["audit_path"], "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def coerce_bool(x: Any) -> Any:
    if x is None:
        return pd.NA
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return pd.NA


def run_record_parcel_zoning(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    pid = args.get("parcel_id")
    if pid is None or str(pid).strip() == "":
        return "Error: parcel_id required."
    pid = str(pid).strip()
    df: pd.DataFrame = tool_state["df"]
    j = df.index[df["parcel_id"].astype(str) == pid]
    if len(j) == 0:
        return f"Error: unknown parcel_id={pid}"
    i = j[0]
    df.at[i, "primary_land_use"] = str(args.get("primary_land_use") or "")
    df.at[i, "allows_residential"] = coerce_bool(args.get("allows_residential"))
    df.at[i, "allows_commercial"] = coerce_bool(args.get("allows_commercial"))
    df.at[i, "parking_mentioned"] = coerce_bool(args.get("parking_mentioned"))
    df.at[i, "notes"] = str(args.get("notes") or "")
    append_audit_parcel(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "record_parcel_zoning",
            "parcel_id": pid,
        }
    )
    return f"OK: parcel_id={pid} updated."


def parcel_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "record_parcel_zoning",
                "description": (
                    "Store LLM-derived zoning tags for one parcel. parcel_id must match the chunk CSV. "
                    "Infer fields from zoning_excerpt; leave notes concise (<=120 chars)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parcel_id": {"type": "string", "description": "parcel_id from the CSV row."},
                        "primary_land_use": {
                            "type": "string",
                            "description": (
                                "One of: residential, commercial, industrial, mixed, open_space, institutional, other."
                            ),
                        },
                        "allows_residential": {"type": "boolean"},
                        "allows_commercial": {"type": "boolean"},
                        "parking_mentioned": {"type": "boolean"},
                        "notes": {"type": "string", "description": "Short rationale or caveats (<=120 chars)."},
                    },
                    "required": [
                        "parcel_id",
                        "primary_land_use",
                        "allows_residential",
                        "allows_commercial",
                        "parking_mentioned",
                        "notes",
                    ],
                },
            },
        }
    ]


def dispatch_parcel_tool(name: str, args: dict[str, Any], api_round: int) -> str:
    if name == "record_parcel_zoning":
        print(f"      ✏️  record_parcel_zoning parcel_id={args.get('parcel_id', '?')}")
        return run_record_parcel_zoning(args, api_round)
    print(f"      ❓ unknown tool: {name}")
    return f"Unknown tool: {name}"


def call_parcel_chunk_ollama(
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
        "Task: for each parcel in the chunk, call **record_parcel_zoning** once (use **parcel_id** from the CSV).\n\n"
        f"{data_blurb}\n\n---\nChunk {chunk_index} of {n_chunks} (EPSG:4326 polygons in **wkt**; do not edit geometry).\n\n"
        f"{chunk_csv_text}\n\n---\nEmit one **record_parcel_zoning** per row. Reply with tool calls only (minimal prose)."
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
        return {"chunk_index": chunk_index, "tool_calls": [], "error": str(e), "content": ""}
    msg = out.get("message") or {}
    return {
        "chunk_index": chunk_index,
        "tool_calls": msg.get("tool_calls") or [],
        "error": None,
        "content": out.get("content") or "",
    }


# 2. LOAD DATA ###################################

print("-----------------------------------------------------------------")
print("📂 Step 1 — Load parcels (polygon WKT)")
print("-----------------------------------------------------------------\n")

OUT_DIR.mkdir(parents=True, exist_ok=True)
if AUDIT_PATH.is_file():
    AUDIT_PATH.unlink()

parcels_in = pd.read_csv(PARCELS_PATH)
if "parcel_id" not in parcels_in.columns or "wkt" not in parcels_in.columns:
    raise SystemExit("parcels CSV must include parcel_id and wkt")

parcels_tbl = parcels_in.copy()
parcels_tbl["primary_land_use"] = ""
parcels_tbl["allows_residential"] = pd.NA
parcels_tbl["allows_commercial"] = pd.NA
parcels_tbl["parking_mentioned"] = pd.NA
parcels_tbl["notes"] = ""
parcels_tbl["error_flag"] = False

tool_state["df"] = parcels_tbl
print(f"   ✅ {len(parcels_tbl)} parcels × {len(parcels_tbl.columns)} cols.\n")

chunks_in = parcels_in[["parcel_id", "wkt", "zone_code", "zoning_excerpt"]].copy()
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = len(chunks)
chunk_csv_texts = [c.to_csv(index=False) for c in chunks]
print(f"✂️  Split into {n_chunks} chunk(s) of up to {ROWS_PER_BATCH} rows.\n")

parcel_tools = parcel_tool_definitions()

# 3. PARALLEL CHUNK API ###################################

print("-----------------------------------------------------------------")
print("🔄 Step 2 — Ollama /api/chat per chunk (ThreadPoolExecutor)")
print("-----------------------------------------------------------------\n\n")


def _run_parcel(i: int) -> dict[str, Any]:
    return call_parcel_chunk_ollama(
        chunk_index=i,
        n_chunks=n_chunks,
        chunk_csv_text=chunk_csv_texts[i - 1],
        ollama_host=OLLAMA_HOST,
        ollama_key=OLLAMA_API_KEY,
        ollama_model=OLLAMA_MODEL,
        system_prompt=SYSTEM_PARCELS,
        data_blurb=ZONING_DATA_BLURB,
        tools=parcel_tools,
        max_output_tokens=MAX_OUT,
    )


with ThreadPoolExecutor(max_workers=FIXER_CHUNK_WORKERS) as ex:
    tmp: dict[int, dict[str, Any]] = {}
    futs = {ex.submit(_run_parcel, i): i for i in range(1, n_chunks + 1)}
    for fut in as_completed(futs):
        cr = fut.result()
        tmp[cr["chunk_index"]] = cr
    chunk_results = [tmp[i] for i in range(1, n_chunks + 1)]

# 4. APPLY TOOLS ###################################

print("-----------------------------------------------------------------")
print("🔧 Step 3 — Apply tool calls (chunk order)")
print("-----------------------------------------------------------------\n\n")

api_round_counter = 0
n_tools = 0
df = tool_state["df"]

for cr in chunk_results:
    ci = cr["chunk_index"]
    if cr.get("error"):
        print(f"   ❌ Chunk {ci}: {cr['error']}")
        for pid in chunks[ci - 1]["parcel_id"].astype(str):
            jj = df.index[df["parcel_id"].astype(str) == pid]
            if len(jj):
                df.at[jj[0], "error_flag"] = True
        continue
    tcalls = cr.get("tool_calls") or []
    if not tcalls:
        print(f"   ⚠️  Chunk {ci}: no tool calls")
        for pid in chunks[ci - 1]["parcel_id"].astype(str):
            jj = df.index[df["parcel_id"].astype(str) == pid]
            if len(jj):
                df.at[jj[0], "error_flag"] = True
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
        dispatch_parcel_tool(name, args, api_round_counter)
        n_tools += 1

plu = df["primary_land_use"].astype(str).str.strip()
df["error_flag"] = (plu.eq("") | df["primary_land_use"].isna()) | df["error_flag"]

parcels_out = df
parcels_out.to_csv(OUT_CSV, index=False, na_rep="")
print(f"\n   ✅ Wrote {OUT_CSV}\n")

# 5. SF + MAPS ###################################

print("\n-----------------------------------------------------------------")
print("🎨 Step 4 — Maps (geopandas + matplotlib polygons)")
print("-----------------------------------------------------------------\n")

parcels_sf = gpd.GeoDataFrame(
    parcels_out,
    geometry=gpd.GeoSeries.from_wkt(parcels_out["wkt"]),
    crs=WGS84_CRS,
)

fig, ax = plt.subplots(figsize=(7, 5))
parcels_sf.plot(column="zone_code", ax=ax, edgecolor="gray", linewidth=0.3, legend=True)
ax.set_title("Parcels by raw zone_code")
ax.set_axis_off()
path_pb = OUT_DIR / "map_parcels_before.png"
fig.savefig(path_pb, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"   💾 {path_pb}")

fig, ax = plt.subplots(figsize=(7, 5))
parcels_sf.plot(column="primary_land_use", ax=ax, edgecolor="gray", linewidth=0.3, legend=True)
ax.set_title("Parcels by LLM primary_land_use")
ax.set_axis_off()
path_pa = OUT_DIR / "map_parcels_after.png"
fig.savefig(path_pa, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"   💾 {path_pa}")

# 6. SUMMARY ###################################

n_audit = 0
if AUDIT_PATH.is_file():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        n_audit = sum(1 for line in f if line.strip())
n_err = int(parcels_out["error_flag"].fillna(False).sum())

print("\n=================================================================")
print("📊 Summary (fixer_parcels.py)")
print("=================================================================")
print(f"📦 Chunks: {n_chunks} | tool calls: {n_tools} | audit lines: {n_audit}")
print(f"⚠️  Rows error_flag TRUE: {n_err} / {len(parcels_out)}")
print("=================================================================")
