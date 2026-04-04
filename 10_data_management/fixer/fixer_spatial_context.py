# fixer_spatial_context.py
# Contextual spatial routing — LLM picks geopandas-backed tools per parcel (batched Ollama)
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
print("🧭 fixer_spatial_context.py — contextual tool routing + geopandas")
print("=================================================================\n")

print("📦 Loading Python packages (pandas, geopandas, matplotlib, httpx, dotenv) ...")
print("   ✅ Packages ready.\n")

FIXER_ROOT = Path(__file__).resolve().parent
os.chdir(FIXER_ROOT)
print("📁 Resolving fixer folder and paths ...")
print(f"   📍 FIXER_ROOT: {FIXER_ROOT}")

PARCELS_PATH = Path(
    os.environ.get("FIXER_CONTEXT_PARCELS", str(FIXER_ROOT / "output" / "parcels_enriched.csv"))
)
POIS_PATH = Path(os.environ.get("FIXER_CONTEXT_POIS", str(FIXER_ROOT / "output" / "pois_enriched.csv")))
OUT_CSV = FIXER_ROOT / "output" / "parcels_context_enriched.csv"
AUDIT_PATH = FIXER_ROOT / "output" / "context_routing_audit.jsonl"
OUT_DIR = FIXER_ROOT / "output"
print(f"   📄 Parcels: {PARCELS_PATH}")
print(f"   📄 POIs:    {POIS_PATH}")
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
print(f"📊 ROWS_PER_BATCH = {ROWS_PER_BATCH} (env ROWS_PER_BATCH)")
print(f"📊 FIXER_CHUNK_WORKERS = {FIXER_CHUNK_WORKERS} (env FIXER_CHUNK_WORKERS)\n")

et = os.environ.get("FIXER_MAX_OUTPUT_TOKENS", "").strip()
MAX_OUT: int | None = int(et) if et.isdigit() else None

print("🔌 Importing fixer/functions.py ...")
print("   ✅ Helpers loaded.\n")

WGS84_CRS = 4326
METER_CRS = 32617

POI_CATEGORIES = [
    "healthcare",
    "food_retail",
    "retail",
    "financial",
    "transport",
    "recreation",
    "parking",
    "childcare",
    "agriculture",
    "vacant",
    "public_government",
    "other",
]

ROUTING_BLURB = (
    "## Your job (contextual routing)\n"
    "For **each parcel_id** in the chunk, decide **which spatial tools** to call. "
    "Geometry is computed **only** inside tools—**never** invent distances or counts in prose.\n\n"
    "## Parcel attributes you see\n"
    "- **zone_code** (e.g. R-1, C-1, I-1, MIX, OS, C-2, PUD)\n"
    "- **primary_land_use** (e.g. residential, commercial, industrial, mixed, open_space, institutional, other)\n\n"
    "## Routing rules (apply per row; call multiple tools when appropriate)\n"
    "1. **Residential** (`primary_land_use` is residential **or** `zone_code` matches `^R-`): "
    "**nearest_poi** with **poi_category**=`transport`; **count_pois_within** **food_retail** buffer_m=400 (walkable food).\n"
    "2. **Commercial** (`commercial` **or** `zone_code` in C-1, C-2): "
    "**count_pois_within** **retail** 400m; **nearest_poi** **transport**.\n"
    "3. **Mixed** (`mixed` **or** `zone_code` is MIX or PUD): "
    "**nearest_poi** **transport**; **count_pois_within** **retail** 400m; **count_pois_within** **food_retail** 400m.\n"
    "4. **Open space** (`open_space` **or** `zone_code` is OS): "
    "**nearest_poi** **recreation**; **count_pois_within** **parking** 400m.\n"
    "5. **Industrial** (`industrial` **or** `zone_code` matches `^I-`): "
    "**nearest_poi** **transport**; optional **nearest_poi** **healthcare**.\n"
    "6. **Institutional**: **nearest_poi** **healthcare**; **count_pois_within** **parking** 400m.\n"
    "7. **Other / unknown** land use: at least **nearest_poi** **transport**.\n\n"
    "## After spatial tools\n"
    "Optionally call **record_context_note** for that **parcel_id** (<=180 chars): short summary of **which** rules you applied (no numeric fabrication).\n\n"
    "## Tool constraints\n"
    "- **nearest_poi** **poi_category** must be one of: "
    + ", ".join(POI_CATEGORIES)
    + ".\n"
    "- **count_pois_within**: **buffer_m** must be **400** or **800**.\n"
    "- **max_search_m** on **nearest_poi** defaults to 5000 (meters).\n"
)

SYSTEM_CONTEXT = (
    "You are a **spatial analysis router**. Each user message is a CSV chunk of parcels with "
    "**zone_code** and **primary_land_use**. You choose **nearest_poi**, **count_pois_within**, "
    "and optional **record_context_note** tool calls so that R can compute distances and counts. "
    "Do **not** output made-up distances. **parcel_id** must match the chunk. "
    "Emit tool calls only (minimal prose)."
)

# 1. LOAD DATA + BUILD SF ###################################

print("-----------------------------------------------------------------")
print("📂 Step 1 — Load parcels, POIs, build sf (metric CRS for ops)")
print("-----------------------------------------------------------------\n")

OUT_DIR.mkdir(parents=True, exist_ok=True)
if AUDIT_PATH.is_file():
    AUDIT_PATH.unlink()

parcels_tbl = pd.read_csv(PARCELS_PATH)
pois_tbl = pd.read_csv(POIS_PATH)

req_p = ["parcel_id", "wkt", "zone_code"]
miss_p = [c for c in req_p if c not in parcels_tbl.columns]
if miss_p:
    raise SystemExit(f"Parcels file missing columns: {', '.join(miss_p)}")

if "primary_land_use" not in parcels_tbl.columns:
    parcels_tbl["primary_land_use"] = ""
    print("   ⚠️  No primary_land_use column — routing uses zone_code only; enrich parcels first for best results.\n")

req_i = ["poi_id", "x", "y", "normalized_category"]
miss_i = [c for c in req_i if c not in pois_tbl.columns]
if miss_i:
    raise SystemExit(f"POIs file missing columns: {', '.join(miss_i)}")

ctx_count_cols = [f"ctx_n_{cat}_{buf}" for cat in POI_CATEGORIES for buf in (400, 800)]
ctx_nearest_cols = [f"ctx_nearest_{cat}_m" for cat in POI_CATEGORIES] + [
    f"ctx_nearest_{cat}_poi_id" for cat in POI_CATEGORIES
]
for cn in ctx_count_cols:
    if cn not in parcels_tbl.columns:
        parcels_tbl[cn] = pd.NA
for cn in ctx_nearest_cols:
    if cn not in parcels_tbl.columns:
        if cn.endswith("_poi_id"):
            parcels_tbl[cn] = pd.NA
        else:
            parcels_tbl[cn] = float("nan")
if "ctx_context_note" not in parcels_tbl.columns:
    parcels_tbl["ctx_context_note"] = ""
if "error_flag" not in parcels_tbl.columns:
    parcels_tbl["error_flag"] = False

parcels_sf = gpd.GeoDataFrame(
    parcels_tbl,
    geometry=gpd.GeoSeries.from_wkt(parcels_tbl["wkt"]),
    crs=WGS84_CRS,
)
parcels_sf_m = parcels_sf.to_crs(METER_CRS)

pois_sf = gpd.GeoDataFrame(
    pois_tbl,
    geometry=gpd.points_from_xy(pois_tbl["x"], pois_tbl["y"]),
    crs=WGS84_CRS,
)
pois_sf_m = pois_sf.to_crs(METER_CRS)

print(f"   ✅ Parcels: {len(parcels_tbl)} | POIs: {len(pois_tbl)}")
print(f"   🗺️  Ops CRS: EPSG:{METER_CRS} (buffers / distances in meters)\n")

tool_state: dict[str, Any] = {
    "df": parcels_tbl,
    "parcels_sf_m": parcels_sf_m,
    "pois_sf_m": pois_sf_m,
    "pois_tbl": pois_tbl,
    "audit_path": str(AUDIT_PATH),
    "api_round": 0,
}


def append_ctx_audit(obj: dict[str, Any]) -> None:
    with open(tool_state["audit_path"], "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def nearest_col_names(poi_category: str) -> tuple[str, str] | None:
    m = f"ctx_nearest_{poi_category}_m"
    pid = f"ctx_nearest_{poi_category}_poi_id"
    df = tool_state["df"]
    if m not in df.columns or pid not in df.columns:
        return None
    return m, pid


def count_col_name(poi_category: str, buffer_m: int) -> str:
    return f"ctx_n_{poi_category}_{buffer_m}"


def run_nearest_poi(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    pid = str(args.get("parcel_id") or "").strip()
    if not pid:
        return "Error: parcel_id required."
    catg = str(args.get("poi_category") or "")
    if catg not in POI_CATEGORIES:
        return f"Error: invalid poi_category: {catg}"
    cols = nearest_col_names(catg)
    if cols is None:
        return f"Error: nearest_poi column missing for category {catg}."
    max_m = args.get("max_search_m", 5000)
    try:
        max_m = float(max_m)
    except (TypeError, ValueError):
        max_m = 5000.0
    if max_m <= 0:
        max_m = 5000.0

    df = tool_state["df"]
    j = df.index[df["parcel_id"].astype(str) == pid]
    if len(j) == 0:
        return f"Error: unknown parcel_id={pid}"
    ji = j[0]

    psf = tool_state["parcels_sf_m"]
    p_geom = psf.loc[psf["parcel_id"].astype(str) == pid]
    if len(p_geom) != 1:
        return "Error: parcel geometry not found."
    parcel_row_geom = p_geom.geometry.iloc[0]
    ctr = parcel_row_geom.centroid

    pt = tool_state["pois_sf_m"]
    pt = pt[pt["normalized_category"].astype(str) == catg]
    if len(pt) < 1:
        df.at[ji, cols[0]] = float("nan")
        df.at[ji, cols[1]] = pd.NA
        append_ctx_audit(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "api_round": int(api_round),
                "tool": "nearest_poi",
                "parcel_id": pid,
                "poi_category": catg,
                "result": "no_pois_of_category",
            }
        )
        return f"OK: no {catg} POIs; stored NA."

    dists = pt.geometry.distance(ctr)
    imin_idx = dists.idxmin()
    best_d = float(dists.min())
    if best_d > max_m:
        df.at[ji, cols[0]] = float("nan")
        df.at[ji, cols[1]] = pd.NA
        append_ctx_audit(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "api_round": int(api_round),
                "tool": "nearest_poi",
                "parcel_id": pid,
                "poi_category": catg,
                "result": "beyond_max_search_m",
                "distance_m": best_d,
            }
        )
        return "OK: nearest beyond max_search_m; stored NA."

    best_id = int(pt.loc[imin_idx, "poi_id"])
    df.at[ji, cols[0]] = best_d
    df.at[ji, cols[1]] = best_id
    append_ctx_audit(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "nearest_poi",
            "parcel_id": pid,
            "poi_category": catg,
            "distance_m": best_d,
            "nearest_poi_id": best_id,
        }
    )
    return f"OK: nearest {catg} = {round(best_d, 1)} m (poi_id={best_id})."


def run_count_pois_within(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    pid = str(args.get("parcel_id") or "").strip()
    if not pid:
        return "Error: parcel_id required."
    catg = str(args.get("poi_category") or "")
    if catg not in POI_CATEGORIES:
        return f"Error: invalid poi_category: {catg}"
    try:
        buf = int(args.get("buffer_m"))
    except (TypeError, ValueError):
        buf = -1
    if buf not in (400, 800):
        return "Error: buffer_m must be 400 or 800."
    coln = count_col_name(catg, buf)
    if coln not in tool_state["df"].columns:
        return f"Error: no output column for {catg} {buf}m."

    df = tool_state["df"]
    j = df.index[df["parcel_id"].astype(str) == pid]
    if len(j) == 0:
        return f"Error: unknown parcel_id={pid}"
    ji = j[0]

    psf = tool_state["parcels_sf_m"]
    p_geom = psf.loc[psf["parcel_id"].astype(str) == pid]
    if len(p_geom) != 1:
        return "Error: parcel geometry not found."
    parcel_row_geom = p_geom.geometry.iloc[0]
    buf_geom = parcel_row_geom.buffer(float(buf))

    pt = tool_state["pois_sf_m"]
    pt = pt[pt["normalized_category"].astype(str) == catg]
    if len(pt) < 1:
        df.at[ji, coln] = 0
        append_ctx_audit(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "api_round": int(api_round),
                "tool": "count_pois_within",
                "parcel_id": pid,
                "poi_category": catg,
                "buffer_m": buf,
                "count": 0,
            }
        )
        return "OK: count=0 (no POIs of category)."

    n_hit = int(pt.geometry.intersects(buf_geom).sum())
    df.at[ji, coln] = n_hit
    append_ctx_audit(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "count_pois_within",
            "parcel_id": pid,
            "poi_category": catg,
            "buffer_m": buf,
            "count": n_hit,
        }
    )
    return f"OK: count={n_hit} within {buf} m."


def run_record_context_note(args: dict[str, Any], api_round: int) -> str:
    args = args or {}
    pid = str(args.get("parcel_id") or "").strip()
    note = str(args.get("note") or "")
    if not pid:
        return "Error: parcel_id required."
    if len(note) > 180:
        note = note[:180]
    df = tool_state["df"]
    j = df.index[df["parcel_id"].astype(str) == pid]
    if len(j) == 0:
        return f"Error: unknown parcel_id={pid}"
    ji = j[0]
    df.at[ji, "ctx_context_note"] = note
    append_ctx_audit(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api_round": int(api_round),
            "tool": "record_context_note",
            "parcel_id": pid,
        }
    )
    return "OK: note stored."


def context_tool_definitions() -> list[dict[str, Any]]:
    cat_list = ", ".join(POI_CATEGORIES)
    return [
        {
            "type": "function",
            "function": {
                "name": "nearest_poi",
                "description": (
                    "Compute distance (meters) from parcel centroid to nearest POI of poi_category "
                    "(must match **normalized_category** on POI points)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parcel_id": {"type": "string"},
                        "poi_category": {"type": "string", "description": f"One of: {cat_list}"},
                        "max_search_m": {
                            "type": "number",
                            "description": "Ignore matches farther than this (default 5000).",
                        },
                    },
                    "required": ["parcel_id", "poi_category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "count_pois_within",
                "description": (
                    f"Count POI points of poi_category within buffer_m meters of the parcel polygon "
                    f"(buffer in EPSG:{METER_CRS})."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parcel_id": {"type": "string"},
                        "poi_category": {"type": "string", "description": cat_list},
                        "buffer_m": {"type": "integer", "description": "400 or 800 only."},
                    },
                    "required": ["parcel_id", "poi_category", "buffer_m"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "record_context_note",
                "description": "Short optional summary of which routing rules you applied (no fabricated numbers).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "parcel_id": {"type": "string"},
                        "note": {"type": "string", "description": "Max ~180 characters."},
                    },
                    "required": ["parcel_id", "note"],
                },
            },
        },
    ]


def dispatch_context_tool(name: str, args: dict[str, Any], api_round: int) -> str:
    if name == "nearest_poi":
        print(f"      🎯 nearest_poi parcel_id={args.get('parcel_id', '?')} cat={args.get('poi_category', '?')}")
        return run_nearest_poi(args, api_round)
    if name == "count_pois_within":
        print(f"      🔢 count_pois_within parcel_id={args.get('parcel_id', '?')}")
        return run_count_pois_within(args, api_round)
    if name == "record_context_note":
        print(f"      📝 record_context_note parcel_id={args.get('parcel_id', '?')}")
        return run_record_context_note(args, api_round)
    print(f"      ❓ unknown tool: {name}")
    return f"Unknown tool: {name}"


def call_context_chunk_ollama(
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
        "Apply **contextual routing** for every parcel in this chunk.\n\n"
        f"{data_blurb}\n\n---\nChunk {chunk_index} of {n_chunks}:\n\n"
        f"{chunk_csv_text}\n\n---\nCall tools for each parcel as the rules dictate. "
        "Then optionally **record_context_note** per parcel. Tool calls only (minimal prose)."
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


# 3. CHUNK PARCELS FOR LLM ###################################

cols_chunk = ["parcel_id"]
for c in ("zone_code", "primary_land_use", "allows_commercial", "allows_residential"):
    if c in parcels_tbl.columns:
        cols_chunk.append(c)
chunks_in = parcels_tbl[cols_chunk].copy()
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = len(chunks)
chunk_csv_texts = [c.to_csv(index=False) for c in chunks]
print(f"✂️  Split into {n_chunks} chunk(s) of up to {ROWS_PER_BATCH} rows.\n")

ctx_tools = context_tool_definitions()

# 4. PARALLEL CHUNK API CALLS ###################################

print("-----------------------------------------------------------------")
print("🔄 Step 2 — Ollama /api/chat per chunk (ThreadPoolExecutor)")
print("-----------------------------------------------------------------\n\n")


def _run_ctx(i: int) -> dict[str, Any]:
    return call_context_chunk_ollama(
        chunk_index=i,
        n_chunks=n_chunks,
        chunk_csv_text=chunk_csv_texts[i - 1],
        ollama_host=OLLAMA_HOST,
        ollama_key=OLLAMA_API_KEY,
        ollama_model=OLLAMA_MODEL,
        system_prompt=SYSTEM_CONTEXT,
        data_blurb=ROUTING_BLURB,
        tools=ctx_tools,
        max_output_tokens=MAX_OUT,
    )


with ThreadPoolExecutor(max_workers=FIXER_CHUNK_WORKERS) as ex:
    tmp: dict[int, dict[str, Any]] = {}
    futs = {ex.submit(_run_ctx, i): i for i in range(1, n_chunks + 1)}
    for fut in as_completed(futs):
        cr = fut.result()
        tmp[cr["chunk_index"]] = cr
    chunk_results = [tmp[i] for i in range(1, n_chunks + 1)]

# 5. APPLY TOOL CALLS ON MAIN PROCESS (CHUNK ORDER) ###################################

print("-----------------------------------------------------------------")
print("🔧 Step 3 — Execute spatial tools (chunk order)")
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
        dispatch_context_tool(name, args, api_round_counter)
        n_tools += 1

parcels_out = tool_state["df"]
parcels_out.to_csv(OUT_CSV, index=False, na_rep="")
print(f"\n   ✅ Wrote {OUT_CSV}\n")

# 6. WRITE CSV + MAP ###################################

print("\n-----------------------------------------------------------------")
print("🎨 Step 4 — Map (nearest transport, meters)")
print("-----------------------------------------------------------------\n")

parcels_map_sf = gpd.GeoDataFrame(
    parcels_out,
    geometry=gpd.GeoSeries.from_wkt(parcels_out["wkt"]),
    crs=WGS84_CRS,
)
pois_plot = gpd.GeoDataFrame(
    pois_tbl,
    geometry=gpd.points_from_xy(pois_tbl["x"], pois_tbl["y"]),
    crs=WGS84_CRS,
)

fig, ax = plt.subplots(figsize=(7, 5))
parcels_map_sf.plot(
    column="ctx_nearest_transport_m",
    ax=ax,
    edgecolor="gray",
    linewidth=0.25,
    legend=True,
    cmap="viridis",
    missing_kwds={"color": "lightgrey"},
)
pois_plot.plot(ax=ax, color="black", markersize=3, alpha=0.5)
ax.set_title("Parcels: nearest transport distance (m) + POI points")
ax.set_axis_off()
path_ctx = OUT_DIR / "map_parcels_context_transport.png"
fig.savefig(path_ctx, dpi=120, bbox_inches="tight")
plt.close(fig)
print(f"   💾 {path_ctx}\n")

# 7. CONSOLE SUMMARY ###################################

n_audit = 0
if AUDIT_PATH.is_file():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        n_audit = sum(1 for line in f if line.strip())
n_err = int(parcels_out["error_flag"].fillna(False).sum())

print("\n=================================================================")
print("📊 Summary (fixer_spatial_context.py)")
print("=================================================================")
print(f"📦 Chunks: {n_chunks} | tool calls: {n_tools} | audit lines: {n_audit}")
print(f"⚠️  Rows error_flag TRUE: {n_err} / {len(parcels_out)}")
print("=================================================================")
