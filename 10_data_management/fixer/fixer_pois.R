#' @name fixer_pois.R
#' @title Batched POI name normalization — one Ollama round per N rows + furrr (Ollama tools)
#' @author Prof. Tim Fraser
#' @description
#' Topic: AI-assisted data management + GIS
#'
#' Points of interest use **x** / **y** (WGS84). Each chunk of **ROWS_PER_BATCH** rows gets one
#' `/api/chat`; the model returns many **record_poi_category** tool calls.
#' Raw: **data/pois_messy_raw.csv**; outputs: **output/pois_enriched.csv**,
#' **output/pois_enrich_audit.jsonl**, map PNGs.

# 0. SETUP ###################################

cat("\n")
cat("=================================================================\n")
cat("📍 fixer_pois.R — batched POI category tools + points (Ollama Cloud)\n")
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

POIS_PATH = file.path(FIXER_ROOT, "data", "pois_messy_raw.csv")
OUT_CSV = file.path(FIXER_ROOT, "output", "pois_enriched.csv")
AUDIT_PATH = file.path(FIXER_ROOT, "output", "pois_enrich_audit.jsonl")
OUT_DIR = file.path(FIXER_ROOT, "output")
cat("   📄 POIs:   ", POIS_PATH, "\n", sep = "")
cat("   💾 Output: ", OUT_CSV, "\n\n", sep = "")

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

POI_DATA_BLURB = paste0(
  "## POI table\n",
  "Each row is one **point** (columns **x** = longitude, **y** = latitude). **poi_id** is the stable key. ",
  "**name_messy** is a noisy facility label to classify.\n\n",
  "## Output fields (one tool call per row)\n",
  "- **normalized_category**: exactly one of ",
  "\"healthcare\", \"food_retail\", \"retail\", \"financial\", \"transport\", ",
  "\"recreation\", \"parking\", \"childcare\", \"agriculture\", \"vacant\", ",
  "\"public_government\", \"other\".\n",
  "- **confidence**: integer 1 (low), 2 (medium), or 3 (high).\n",
  "- **display_name_clean**: short human-readable name.\n"
)

SYSTEM_POIS = paste0(
  "You classify messy facility names into a **closed vocabulary** for a **batch** of POI rows. ",
  "Reply using **record_poi_category** tool calls only (one per poi_id in the chunk). ",
  "confidence is 1=low 2=medium 3=high. Do not invent poi_id values."
)

# 1. TOOL STATE + DEFINITIONS ###################################

tool_state = new.env(parent = emptyenv())
tool_state$df = NULL
tool_state$audit_path = AUDIT_PATH
tool_state$api_round = 0L

append_audit_poi = function(obj) {
  line = paste0(jsonlite::toJSON(obj, auto_unbox = TRUE), "\n")
  cat(line, file = tool_state$audit_path, append = TRUE)
}

run_record_poi_category = function(args, api_round) {
  args = args %||% list()
  pid = args$poi_id
  if (is.null(pid) || (is.character(pid) && !nzchar(pid))) {
    return("Error: poi_id required.")
  }
  pid = as.integer(pid)
  if (is.na(pid)) {
    return("Error: poi_id must be integer-like.")
  }
  df = tool_state$df
  j = which(as.integer(df$poi_id) == pid)
  if (!length(j)) {
    return(paste0("Error: unknown poi_id=", pid))
  }
  j = j[[1L]]
  tool_state$df$normalized_category[[j]] = as.character(args$normalized_category %||% NA_character_)
  tool_state$df$confidence[[j]] = as.integer(args$confidence %||% NA_integer_)
  tool_state$df$display_name_clean[[j]] = as.character(args$display_name_clean %||% NA_character_)
  append_audit_poi(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "record_poi_category",
    poi_id = pid
  ))
  paste0("OK: poi_id=", pid, " updated.")
}

poi_tool_definitions = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "record_poi_category",
        description = paste0(
          "Store normalized category and display name for one POI. poi_id must match the chunk CSV."
        ),
        parameters = list(
          type = "object",
          properties = list(
            poi_id = list(type = "integer", description = "poi_id from the CSV row."),
            normalized_category = list(
              type = "string",
              description = paste0(
                "One of: healthcare, food_retail, retail, financial, transport, recreation, ",
                "parking, childcare, agriculture, vacant, public_government, other."
              )
            ),
            confidence = list(type = "integer", description = "1=low, 2=medium, 3=high."),
            display_name_clean = list(type = "string", description = "Short cleaned facility name.")
          ),
          required = list("poi_id", "normalized_category", "confidence", "display_name_clean")
        )
      )
    )
  )
}

dispatch_poi_tool = function(name, args, api_round) {
  if (name == "record_poi_category") {
    cat("      ✏️  record_poi_category poi_id=", args$poi_id %||% "?", "\n", sep = "")
    return(run_record_poi_category(args, api_round))
  }
  cat("      ❓ unknown tool: ", name, "\n", sep = "")
  paste0("Unknown tool: ", name)
}

call_poi_chunk_ollama = function(
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
    "Task: for each POI in the chunk, call **record_poi_category** once (use **poi_id** from the CSV).\n\n",
    data_blurb,
    "\n\n---\nChunk ",
    chunk_index,
    " of ",
    n_chunks,
    " (EPSG:4326 coordinates).\n\n",
    chunk_csv_text,
    "\n\n---\nEmit one **record_poi_category** per row. Reply with tool calls only (minimal prose)."
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
cat("📂 Step 1 — Load POIs (points)\n")
cat("-----------------------------------------------------------------\n")

invisible(dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE))
if (file.exists(AUDIT_PATH)) {
  invisible(file.remove(AUDIT_PATH))
}

pois_in = readr::read_csv(POIS_PATH, show_col_types = FALSE)
stopifnot("poi_id" %in% names(pois_in), "x" %in% names(pois_in), "y" %in% names(pois_in))

pois_tbl = pois_in |>
  dplyr::mutate(
    normalized_category = NA_character_,
    confidence = NA_integer_,
    display_name_clean = NA_character_,
    error_flag = FALSE
  )

tool_state$df = pois_tbl

cat("   ✅ ", nrow(pois_tbl), " POIs × ", ncol(pois_tbl), " cols.\n\n", sep = "")

chunks_in = pois_in |>
  dplyr::select("poi_id", "x", "y", "name_messy")
chunks = split_df_into_row_chunks(chunks_in, ROWS_PER_BATCH)
n_chunks = length(chunks)
chunk_csv_texts = purrr::map_chr(chunks, \(ch) readr::format_csv(ch))
cat("✂️  Split into ", n_chunks, " chunk(s) of up to ", ROWS_PER_BATCH, " rows.\n\n", sep = "")

poi_tools = poi_tool_definitions()

# 3. PARALLEL CHUNK API ###################################

cat("-----------------------------------------------------------------\n")
cat("🔄 Step 2 — Ollama /api/chat per chunk (furrr)\n")
cat("-----------------------------------------------------------------\n\n")

future::plan(future::multisession, workers = FIXER_CHUNK_WORKERS)

chunk_results = furrr::future_map(
  seq_len(n_chunks),
  function(i) {
    call_poi_chunk_ollama(
      chunk_index = i,
      n_chunks = n_chunks,
      chunk_csv_text = chunk_csv_texts[[i]],
      fixer_root = FIXER_ROOT,
      ollama_host = OLLAMA_HOST,
      ollama_key = OLLAMA_API_KEY,
      ollama_model = OLLAMA_MODEL,
      system_prompt = SYSTEM_POIS,
      data_blurb = POI_DATA_BLURB,
      tools = poi_tools,
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
    pids = as.integer(chunks[[ci]]$poi_id)
    for (pid in pids) {
      jj = which(as.integer(tool_state$df$poi_id) == pid)
      if (length(jj)) {
        tool_state$df$error_flag[[jj[[1L]]]] = TRUE
      }
    }
    next
  }
  tcalls = cr$tool_calls %||% list()
  if (!length(tcalls)) {
    cat("   ⚠️  Chunk ", ci, ": no tool calls\n", sep = "")
    pids = as.integer(chunks[[ci]]$poi_id)
    for (pid in pids) {
      jj = which(as.integer(tool_state$df$poi_id) == pid)
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
    dispatch_poi_tool(name, args, api_round_counter)
    n_tools = n_tools + 1L
  }
}

pois_out = tool_state$df |>
  dplyr::mutate(
    plot_label = dplyr::if_else(
      is.na(.data$normalized_category) | .data$normalized_category == "",
      "unknown",
      .data$normalized_category
    ),
    error_flag = dplyr::if_else(
      is.na(.data$normalized_category) | .data$normalized_category == "",
      TRUE,
      .data$error_flag
    )
  )

readr::write_csv(
  pois_out |> dplyr::select(-"plot_label"),
  OUT_CSV
)
cat("\n   ✅ Wrote ", OUT_CSV, "\n", sep = "")

# 5. SF + MAPS ###################################

cat("\n-----------------------------------------------------------------\n")
cat("🎨 Step 4 — Maps (ggplot2 + geom_sf points)\n")
cat("-----------------------------------------------------------------\n")

pois_sf = pois_out |>
  sf::st_as_sf(coords = c("x", "y"), crs = WGS84_CRS, remove = FALSE)

p_before = ggplot2::ggplot(pois_sf) +
  ggplot2::geom_sf(color = "#2c3e50", fill = "#3498db", size = 2.5, shape = 21) +
  ggplot2::coord_sf(crs = sf::st_crs(WGS84_CRS)) +
  ggplot2::theme_minimal() +
  ggplot2::labs(title = "POIs (uniform symbol before category)")

path_ob = file.path(OUT_DIR, "map_pois_before.png")
ggplot2::ggsave(path_ob, p_before, width = 7, height = 5, dpi = 120)
cat("   💾 ", path_ob, "\n", sep = "")

p_after = ggplot2::ggplot(pois_sf) +
  ggplot2::geom_sf(
    ggplot2::aes(color = .data$plot_label, fill = .data$plot_label),
    size = 2.5,
    shape = 21,
    alpha = 0.85
  ) +
  ggplot2::coord_sf(crs = sf::st_crs(WGS84_CRS)) +
  ggplot2::theme_minimal() +
  ggplot2::labs(title = "POIs by normalized_category", color = "category", fill = "category")

path_oa = file.path(OUT_DIR, "map_pois_after.png")
ggplot2::ggsave(path_oa, p_after, width = 7, height = 5, dpi = 120)
cat("   💾 ", path_oa, "\n", sep = "")

# 6. SUMMARY ###################################

n_audit = if (file.exists(AUDIT_PATH)) sum(nzchar(readr::read_lines(AUDIT_PATH))) else 0L
n_err = sum(pois_out$error_flag, na.rm = TRUE)

cat("\n=================================================================\n")
cat("📊 Summary (fixer_pois.R)\n")
cat("=================================================================\n")
cat("📦 Chunks: ", n_chunks, " | tool calls: ", n_tools, " | audit lines: ", n_audit, "\n", sep = "")
cat("⚠️  Rows error_flag TRUE: ", n_err, " / ", nrow(pois_out), "\n", sep = "")
cat("=================================================================\n")
