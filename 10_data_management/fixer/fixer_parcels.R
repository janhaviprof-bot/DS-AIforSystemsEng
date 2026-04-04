#' @name fixer_parcels.R
#' @title Batched parcel zoning enrichment — one Ollama round per N rows + furrr (Ollama tools)
#' @author Prof. Tim Fraser
#' @description
#' Topic: AI-assisted data management + GIS
#'
#' Parcels are **non-overlapping polygons** in column **wkt** (WGS84). Each chunk of **ROWS_PER_BATCH**
#' rows gets one `/api/chat`; the model returns many **record_parcel_zoning** tool calls.
#' Raw: **data/parcels_zoning_raw.csv**; outputs: **output/parcels_enriched.csv**,
#' **output/parcels_enrich_audit.jsonl**, map PNGs.

# 0. SETUP ###################################

cat("\n")
cat("=================================================================\n")
cat("🏘️  fixer_parcels.R — batched zoning tools + polygons (Ollama Cloud)\n")
cat("=================================================================\n\n")

cat("📦 Loading R packages (dplyr, readr, httr2, jsonlite, stringr, purrr, sf, ggplot2, future, furrr) ...\n")
library(dplyr)
library(readr)
library(httr2)
library(jsonlite)
library(stringr)
library(purrr)
library(sf)
library(ggplot2)
library(future)
library(furrr)
cat("   ✅ Packages ready.\n\n")

cat("📁 Resolving fixer folder and paths ...\n")
REPO = stringr::str_extract(getwd(), ".*dsai")
FIXER_ROOT = paste0(REPO, "/10_data_management/fixer")
setwd(FIXER_ROOT)
cat("   📍 FIXER_ROOT: ", FIXER_ROOT, "\n", sep = "")

PARCELS_PATH = file.path(FIXER_ROOT, "data", "parcels_zoning_raw.csv")
OUT_CSV = file.path(FIXER_ROOT, "output", "parcels_enriched.csv")
AUDIT_PATH = file.path(FIXER_ROOT, "output", "parcels_enrich_audit.jsonl")
OUT_DIR = file.path(FIXER_ROOT, "output")
cat("   📄 Parcels: ", PARCELS_PATH, "\n", sep = "")
cat("   💾 Output:  ", OUT_CSV, "\n\n", sep = "")

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
FIXER_CHUNK_WORKERS = read_env_digits("FIXER_CHUNK_WORKERS", 1L)
cat("📊 ROWS_PER_BATCH = ", ROWS_PER_BATCH, "\n", sep = "")
cat("📊 FIXER_CHUNK_WORKERS = ", FIXER_CHUNK_WORKERS, "\n\n", sep = "")

MAX_OUT = {
  et = stringr::str_trim(Sys.getenv("FIXER_MAX_OUTPUT_TOKENS", unset = ""))
  if (nzchar(et) && grepl("^[0-9]+$", et)) as.integer(et) else NULL
}

cat("🔌 Sourcing fixer/functions.R ...\n")
source(file.path(FIXER_ROOT, "functions.R"), local = FALSE)
cat("   ✅ Helpers loaded.\n\n")

WGS84_CRS = 4326L

ZONING_DATA_BLURB = paste0(
  "## Parcel table\n",
  "Each row is one **parcel polygon** (column **wkt**). **parcel_id** is the stable key. ",
  "**zone_code** is a short label; **zoning_excerpt** is ordinance-style prose to interpret.\n\n",
  "## Output fields (one tool call per row)\n",
  "- **primary_land_use**: exactly one of ",
  "\"residential\", \"commercial\", \"industrial\", \"mixed\", \"open_space\", \"institutional\", \"other\".\n",
  "- **allows_residential**, **allows_commercial**, **parking_mentioned**: booleans true/false.\n",
  "- **notes**: <= 120 characters summarizing uncertainty or key cues.\n"
)

SYSTEM_PARCELS = paste0(
  "You extract structured zoning attributes from short ordinance excerpts for a **batch** of parcel rows. ",
  "Reply using **record_parcel_zoning** tool calls only (one per parcel_id in the chunk). ",
  "Booleans must be true/false. primary_land_use must be one of the allowed values. ",
  "Do not invent parcel_id values. Do not modify **wkt** geometry."
)

# 1. TOOL STATE + DEFINITIONS ###################################

tool_state = new.env(parent = emptyenv())
tool_state$df = NULL
tool_state$audit_path = AUDIT_PATH
tool_state$api_round = 0L

append_audit_parcel = function(obj) {
  line = paste0(jsonlite::toJSON(obj, auto_unbox = TRUE), "\n")
  cat(line, file = tool_state$audit_path, append = TRUE)
}

coerce_bool = function(x) {
  if (is.null(x)) {
    return(NA)
  }
  if (is.logical(x) && length(x) == 1L) {
    return(x)
  }
  s = tolower(stringr::str_trim(as.character(x)))
  if (s %in% c("true", "1", "yes")) {
    return(TRUE)
  }
  if (s %in% c("false", "0", "no")) {
    return(FALSE)
  }
  as.logical(NA)
}

run_record_parcel_zoning = function(args, api_round) {
  args = args %||% list()
  pid = args$parcel_id
  if (is.null(pid) || !nzchar(as.character(pid))) {
    return("Error: parcel_id required.")
  }
  pid = as.character(pid)
  df = tool_state$df
  j = which(as.character(df$parcel_id) == pid)
  if (!length(j)) {
    return(paste0("Error: unknown parcel_id=", pid))
  }
  j = j[[1L]]
  plu = as.character(args$primary_land_use %||% NA_character_)
  tool_state$df$primary_land_use[[j]] = plu
  tool_state$df$allows_residential[[j]] = coerce_bool(args$allows_residential)
  tool_state$df$allows_commercial[[j]] = coerce_bool(args$allows_commercial)
  tool_state$df$parking_mentioned[[j]] = coerce_bool(args$parking_mentioned)
  tool_state$df$notes[[j]] = as.character(args$notes %||% NA_character_)
  append_audit_parcel(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "record_parcel_zoning",
    parcel_id = pid
  ))
  paste0("OK: parcel_id=", pid, " updated.")
}

parcel_tool_definitions = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "record_parcel_zoning",
        description = paste0(
          "Store LLM-derived zoning tags for one parcel. parcel_id must match the chunk CSV. ",
          "Infer fields from zoning_excerpt; leave notes concise (<=120 chars)."
        ),
        parameters = list(
          type = "object",
          properties = list(
            parcel_id = list(type = "string", description = "parcel_id from the CSV row."),
            primary_land_use = list(
              type = "string",
              description = paste0(
                "One of: residential, commercial, industrial, mixed, open_space, institutional, other."
              )
            ),
            allows_residential = list(type = "boolean"),
            allows_commercial = list(type = "boolean"),
            parking_mentioned = list(type = "boolean"),
            notes = list(type = "string", description = "Short rationale or caveats (<=120 chars).")
          ),
          required = list(
            "parcel_id",
            "primary_land_use",
            "allows_residential",
            "allows_commercial",
            "parking_mentioned",
            "notes"
          )
        )
      )
    )
  )
}

dispatch_parcel_tool = function(name, args, api_round) {
  if (name == "record_parcel_zoning") {
    cat("      ✏️  record_parcel_zoning parcel_id=", args$parcel_id %||% "?", "\n", sep = "")
    return(run_record_parcel_zoning(args, api_round))
  }
  cat("      ❓ unknown tool: ", name, "\n", sep = "")
  paste0("Unknown tool: ", name)
}

call_parcel_chunk_ollama = function(
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
    "Task: for each parcel in the chunk, call **record_parcel_zoning** once (use **parcel_id** from the CSV).\n\n",
    data_blurb,
    "\n\n---\nChunk ",
    chunk_index,
    " of ",
    n_chunks,
    " (EPSG:4326 polygons in **wkt**; do not edit geometry).\n\n",
    chunk_csv_text,
    "\n\n---\nEmit one **record_parcel_zoning** per row. Reply with tool calls only (minimal prose)."
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

# 2. LOAD DATA ###################################

cat("-----------------------------------------------------------------\n")
cat("📂 Step 1 — Load parcels (polygon WKT)\n")
cat("-----------------------------------------------------------------\n")

invisible(dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE))
if (file.exists(AUDIT_PATH)) {
  invisible(file.remove(AUDIT_PATH))
}

parcels_in = readr::read_csv(PARCELS_PATH, show_col_types = FALSE)
stopifnot("parcel_id" %in% names(parcels_in), "wkt" %in% names(parcels_in))

parcels_tbl = parcels_in |>
  dplyr::mutate(
    primary_land_use = NA_character_,
    allows_residential = NA,
    allows_commercial = NA,
    parking_mentioned = NA,
    notes = NA_character_,
    error_flag = FALSE
  )

tool_state$df = parcels_tbl

cat("   ✅ ", nrow(parcels_tbl), " parcels × ", ncol(parcels_tbl), " cols.\n\n", sep = "")

chunks_in = parcels_in |>
  dplyr::select("parcel_id", "wkt", "zone_code", "zoning_excerpt")
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = length(chunks)
chunk_csv_texts = purrr::map_chr(chunks, \(ch) readr::format_csv(ch))
cat("✂️  Split into ", n_chunks, " chunk(s) of up to ", ROWS_PER_BATCH, " rows.\n\n", sep = "")

parcel_tools = parcel_tool_definitions()

# 3. PARALLEL CHUNK API ###################################

cat("-----------------------------------------------------------------\n")
cat("🔄 Step 2 — Ollama /api/chat per chunk (furrr)\n")
cat("-----------------------------------------------------------------\n\n")

future::plan(future::multisession, workers = FIXER_CHUNK_WORKERS)

chunk_results = furrr::future_map(
  seq_len(n_chunks),
  function(i) {
    call_parcel_chunk_ollama(
      chunk_index = i,
      n_chunks = n_chunks,
      chunk_csv_text = chunk_csv_texts[[i]],
      fixer_root = FIXER_ROOT,
      ollama_host = OLLAMA_HOST,
      ollama_key = OLLAMA_API_KEY,
      ollama_model = OLLAMA_MODEL,
      system_prompt = SYSTEM_PARCELS,
      data_blurb = ZONING_DATA_BLURB,
      tools = parcel_tools,
      max_output_tokens = MAX_OUT
    )
  },
  .options = furrr::furrr_options(seed = TRUE)
)

future::plan(future::sequential)

# 4. APPLY TOOLS ###################################

cat("-----------------------------------------------------------------\n")
cat("🔧 Step 3 — Apply tool calls (chunk order)\n")
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
    dispatch_parcel_tool(name, args, api_round_counter)
    n_tools = n_tools + 1L
  }
}

parcels_out = tool_state$df |>
  dplyr::mutate(
    error_flag = dplyr::if_else(is.na(.data$primary_land_use) | .data$primary_land_use == "", TRUE, .data$error_flag)
  )

readr::write_csv(parcels_out, OUT_CSV)
cat("\n   ✅ Wrote ", OUT_CSV, "\n", sep = "")

# 5. SF + MAPS ###################################

cat("\n-----------------------------------------------------------------\n")
cat("🎨 Step 4 — Maps (ggplot2 + geom_sf polygons)\n")
cat("-----------------------------------------------------------------\n")

parcels_sf = parcels_out |>
  sf::st_as_sf(wkt = "wkt", crs = WGS84_CRS, remove = FALSE)

p_before = ggplot2::ggplot(parcels_sf) +
  ggplot2::geom_sf(ggplot2::aes(fill = .data$zone_code), color = "gray30", linewidth = 0.3) +
  ggplot2::coord_sf(crs = sf::st_crs(WGS84_CRS)) +
  ggplot2::theme_minimal() +
  ggplot2::labs(title = "Parcels by raw zone_code", fill = "zone_code")

path_pb = file.path(OUT_DIR, "map_parcels_before.png")
ggplot2::ggsave(path_pb, p_before, width = 7, height = 5, dpi = 120)
cat("   💾 ", path_pb, "\n", sep = "")

p_after = ggplot2::ggplot(parcels_sf) +
  ggplot2::geom_sf(ggplot2::aes(fill = .data$primary_land_use), color = "gray30", linewidth = 0.3) +
  ggplot2::coord_sf(crs = sf::st_crs(WGS84_CRS)) +
  ggplot2::theme_minimal() +
  ggplot2::labs(title = "Parcels by LLM primary_land_use", fill = "primary_land_use")

path_pa = file.path(OUT_DIR, "map_parcels_after.png")
ggplot2::ggsave(path_pa, p_after, width = 7, height = 5, dpi = 120)
cat("   💾 ", path_pa, "\n", sep = "")

# 6. SUMMARY ###################################

n_audit = if (file.exists(AUDIT_PATH)) sum(nzchar(readr::read_lines(AUDIT_PATH))) else 0L
n_err = sum(parcels_out$error_flag, na.rm = TRUE)

cat("\n=================================================================\n")
cat("📊 Summary (fixer_parcels.R)\n")
cat("=================================================================\n")
cat("📦 Chunks: ", n_chunks, " | tool calls: ", n_tools, " | audit lines: ", n_audit, "\n", sep = "")
cat("⚠️  Rows error_flag TRUE: ", n_err, " / ", nrow(parcels_out), "\n", sep = "")
cat("=================================================================\n")
