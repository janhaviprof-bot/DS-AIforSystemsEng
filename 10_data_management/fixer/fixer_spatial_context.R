#' @name fixer_spatial_context.R
#' @title Contextual spatial routing — LLM picks sf-backed tools per parcel (batched Ollama)
#' @author Prof. Tim Fraser
#' @description
#' Topic: AI-assisted data management + GIS synthesis
#'
#' Joins **parcels** (polygons) with **POIs** (points). The model does **not** compute geometry;
#' it **routes** which **nearest_poi** / **count_pois_within** / **record_context_note** tools to call
#' based on **zone_code** and **primary_land_use**. All distances and counts are computed in R (**sf**).
#'
#' Demo data (**`data/parcels_zoning_raw.csv`**, **`data/pois_messy_raw.csv`**) has **24** parcels and
#' **24** POIs on a non-overlapping grid so, with default **ROWS_PER_BATCH=10**, **`fixer_spatial_context.R`**
#' runs **three** parcel chunks (teaching batched routing).
#'
#' **Inputs:** **`output/parcels_enriched.csv`** (needs **parcel_id**, **wkt**, **zone_code**,
#' **primary_land_use**) and **`output/pois_enriched.csv`** (**poi_id**, **x**, **y**,
#' **normalized_category**). Run **`fixer_parcels.R`** and **`fixer_pois.R`** first if those files
#' are missing columns.
#'
#' **Outputs:** **`output/parcels_context_enriched.csv`**, **`output/context_routing_audit.jsonl`**,
#' **`output/map_parcels_context_transport.png`**.

# 0. SETUP ###################################

cat("\n")
cat("=================================================================\n")
cat("🧭 fixer_spatial_context.R — contextual tool routing + sf\n")
cat("=================================================================\n\n")

## 0.1 Load packages #################################
# dplyr/tidy selection; readr I/O; httr2 is loaded before sourcing functions.R in other fixers;
# jsonlite audit lines; stringr path/env trimming; purrr over chunks; sf geometry; ggplot2 map;
# future/furrr parallel chunk HTTP (same pattern as fixer_csv.R / fixer_parcels.R).

cat("📦 Loading R packages (dplyr, readr, httr2, jsonlite, stringr, purrr, sf, ggplot2, future, furrr) ...\n")
library(dplyr) # select, mutate, any_of
library(readr) # read_csv, write_csv, format_csv
library(httr2) # optional debugging of HTTP failures when extending ollama_chat_once
library(jsonlite) # audit JSONL
library(stringr) # str_trim, str_extract for FIXER_ROOT
library(purrr) # map_chr over chunk text
library(sf) # st_as_sf, distances, buffers (metric CRS)
library(ggplot2) # choropleth + POI overlay
library(future) # multisession plan for furrr
library(furrr) # future_map: one Ollama request per parcel chunk
cat("   ✅ Packages ready.\n\n")

## 0.2 Paths and outputs #################################

cat("📁 Resolving fixer folder and paths ...\n")
REPO = stringr::str_extract(getwd(), ".*dsai")
FIXER_ROOT = paste0(REPO, "/10_data_management/fixer")
setwd(FIXER_ROOT)
cat("   📍 FIXER_ROOT: ", FIXER_ROOT, "\n", sep = "")

# Enriched parcel/POI tables (defaults); override for other studies via env.
PARCELS_PATH = Sys.getenv(
  "FIXER_CONTEXT_PARCELS",
  unset = file.path(FIXER_ROOT, "output", "parcels_enriched.csv")
)
POIS_PATH = Sys.getenv(
  "FIXER_CONTEXT_POIS",
  unset = file.path(FIXER_ROOT, "output", "pois_enriched.csv")
)
OUT_CSV = file.path(FIXER_ROOT, "output", "parcels_context_enriched.csv")
AUDIT_PATH = file.path(FIXER_ROOT, "output", "context_routing_audit.jsonl")
OUT_DIR = file.path(FIXER_ROOT, "output")
cat("   📄 Parcels: ", PARCELS_PATH, "\n", sep = "")
cat("   📄 POIs:    ", POIS_PATH, "\n", sep = "")
cat("   💾 Output:  ", OUT_CSV, "\n\n", sep = "")

## 0.3 Environment and Ollama #################################

env_path = file.path(FIXER_ROOT, ".env")
cat("🔐 Loading .env ...\n")
if (file.exists(env_path)) {
  readRenviron(env_path)
} else {
  stop("No .env in fixer folder; create one with OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL.")
}
cat("   ✅ .env read from fixer folder.\n\n")

OLLAMA_HOST = Sys.getenv("OLLAMA_HOST", unset = "https://ollama.com")
OLLAMA_API_KEY = Sys.getenv("OLLAMA_API_KEY", unset = "")
OLLAMA_MODEL = Sys.getenv("OLLAMA_MODEL", unset = "nemotron-3-nano:30b-cloud")
cat("☁️  Ollama: host = ", OLLAMA_HOST, "\n", sep = "")
cat("   model  = ", OLLAMA_MODEL, "\n\n", sep = "")

# Chunk size: rows per single chat request (24 parcels → 3 API rounds when ROWS_PER_BATCH=10).
read_env_digits = function(nm, default) {
  s = stringr::str_trim(Sys.getenv(nm, unset = as.character(default)))
  if (nzchar(s) && grepl("^[0-9]+$", s)) {
    v = as.integer(s)
    if (!is.na(v) && v >= 1L) {
      return(v)
    }
  }
  as.integer(default)
}
ROWS_PER_BATCH = read_env_digits("ROWS_PER_BATCH", 10L)
# Parallel Ollama requests only — tool execution stays sequential on the main process.
FIXER_CHUNK_WORKERS = read_env_digits("FIXER_CHUNK_WORKERS", 1L)
cat("📊 ROWS_PER_BATCH = ", ROWS_PER_BATCH, " (env ROWS_PER_BATCH)\n", sep = "")
cat("📊 FIXER_CHUNK_WORKERS = ", FIXER_CHUNK_WORKERS, " (env FIXER_CHUNK_WORKERS)\n\n", sep = "")

MAX_OUT = {
  et = stringr::str_trim(Sys.getenv("FIXER_MAX_OUTPUT_TOKENS", unset = ""))
  if (nzchar(et) && grepl("^[0-9]+$", et)) as.integer(et) else NULL
}

cat("🔌 Sourcing fixer/functions.R ...\n")
source(file.path(FIXER_ROOT, "functions.R"), local = FALSE)
cat("   ✅ Helpers loaded.\n\n")

## 0.4 CRS, POI vocabulary, and LLM prompts #################################
# WGS84 for storage/maps; projected CRS for buffers and planar distances in meters.
WGS84_CRS = 4326L
METER_CRS = 32617L # WGS 84 / UTM zone 17N — appropriate for Ithaca-area demo lon ~ -76.

# Must match normalized_category vocabulary from fixer_pois.R (closed set for tool schemas).
POI_CATEGORIES = c(
  "healthcare", "food_retail", "retail", "financial", "transport",
  "recreation", "parking", "childcare", "agriculture", "vacant",
  "public_government", "other"
)

# User-visible data dictionary + routing rubric (mirrors role of DATA_QUALITY_BLURB in fixer_csv.R).
ROUTING_BLURB = paste0(
  "## Your job (contextual routing)\n",
  "For **each parcel_id** in the chunk, decide **which spatial tools** to call. ",
  "Geometry is computed **only** inside tools—**never** invent distances or counts in prose.\n\n",
  "## Parcel attributes you see\n",
  "- **zone_code** (e.g. R-1, C-1, I-1, MIX, OS, C-2, PUD)\n",
  "- **primary_land_use** (e.g. residential, commercial, industrial, mixed, open_space, institutional, other)\n\n",
  "## Routing rules (apply per row; call multiple tools when appropriate)\n",
  "1. **Residential** (`primary_land_use` is residential **or** `zone_code` matches `^R-`): ",
  "**nearest_poi** with **poi_category**=`transport`; **count_pois_within** **food_retail** buffer_m=400 (walkable food).\n",
  "2. **Commercial** (`commercial` **or** `zone_code` in C-1, C-2): ",
  "**count_pois_within** **retail** 400m; **nearest_poi** **transport**.\n",
  "3. **Mixed** (`mixed` **or** `zone_code` is MIX or PUD): ",
  "**nearest_poi** **transport**; **count_pois_within** **retail** 400m; **count_pois_within** **food_retail** 400m.\n",
  "4. **Open space** (`open_space` **or** `zone_code` is OS): ",
  "**nearest_poi** **recreation**; **count_pois_within** **parking** 400m.\n",
  "5. **Industrial** (`industrial` **or** `zone_code` matches `^I-`): ",
  "**nearest_poi** **transport**; optional **nearest_poi** **healthcare**.\n",
  "6. **Institutional**: **nearest_poi** **healthcare**; **count_pois_within** **parking** 400m.\n",
  "7. **Other / unknown** land use: at least **nearest_poi** **transport**.\n\n",
  "## After spatial tools\n",
  "Optionally call **record_context_note** for that **parcel_id** (<=180 chars): short summary of **which** rules you applied (no numeric fabrication).\n\n",
  "## Tool constraints\n",
  "- **nearest_poi** **poi_category** must be one of: ",
  paste(POI_CATEGORIES, collapse = ", "), ".\n",
  "- **count_pois_within**: **buffer_m** must be **400** or **800**.\n",
  "- **max_search_m** on **nearest_poi** defaults to 5000 (meters).\n"
)

# Short system line: model emits tool calls only; geometry is never invented.
SYSTEM_CONTEXT = paste0(
  "You are a **spatial analysis router**. Each user message is a CSV chunk of parcels with ",
  "**zone_code** and **primary_land_use**. You choose **nearest_poi**, **count_pois_within**, ",
  "and optional **record_context_note** tool calls so that R can compute distances and counts. ",
  "Do **not** output made-up distances. **parcel_id** must match the chunk. ",
  "Emit tool calls only (minimal prose)."
)

# 1. LOAD DATA + BUILD SF ###################################

cat("-----------------------------------------------------------------\n")
cat("📂 Step 1 — Load parcels, POIs, build sf (metric CRS for ops)\n")
cat("-----------------------------------------------------------------\n")

invisible(dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE))
if (file.exists(AUDIT_PATH)) {
  invisible(file.remove(AUDIT_PATH))
}

parcels_tbl = readr::read_csv(PARCELS_PATH, show_col_types = FALSE)
pois_tbl = readr::read_csv(POIS_PATH, show_col_types = FALSE)

req_p = c("parcel_id", "wkt", "zone_code")
miss_p = setdiff(req_p, names(parcels_tbl))
if (length(miss_p)) {
  stop("Parcels file missing columns: ", paste(miss_p, collapse = ", "))
}
if (!"primary_land_use" %in% names(parcels_tbl)) {
  parcels_tbl$primary_land_use = NA_character_
  cat("   ⚠️  No primary_land_use column — routing uses zone_code only; enrich parcels first for best results.\n")
}

req_i = c("poi_id", "x", "y", "normalized_category")
miss_i = setdiff(req_i, names(pois_tbl))
if (length(miss_i)) {
  stop("POIs file missing columns: ", paste(miss_i, collapse = ", "))
}

## 1.2 Initialize ctx_* output columns (wide result table) #################################
# One count column per (POI category × buffer 400/800 m); one nearest pair per category.
ctx_count_cols = purrr::map(POI_CATEGORIES, function(cat) {
  paste0("ctx_n_", cat, "_", c(400L, 800L))
}) |>
  unlist(use.names = FALSE)
ctx_nearest_cols = purrr::map(POI_CATEGORIES, function(cat) {
  c(paste0("ctx_nearest_", cat, "_m"), paste0("ctx_nearest_", cat, "_poi_id"))
}) |>
  unlist(use.names = FALSE)
for (cn in unique(ctx_count_cols)) {
  if (!cn %in% names(parcels_tbl)) {
    parcels_tbl[[cn]] = NA_integer_
  }
}
for (cn in ctx_nearest_cols) {
  if (!cn %in% names(parcels_tbl)) {
    if (grepl("_poi_id$", cn)) {
      parcels_tbl[[cn]] = NA_integer_
    } else {
      parcels_tbl[[cn]] = NA_real_
    }
  }
}
if (!"ctx_context_note" %in% names(parcels_tbl)) {
  parcels_tbl$ctx_context_note = NA_character_
}
if (!"error_flag" %in% names(parcels_tbl)) {
  parcels_tbl$error_flag = FALSE
}

## 1.3 Simple features: WGS84 for I/O and maps; metric CRS for st_distance / st_buffer #################################

parcels_sf = parcels_tbl |>
  sf::st_as_sf(wkt = "wkt", crs = WGS84_CRS, remove = FALSE)
parcels_sf_m = sf::st_transform(parcels_sf, METER_CRS)

pois_sf = pois_tbl |>
  sf::st_as_sf(coords = c("x", "y"), crs = WGS84_CRS, remove = FALSE)
pois_sf_m = sf::st_transform(pois_sf, METER_CRS)

cat("   ✅ Parcels: ", nrow(parcels_tbl), " | POIs: ", nrow(pois_tbl), "\n", sep = "")
cat("   🗺️  Ops CRS: EPSG:", METER_CRS, " (buffers / distances in meters)\n\n", sep = "")

# 2. TOOL STATE + HANDLERS ###################################
# Mutable env: in-memory parcel table, frozen sf layers for geometry ops, audit path.
# Pattern matches fixer_csv.R tool_state + dispatch (single-turn tool apply, no second LLM round).

tool_state = new.env(parent = emptyenv())
tool_state$df = parcels_tbl
tool_state$parcels_sf_m = parcels_sf_m
tool_state$pois_sf_m = pois_sf_m
tool_state$pois_tbl = pois_tbl
tool_state$audit_path = AUDIT_PATH
tool_state$api_round = 0L

#' @name append_ctx_audit
#' @title Append one JSON line to context_routing_audit.jsonl
append_ctx_audit = function(obj) {
  line = paste0(jsonlite::toJSON(obj, auto_unbox = TRUE), "\n")
  cat(line, file = tool_state$audit_path, append = TRUE)
}

#' @name nearest_col_names
#' @title Map POI category to ctx_nearest_* column names in tool_state$df
nearest_col_names = function(poi_category) {
  m = paste0("ctx_nearest_", poi_category, "_m")
  id = paste0("ctx_nearest_", poi_category, "_poi_id")
  if (!all(c(m, id) %in% names(tool_state$df))) {
    return(NULL)
  }
  c(m, id)
}

#' @name count_col_name
#' @title Column name for count_pois_within result
count_col_name = function(poi_category, buffer_m) {
  paste0("ctx_n_", poi_category, "_", buffer_m)
}

#' @name run_nearest_poi
#' @title Tool implementation: centroid-to-POI distances in METER_CRS
run_nearest_poi = function(args, api_round) {
  args = args %||% list()
  pid = as.character(args$parcel_id %||% "")
  if (!nzchar(pid)) {
    return("Error: parcel_id required.")
  }
  catg = as.character(args$poi_category %||% "")
  if (!catg %in% POI_CATEGORIES) {
    return(paste0("Error: invalid poi_category: ", catg))
  }
  cols = nearest_col_names(catg)
  if (is.null(cols)) {
    return(paste0("Error: nearest_poi column missing for category ", catg, "."))
  }
  max_m = as.numeric(args$max_search_m %||% 5000)
  if (is.na(max_m) || max_m <= 0) {
    max_m = 5000
  }

  j = which(as.character(tool_state$df$parcel_id) == pid)
  if (!length(j)) {
    return(paste0("Error: unknown parcel_id=", pid))
  }
  j = j[[1L]]

  p_geom = tool_state$parcels_sf_m[tool_state$parcels_sf_m$parcel_id == pid, ]
  if (nrow(p_geom) != 1L) {
    return("Error: parcel geometry not found.")
  }
  ctr = sf::st_centroid(sf::st_geometry(p_geom))

  pt = tool_state$pois_sf_m
  pt = pt[as.character(pt$normalized_category) == catg, , drop = FALSE]
  if (nrow(pt) < 1L) {
    tool_state$df[[cols[[1]]]][[j]] = NA_real_
    tool_state$df[[cols[[2]]]][[j]] = NA_integer_
    append_ctx_audit(list(
      ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
      api_round = as.integer(api_round),
      tool = "nearest_poi",
      parcel_id = pid,
      poi_category = catg,
      result = "no_pois_of_category"
    ))
    return(paste0("OK: no ", catg, " POIs; stored NA."))
  }

  d = sf::st_distance(ctr, sf::st_geometry(pt), by_element = FALSE)
  d_m = as.numeric(d[1L, ])
  imin = which.min(d_m)
  best_d = d_m[[imin]]
  if (best_d > max_m) {
    tool_state$df[[cols[[1]]]][[j]] = NA_real_
    tool_state$df[[cols[[2]]]][[j]] = NA_integer_
    append_ctx_audit(list(
      ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
      api_round = as.integer(api_round),
      tool = "nearest_poi",
      parcel_id = pid,
      poi_category = catg,
      result = "beyond_max_search_m",
      distance_m = best_d
    ))
    return("OK: nearest beyond max_search_m; stored NA.")
  }

  best_id = as.integer(pt$poi_id[[imin]])
  tool_state$df[[cols[[1]]]][[j]] = best_d
  tool_state$df[[cols[[2]]]][[j]] = best_id
  append_ctx_audit(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "nearest_poi",
    parcel_id = pid,
    poi_category = catg,
    distance_m = best_d,
    nearest_poi_id = best_id
  ))
  paste0("OK: nearest ", catg, " = ", round(best_d, 1), " m (poi_id=", best_id, ").")
}

#' @name run_count_pois_within
#' @title Tool implementation: st_buffer + st_intersects counts
run_count_pois_within = function(args, api_round) {
  args = args %||% list()
  pid = as.character(args$parcel_id %||% "")
  if (!nzchar(pid)) {
    return("Error: parcel_id required.")
  }
  catg = as.character(args$poi_category %||% "")
  if (!catg %in% POI_CATEGORIES) {
    return(paste0("Error: invalid poi_category: ", catg))
  }
  buf = as.integer(args$buffer_m %||% NA_integer_)
  if (!buf %in% c(400L, 800L)) {
    return("Error: buffer_m must be 400 or 800.")
  }
  coln = count_col_name(catg, buf)
  if (!coln %in% names(tool_state$df)) {
    return(paste0("Error: no output column for ", catg, " ", buf, "m."))
  }

  j = which(as.character(tool_state$df$parcel_id) == pid)
  if (!length(j)) {
    return(paste0("Error: unknown parcel_id=", pid))
  }
  j = j[[1L]]

  p_geom = tool_state$parcels_sf_m[tool_state$parcels_sf_m$parcel_id == pid, ]
  if (nrow(p_geom) != 1L) {
    return("Error: parcel geometry not found.")
  }
  # Buffer distance is in meters because parcels_sf_m uses METER_CRS.
  buf_geom = sf::st_buffer(sf::st_geometry(p_geom), dist = as.numeric(buf))
  pt = tool_state$pois_sf_m
  pt = pt[as.character(pt$normalized_category) == catg, , drop = FALSE]
  if (nrow(pt) < 1L) {
    tool_state$df[[coln]][[j]] = 0L
    append_ctx_audit(list(
      ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
      api_round = as.integer(api_round),
      tool = "count_pois_within",
      parcel_id = pid,
      poi_category = catg,
      buffer_m = buf,
      count = 0L
    ))
    return("OK: count=0 (no POIs of category).")
  }

  # Count POI points whose geometry intersects the buffer polygon.
  ii = sf::st_intersects(buf_geom, sf::st_geometry(pt), sparse = TRUE)
  n_hit = length(ii[[1L]])
  tool_state$df[[coln]][[j]] = as.integer(n_hit)
  append_ctx_audit(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "count_pois_within",
    parcel_id = pid,
    poi_category = catg,
    buffer_m = buf,
    count = as.integer(n_hit)
  ))
  paste0("OK: count=", n_hit, " within ", buf, " m.")
}

#' @name run_record_context_note
#' @title Optional prose note only (no numeric fabrication)
run_record_context_note = function(args, api_round) {
  args = args %||% list()
  pid = as.character(args$parcel_id %||% "")
  note = as.character(args$note %||% "")
  if (!nzchar(pid)) {
    return("Error: parcel_id required.")
  }
  if (nchar(note) > 180L) {
    note = substr(note, 1L, 180L)
  }
  j = which(as.character(tool_state$df$parcel_id) == pid)
  if (!length(j)) {
    return(paste0("Error: unknown parcel_id=", pid))
  }
  j = j[[1L]]
  tool_state$df$ctx_context_note[[j]] = note
  append_ctx_audit(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "record_context_note",
    parcel_id = pid
  ))
  "OK: note stored."
}

#' @name context_tool_definitions
#' @title Ollama tool schemas for nearest / count / note
context_tool_definitions = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "nearest_poi",
        description = paste0(
          "Compute distance (meters) from parcel centroid to nearest POI of poi_category ",
          "(must match **normalized_category** on POI points)."
        ),
        parameters = list(
          type = "object",
          properties = list(
            parcel_id = list(type = "string"),
            poi_category = list(
              type = "string",
              description = paste("One of:", paste(POI_CATEGORIES, collapse = ", "))
            ),
            max_search_m = list(type = "number", description = "Ignore matches farther than this (default 5000).")
          ),
          required = list("parcel_id", "poi_category")
        )
      )
    ),
    list(
      type = "function",
      `function` = list(
        name = "count_pois_within",
        description = paste0(
          "Count POI points of poi_category within buffer_m meters of the parcel polygon (buffer in EPSG:",
          METER_CRS, ")."
        ),
        parameters = list(
          type = "object",
          properties = list(
            parcel_id = list(type = "string"),
            poi_category = list(type = "string", description = paste(POI_CATEGORIES, collapse = ", ")),
            buffer_m = list(type = "integer", description = "400 or 800 only.")
          ),
          required = list("parcel_id", "poi_category", "buffer_m")
        )
      )
    ),
    list(
      type = "function",
      `function` = list(
        name = "record_context_note",
        description = "Short optional summary of which routing rules you applied (no fabricated numbers).",
        parameters = list(
          type = "object",
          properties = list(
            parcel_id = list(type = "string"),
            note = list(type = "string", description = "Max ~180 characters.")
          ),
          required = list("parcel_id", "note")
        )
      )
    )
  )
}

#' @name dispatch_context_tool
#' @title Route executed tool name to run_* handler
dispatch_context_tool = function(name, args, api_round) {
  if (name == "nearest_poi") {
    cat("      🎯 nearest_poi parcel_id=", args$parcel_id %||% "?", " cat=", args$poi_category %||% "?", "\n", sep = "")
    return(run_nearest_poi(args, api_round))
  }
  if (name == "count_pois_within") {
    cat("      🔢 count_pois_within parcel_id=", args$parcel_id %||% "?", "\n", sep = "")
    return(run_count_pois_within(args, api_round))
  }
  if (name == "record_context_note") {
    cat("      📝 record_context_note parcel_id=", args$parcel_id %||% "?", "\n", sep = "")
    return(run_record_context_note(args, api_round))
  }
  cat("      ❓ unknown tool: ", name, "\n", sep = "")
  paste0("Unknown tool: ", name)
}

call_context_chunk_ollama = function(
  chunk_index,
  n_chunks,
  chunk_csv_text,
  fixer_root,
  ollama_host,
  ollama_key,
  ollama_model,
  system_prompt,
  data_blurb,
  tools,
  max_output_tokens
) {
  source(file.path(fixer_root, "functions.R"), local = FALSE)
  user_msg = paste0(
    "Apply **contextual routing** for every parcel in this chunk.\n\n",
    data_blurb,
    "\n\n---\nChunk ",
    chunk_index,
    " of ",
    n_chunks,
    ":\n\n",
    chunk_csv_text,
    "\n\n---\nCall tools for each parcel as the rules dictate. ",
    "Then optionally **record_context_note** per parcel. Tool calls only (minimal prose)."
  )
  messages = list(
    list(role = "system", content = system_prompt),
    list(role = "user", content = user_msg)
  )
  out = tryCatch(
    ollama_chat_once(
      ollama_host,
      ollama_key,
      ollama_model,
      messages,
      tools = tools,
      format = NULL,
      max_output_tokens = max_output_tokens
    ),
    error = function(e) {
      list(error = e, message = list(), content = "")
    }
  )
  if (!is.null(out$error)) {
    return(list(
      chunk_index = chunk_index,
      tool_calls = list(),
      error = conditionMessage(out$error),
      content = ""
    ))
  }
  msg = out$message %||% list()
  list(
    chunk_index = chunk_index,
    tool_calls = msg$tool_calls %||% list(),
    error = NULL,
    content = out$content %||% ""
  )
}

# 3. CHUNK PARCELS FOR LLM ###################################
# Omit wkt from the CSV sent to the model — saves tokens; parcel_id keys tool calls.

chunks_in = parcels_tbl |>
  dplyr::select(
    "parcel_id",
    dplyr::any_of(c("zone_code", "primary_land_use", "allows_commercial", "allows_residential"))
  )
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = length(chunks)
chunk_csv_texts = purrr::map_chr(chunks, function(ch) readr::format_csv(ch))
cat("✂️  Split into ", n_chunks, " chunk(s) of up to ", ROWS_PER_BATCH, " rows.\n\n", sep = "")

ctx_tools = context_tool_definitions()

# 4. PARALLEL CHUNK API CALLS ###################################

cat("-----------------------------------------------------------------\n")
cat("🔄 Step 2 — Ollama /api/chat per chunk (furrr)\n")
cat("-----------------------------------------------------------------\n\n")

future::plan(future::multisession, workers = FIXER_CHUNK_WORKERS)

chunk_results = furrr::future_map(
  seq_len(n_chunks),
  function(i) {
    call_context_chunk_ollama(
      chunk_index = i,
      n_chunks = n_chunks,
      chunk_csv_text = chunk_csv_texts[[i]],
      fixer_root = FIXER_ROOT,
      ollama_host = OLLAMA_HOST,
      ollama_key = OLLAMA_API_KEY,
      ollama_model = OLLAMA_MODEL,
      system_prompt = SYSTEM_CONTEXT,
      data_blurb = ROUTING_BLURB,
      tools = ctx_tools,
      max_output_tokens = MAX_OUT
    )
  },
  .options = furrr::furrr_options(seed = TRUE)
)

future::plan(future::sequential)

# 5. APPLY TOOL CALLS ON MAIN PROCESS (CHUNK ORDER) ###################################

cat("-----------------------------------------------------------------\n")
cat("🔧 Step 3 — Execute spatial tools (chunk order)\n")
cat("-----------------------------------------------------------------\n\n")

api_round_counter = 0L
n_tools = 0L

for (cr in chunk_results) {
  ci = cr$chunk_index
  if (!is.null(cr$error)) {
    cat("   ❌ Chunk ", ci, ": ", cr$error, "\n", sep = "")
    pids = as.character(chunks[[ci]]$parcel_id)
    for (pid in pids) {
      jj = which(as.character(tool_state$df$parcel_id) == pid)
      if (length(jj)) {
        tool_state$df$error_flag[[jj[[1L]]]] = TRUE
      }
    }
    next
  }
  tcalls = cr$tool_calls %||% list()
  if (!length(tcalls)) {
    cat("   ⚠️  Chunk ", ci, ": no tool calls\n", sep = "")
    pids = as.character(chunks[[ci]]$parcel_id)
    for (pid in pids) {
      jj = which(as.character(tool_state$df$parcel_id) == pid)
      if (length(jj)) {
        tool_state$df$error_flag[[jj[[1L]]]] = TRUE
      }
    }
    next
  }
  cat("   📦 Chunk ", ci, ": ", length(tcalls), " tool call(s)\n", sep = "")
  for (tc in tcalls) {
    if (!is.list(tc)) {
      next
    }
    api_round_counter = api_round_counter + 1L
    tool_state$api_round = api_round_counter
    fn = tc[["function"]] %||% list()
    name = as.character(fn$name %||% "")
    args = parse_function_arguments(fn$arguments)
    dispatch_context_tool(name, args, api_round_counter)
    n_tools = n_tools + 1L
  }
}

parcels_out = tool_state$df

readr::write_csv(parcels_out, OUT_CSV)
cat("\n   ✅ Wrote ", OUT_CSV, "\n", sep = "")

# 6. WRITE CSV + MAP ###################################

cat("\n-----------------------------------------------------------------\n")
cat("🎨 Step 4 — Map (nearest transport, meters)\n")
cat("-----------------------------------------------------------------\n")

parcels_map_sf = parcels_out |>
  sf::st_as_sf(wkt = "wkt", crs = WGS84_CRS, remove = FALSE)

p_ctx = ggplot2::ggplot(parcels_map_sf) +
  ggplot2::geom_sf(ggplot2::aes(fill = .data$ctx_nearest_transport_m), color = "gray25", linewidth = 0.25) +
  ggplot2::geom_sf(data = pois_sf, inherit.aes = FALSE, size = 0.6, alpha = 0.5, color = "black") +
  ggplot2::coord_sf(crs = sf::st_crs(WGS84_CRS)) +
  ggplot2::scale_fill_viridis_c(option = "C", na.value = "grey90") +
  ggplot2::theme_minimal() +
  ggplot2::labs(
    title = "Parcels: nearest transport distance (m) + POI points",
    fill = "m"
  )

path_ctx = file.path(OUT_DIR, "map_parcels_context_transport.png")
ggplot2::ggsave(path_ctx, p_ctx, width = 7, height = 5, dpi = 120)
cat("   💾 ", path_ctx, "\n", sep = "")

# 7. CONSOLE SUMMARY ###################################

n_audit = if (file.exists(AUDIT_PATH)) sum(nzchar(readr::read_lines(AUDIT_PATH))) else 0L
n_err = sum(parcels_out$error_flag, na.rm = TRUE)

cat("\n=================================================================\n")
cat("📊 Summary (fixer_spatial_context.R)\n")
cat("=================================================================\n")
cat("📦 Chunks: ", n_chunks, " | tool calls: ", n_tools, " | audit lines: ", n_audit, "\n", sep = "")
cat("⚠️  Rows error_flag TRUE: ", n_err, " / ", nrow(parcels_out), "\n", sep = "")
cat("=================================================================\n")
