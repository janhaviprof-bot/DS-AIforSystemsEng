# fixer_pois.py
# Batched POI name normalization — one Ollama round per N rows + ThreadPoolExecutor (Ollama tools)
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
print("📍 fixer_pois.py — batched POI category tools + points (Ollama Cloud)")
print("=================================================================\n")

print("📦 Loading Python packages (pandas, geopandas, matplotlib, httpx, dotenv) ...")
print("   ✅ Packages ready.\n")

FIXER_ROOT = Path(__file__).resolve().parent
os.chdir(FIXER_ROOT)
print("📁 Resolving fixer folder and paths ...")
print(f"   📍 FIXER_ROOT: {FIXER_ROOT}")

POIS_PATH = FIXER_ROOT / "data" / "pois_messy_raw.csv"
OUT_CSV = FIXER_ROOT / "output" / "pois_enriched.csv"
AUDIT_PATH = FIXER_ROOT / "output" / "pois_enrich_audit.jsonl"
OUT_DIR = FIXER_ROOT / "output"
print(f"   📄 POIs:   {POIS_PATH}")
print(f"   💾 Output: {OUT_CSV}\n")

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

POI_DATA_BLURB = (
    "## POI table\n"
    "Each row is one **point** (columns **x** = longitude, **y** = latitude). **poi_id** is the stable key. "
    "**name_messy** is a noisy facility label to classify.\n\n"
    "## Output fields (one tool call per row)\n"
    "- **normalized_category**: exactly one of "
    '"healthcare", "food_retail", "retail", "financial", "transport", '
    '"recreation", "parking", "childcare", "agriculture", "vacant", '
    '"public_government", "other".\n'
    "- **confidence**: integer 1 (low), 2 (medium), or 3 (high).\n"
    "- **display_name_clean**: short human-readable name.\n"
)

SYSTEM_POIS = (
    "You classify messy facility names into a **closed vocabulary** for a **batch** of POI rows. "
    "Reply using **record_poi_category** tool calls only (one per poi_id in the chunk). "
    "confidence is 1=low 2=medium 3=high. Do not invent poi_id values."
)

tool_state: dict[str, Any] = {"df": None, "audit_path": str(AUDIT_PATH), "api_round": 0}


def append_audit_poi(obj: dict[str, Any]) -> None:
    with open(tool_state["audit_path"], "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_record_poi_category(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    pid = args.get("poi_id")
    if pid is None or (isinstance(pid, str) and not str(pid).strip()):
        return "Error: poi_id required."
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return "Error: poi_id must be integer-like."
    df: pd.DataFrame = tool_state["df"]
    j = df.index[pd.to_numeric(df["poi_id"], errors="coerce") == pid]
    if len(j) == 0:
        return f"Error: unknown poi_id={pid}"
    i = j[0]
    df.at[i, "normalized_category"] = str(args.get("normalized_category") or "")
    conf = args.get("confidence")
    try:
        df.at[i, "confidence"] = int(conf) if conf is not None and str(conf).strip() != "" else pd.NA
    except (TypeError, ValueError):
        df.at[i, "confidence"] = pd.NA
    df.at[i, "display_name_clean"] = str(args.get("display_name_clean") or "")
    append_audit_poi(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "record_poi_category",
            "poi_id": pid,
        }
    )
    return f"OK: poi_id={pid} updated."


def poi_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "record_poi_category",
                "description": "Store normalized category and display name for one POI. poi_id must match the chunk CSV.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "poi_id": {"type": "integer", "description": "poi_id from the CSV row."},
                        "normalized_category": {
                            "type": "string",
                            "description": (
                                "One of: healthcare, food_retail, retail, financial, transport, recreation, "
                                "parking, childcare, agriculture, vacant, public_government, other."
                            ),
                        },
                        "confidence": {"type": "integer", "description": "1=low, 2=medium, 3=high."},
                        "display_name_clean": {"type": "string", "description": "Short cleaned facility name."},
                    },
                    "required": ["poi_id", "normalized_category", "confidence", "display_name_clean"],
                },
            },
        }
    ]


def dispatch_poi_tool(name: str, args: dict[str, Any], api_round: int) -> str:
    if name == "record_poi_category":
        print(f"      ✏️  record_poi_category poi_id={args.get('poi_id', '?')}")
        return run_record_poi_category(args, api_round)
    print(f"      ❓ unknown tool: {name}")
    return f"Unknown tool: {name}"


def call_poi_chunk_ollama(
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
        "Task: for each POI in the chunk, call **record_poi_category** once (use **poi_id** from the CSV).\n\n"
        f"{data_blurb}\n\n---\nChunk {chunk_index} of {n_chunks} (EPSG:4326 coordinates).\n\n"
        f"{chunk_csv_text}\n\n---\nEmit one **record_poi_category** per row. Reply with tool calls only (minimal prose)."
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
print("📂 Step 1 — Load POIs (points)")
print("-----------------------------------------------------------------\n")

OUT_DIR.mkdir(parents=True, exist_ok=True)
if AUDIT_PATH.is_file():
    AUDIT_PATH.unlink()

pois_in = pd.read_csv(POIS_PATH)
if not all(c in pois_in.columns for c in ("poi_id", "x", "y")):
    raise SystemExit("POIs CSV must include poi_id, x, y")

pois_tbl = pois_in.copy()
pois_tbl["normalized_category"] = ""
pois_tbl["confidence"] = pd.NA
pois_tbl["display_name_clean"] = ""
pois_tbl["error_flag"] = False

tool_state["df"] = pois_tbl
print(f"   ✅ {len(pois_tbl)} POIs × {len(pois_tbl.columns)} cols.\n")

chunks_in = pois_in[["poi_id", "x", "y", "name_messy"]].copy()
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = len(chunks)
chunk_csv_texts = [c.to_csv(index=False) for c in chunks]
print(f"✂️  Split into {n_chunks} chunk(s) of up to {ROWS_PER_BATCH} rows.\n")

poi_tools = poi_tool_definitions()

# 3. PARALLEL CHUNK API ###################################

print("-----------------------------------------------------------------")
print("🔄 Step 2 — Ollama /api/chat per chunk (ThreadPoolExecutor)")
print("-----------------------------------------------------------------\n\n")


def _run_poi(i: int) -> dict[str, Any]:
    return call_poi_chunk_ollama(
        chunk_index=i,
        n_chunks=n_chunks,
        chunk_csv_text=chunk_csv_texts[i - 1],
        ollama_host=OLLAMA_HOST,
        ollama_key=OLLAMA_API_KEY,
        ollama_model=OLLAMA_MODEL,
        system_prompt=SYSTEM_POIS,
        data_blurb=POI_DATA_BLURB,
        tools=poi_tools,
        max_output_tokens=MAX_OUT,
    )


with ThreadPoolExecutor(max_workers=FIXER_CHUNK_WORKERS) as ex:
    tmp: dict[int, dict[str, Any]] = {}
    futs = {ex.submit(_run_poi, i): i for i in range(1, n_chunks + 1)}
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
        for pid in chunks[ci - 1]["poi_id"].astype(int):
            jj = df.index[pd.to_numeric(df["poi_id"], errors="coerce") == pid]
            if len(jj):
                df.at[jj[0], "error_flag"] = True
        continue
    tcalls = cr.get("tool_calls") or []
    if not tcalls:
        print(f"   ⚠️  Chunk {ci}: no tool calls")
        for pid in chunks[ci - 1]["poi_id"].astype(int):
            jj = df.index[pd.to_numeric(df["poi_id"], errors="coerce") == pid]
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
        dispatch_poi_tool(name, args, api_round_counter)
        n_tools += 1

nc = df["normalized_category"].astype(str).str.strip()
df["plot_label"] = nc.where(nc.ne(""), "unknown")
df["error_flag"] = (nc.eq("") | df["normalized_category"].isna()) | df["error_flag"]

pois_out = df.drop(columns=["plot_label"])
pois_out.to_csv(OUT_CSV, index=False, na_rep="")
print(f"\n   ✅ Wrote {OUT_CSV}\n")

# 5. SF + MAPS ###################################

print("\n-----------------------------------------------------------------")
print("🎨 Step 4 — Maps (geopandas + matplotlib points)")
print("-----------------------------------------------------------------\n")

pois_for_map = df.copy()
pois_sf = gpd.GeoDataFrame(
    pois_for_map,
    geometry=gpd.points_from_xy(pois_for_map["x"], pois_for_map["y"]),
    crs=WGS84_CRS,
)

fig, ax = plt.subplots(figsize=(7, 5))
pois_sf.plot(ax=ax, color="#3498db", edgecolor="#2c3e50", markersize=25, alpha=0.9)
ax.set_title("POIs (uniform symbol before category)")
ax.set_axis_off()
path_ob = OUT_DIR / "map_pois_before.png"
fig.savefig(path_ob, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"   💾 {path_ob}")

fig, ax = plt.subplots(figsize=(7, 5))
pois_sf.plot(
    ax=ax,
    column="plot_label",
    categorical=True,
    legend=True,
    markersize=25,
    alpha=0.85,
)
ax.set_title("POIs by normalized_category")
ax.set_axis_off()
path_oa = OUT_DIR / "map_pois_after.png"
fig.savefig(path_oa, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"   💾 {path_oa}")

# 6. SUMMARY ###################################

n_audit = 0
if AUDIT_PATH.is_file():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        n_audit = sum(1 for line in f if line.strip())
n_err = int(df["error_flag"].fillna(False).sum())

print("\n=================================================================")
print("📊 Summary (fixer_pois.py)")
print("=================================================================")
print(f"📦 Chunks: {n_chunks} | tool calls: {n_tools} | audit lines: {n_audit}")
print(f"⚠️  Rows error_flag TRUE: {n_err} / {len(df)}")
print("=================================================================")
