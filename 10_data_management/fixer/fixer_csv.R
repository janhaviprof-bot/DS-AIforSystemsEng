#' @name fixer_csv.R
#' @title Batched CSV repair — one Ollama round per N rows + furrr chunk parallelism
#' @author Prof. Tim Fraser
#' @description
#' Topic: AI-assisted data management
#'
#' Splits the working table into chunks of **ROWS_PER_BATCH** rows. Each chunk gets **one**
#' `/api/chat` with a shared **DATA_QUALITY_BLURB** (no per-row notes column). The model returns
#' many **set_cell** tool calls in a single turn; **furrr** runs chunk requests in parallel
#' (**FIXER_CHUNK_WORKERS**). Patches apply **sequentially on the main process** (safe shared state).
#' Raw data: **data/messy_inventory_raw.csv**; outputs: **output/messy_inventory_working.csv**,
#' **output/fix_audit.jsonl**.

# 0. SETUP ###################################

cat("\n")
cat("=================================================================\n")
cat("📋 fixer_csv.R — batched tool calls + future/furrr (Ollama Cloud)\n")
cat("=================================================================\n\n")

## 0.1 Load Packages #################################

cat("📦 Loading R packages (dplyr, readr, httr2, jsonlite, stringr, purrr, future, furrr) ...\n")
library(dplyr) # group_split, mutate, rowwise table ops
library(readr) # read/write_csv, format_csv
library(httr2) # HTTP (errors on main process)
library(jsonlite) # audit JSON lines
library(stringr) # str_extract, str_trim, env digit checks
library(purrr) # map_chr, walk
library(future) # parallel execution plan
library(furrr) # future_map over chunks
cat("   ✅ Packages ready.\n\n")

## 0.2 Resolve paths and environment #################################

cat("📁 Resolving fixer folder and paths ...\n")
REPO = stringr::str_extract(getwd(), ".*dsai")
FIXER_ROOT = paste0(REPO, "/10_data_management/fixer")
setwd(FIXER_ROOT)
cat("   📍 FIXER_ROOT: ", FIXER_ROOT, "\n", sep = "")

RAW_PATH = file.path(FIXER_ROOT, "data", "messy_inventory_raw.csv")
WORK_PATH = file.path(FIXER_ROOT, "output", "messy_inventory_working.csv")
LOG_PATH = file.path(FIXER_ROOT, "output", "fix_audit.jsonl")
cat("   📄 Raw data:     ", RAW_PATH, "\n", sep = "")
cat("   💾 Working copy: ", WORK_PATH, "\n", sep = "")
cat("   📝 Audit log:    ", LOG_PATH, "\n\n", sep = "")

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
cat("   model  = ", OLLAMA_MODEL, "\n", sep = "")
ak_show = if (nzchar(OLLAMA_API_KEY)) {
  paste0(substr(OLLAMA_API_KEY, 1L, 4L), "...", substr(OLLAMA_API_KEY, nchar(OLLAMA_API_KEY), nchar(OLLAMA_API_KEY)))
} else {
  "(empty)"
}
cat("   API key (masked): ", ak_show, "\n\n", sep = "")

# Chunk size: rows per single chat request
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
# Parallel Ollama requests (not parallel set_cell — main process applies patches)
FIXER_CHUNK_WORKERS = read_env_digits("FIXER_CHUNK_WORKERS", 1L)
cat("📊 ROWS_PER_BATCH = ", ROWS_PER_BATCH, " (env ROWS_PER_BATCH)\n", sep = "")
cat("📊 FIXER_CHUNK_WORKERS = ", FIXER_CHUNK_WORKERS, " (env FIXER_CHUNK_WORKERS)\n\n", sep = "")

cat("🔌 Sourcing fixer/functions.R ...\n")
source(file.path(FIXER_ROOT, "functions.R"), local = FALSE)
cat("   ✅ Helpers loaded.\n\n")

MAX_OUT = {
  et = stringr::str_trim(Sys.getenv("FIXER_MAX_OUTPUT_TOKENS", unset = ""))
  if (nzchar(et) && grepl("^[0-9]+$", et)) as.integer(et) else NULL
}

## 0.3 Data dictionary + cleaning rules (no per-row notes column) #################################

# Edit for class demos. `set_cell` only accepts string new_value: use **empty string** for missing (same as NA in export).

DATA_QUALITY_BLURB = paste0(
  "## What this table is\n",
  "Each row is one **SKU** line in a **store inventory**: how many units are on hand, when it was last restocked, and a high-level **category** (electronics vs food). ",
  "Columns are **not interchangeable**—do not move dates into qty, or category words into qty, or invent numbers.\n\n",
  "## Column meanings (edit only the cell that matches the column’s meaning)\n",
  "- **row_id**: stable row key. **Never** call set_cell on row_id.\n",
  "- **sku**: product code. **Do not** edit unless an obvious duplicate typo is requested (default: leave sku unchanged).\n",
  "- **qty_on_hand**: **stock count** as **digits only**—**positive** integers or **empty**; **`0` counts as missing** → empty. ",
  "This is **not** a date column, **not** a category column, **not** a free-text field.\n",
  "- **last_restock**: calendar date of last restock, **YYYY-MM-DD** only, OR **empty** if invalid/unknown.\n",
  "- **category**: **exactly** one of **`Electronics`** or **`Food`** (those spellings, title case).\n\n",
  "## Missing values (critical)\n",
  "The tool only accepts text. For “missing / NA / unknown / invalid after cleaning”, set **new_value to an empty string** `\"\"` (nothing between the quotes). ",
  "**Forbidden** as new_value: the literal text **NaN**, **nan**, **NULL**, **null**, **N/A**, or the two letters **NA**—those are wrong; use **empty string** instead. ",
  "Examples: messy **N/A**, **n/a**, **unknown** in **qty_on_hand** → **empty string**, not \"NaN\". Sentinel **-99999** in qty → **empty string**. For this inventory table, **`0` in qty_on_hand is a placeholder / unknown count**—set **empty string**, do **not** leave `\"0\"`.\n\n",
  "## qty_on_hand rules\n",
  "- Allowed: **positive** integer as digits (`1`,`12`,…) OR **empty**. (**`0` → empty** for this exercise.)\n",
  "- Strip unit words: `\"3 units\"`→`\"3\"`, `\"12 pcs\"`→`\"12\"`.\n",
  "- **Spaced digits = concatenate only, in order**—remove spaces between digit characters and **nothing else**: `\"1 1\"`→`\"11\"`; `\"1 2 3\"`→`\"123\"`; `\"2 0\"`→`\"20\"`; `\"1 5 0\"`→`\"150\"`. ",
  "The new digits must be **exactly** the digits you see, left to right. **Forbidden**: inventing a different number (e.g. `\"2 0\"` **must not** become `\"150\"` or any value not equal to that concatenation).\n",
  "- Collapsed qty is **one integer**, **not** a date, **not** last_restock.\n",
  "- English number words → digits: **two**→`\"2\"`, **three**→`\"3\"`—use the **correct** digit, do not guess.\n",
  "- If the cell already contains something that is **clearly a date** (e.g. `2025-01-15`) or **clearly belongs in last_restock**, **clear qty** with **empty string**—do **not** invent a substitute number like `123`.\n",
  "- If qty is nonsense for a stock count, use **empty string** rather than fabricating a plausible digit.\n\n",
  "## last_restock rules\n",
  "- Valid: **YYYY-MM-DD** only. **If the cell already looks like a real ISO date** (e.g. `2025-01-01`, `2024-12-15`) with a **plausible** month/day, **leave it as-is**—do **not** blank good dates. Only set **empty** when the value is **not** ISO-shaped, is **impossible** (e.g. month 13), or is junk text (`not-a-date`, `32/01/2024`, slash formats you cannot normalize safely, etc.).\n",
  "- **Never** write a restock date into **qty_on_hand**, and **never** put a quantity into **last_restock**.\n\n",
  "## category rules (Electronics vs Food only)\n",
  "- **Food**: anything about **food retail, dining, grocery, cafeteria, café, food_service, kitchen, meal** → **`Food`**. ",
  "Examples: `food_service`, `grocery`, `cafeteria`, `food_retail`, `FOOD` → **`Food`**. **Cafeteria is Food, not Electronics.**\n",
  "- **Electronics**: consumer/tech retail variants → **`Electronics`**. Examples: `electronics`, `ELEC`, `elec`, `ELECTRONICS`, trailing space on `Electronics ` → **`Electronics`**.\n",
  "- Ambiguous **Retail** alone: if the row is clearly food-related, **`Food`**; if clearly tech, **`Electronics`**; if still unclear, prefer **`Food`** only when name/sku hints at food, else **`Electronics`**.\n",
  "- Trim leading/trailing spaces on category.\n\n",
  "## Anti-hallucination\n",
  "- Do **not** copy a value from **column A** into **column B** unless B’s definition says it belongs there.\n",
  "- Do **not** output **JSON null** or **NaN** as text in cells—use **empty string** for missing.\n",
  "- Prefer **fewer, correct** set_cell calls over creative guesses.\n",
  "- **No-op edits**: do **not** call **set_cell** if **new_value** would equal the current cell (wastes audit lines)."
)

## 0.4 Tool state + batch tool definitions (set_cell + write_checkpoint only) #################################

cat("🧰 Initializing tool_state + tool definitions ...\n")
tool_state = new.env(parent = emptyenv())
tool_state$df = NULL
tool_state$audit_path = LOG_PATH
tool_state$api_round = 0L

#' @name append_audit
#' @title Append one JSON line to the audit log
append_audit = function(obj) {
  line = paste0(jsonlite::toJSON(obj, auto_unbox = TRUE), "\n")
  cat(line, file = tool_state$audit_path, append = TRUE)
}

#' @name run_set_cell
#' @title Set one cell in the working inventory table
run_set_cell = function(args, api_round) {
  args = args %||% list()
  rid = args$row_id
  col = as.character(args$column_name %||% "")
  nv = as.character(args$new_value %||% "")
  ev = args$expected_old_value
  if (is.null(rid)) {
    return("Error: row_id required.")
  }
  rid = as.integer(rid)
  if (is.na(rid)) {
    return("Error: row_id must be integer-like.")
  }
  if (!nzchar(col)) {
    return("Error: column_name required.")
  }
  if (col == "row_id") {
    return("Error: row_id column cannot be edited.")
  }
  df = tool_state$df
  if (!col %in% names(df)) {
    return(paste0("Error: unknown column ", col))
  }
  i = which(as.integer(df$row_id) == rid)
  if (!length(i)) {
    return(paste0("Error: no row with row_id=", rid))
  }
  i = i[[1L]]
  old = as.character(df[[col]][[i]])
  if (length(old) != 1L || is.na(old)) {
    old = ""
  }
  if (!is.null(ev)) {
    ev = as.character(ev)
    if (length(ev) != 1L || is.na(ev)) {
      ev = ""
    }
    if (old != ev) {
      return(paste0(
        "Skipped: expected_old_value mismatch for row_id=", rid, " col=", col,
        " (current=", encodeString(old, quote = "\""), " expected=", encodeString(ev, quote = "\""), ")"
      ))
    }
  }
  tool_state$df[[col]][[i]] = nv
  append_audit(list(
    ts = format(Sys.time(), tz = "UTC", usetz = TRUE),
    api_round = as.integer(api_round),
    tool = "set_cell",
    row_id = rid,
    column = col,
    old_value = old,
    new_value = nv
  ))
  paste0("OK: row_id=", rid, " ", col, " updated.")
}

#' @name run_write_checkpoint
#' @title Write working table to output/messy_inventory_working.csv
run_write_checkpoint = function() {
  readr::write_csv(tool_state$df, WORK_PATH, na = "")
  paste0("Checkpoint written: ", nrow(tool_state$df), " rows to ", WORK_PATH, "\n")
}

#' @name fixer_tool_definitions
#' @title Tool schema: set_cell + write_checkpoint (batch-oriented)
fixer_tool_definitions = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "set_cell",
        description = paste0(
          "Set one cell in the working inventory row (identified by row_id). ",
          "Pass expected_old_value when possible. Do not edit row_id or sku unless instructed. ",
          "For missing/invalid cleaned values use an empty string for new_value—never the literals NaN, NA, null, or N/A as text."
        ),
        parameters = list(
          type = "object",
          properties = list(
            row_id = list(type = "integer", description = "Stable row_id from the CSV."),
            column_name = list(type = "string", description = "One of: qty_on_hand, last_restock, category (not row_id)."),
            new_value = list(
              type = "string",
              description = paste0(
                "New cell text. qty_on_hand: positive digits or empty; 0→empty; spaced digits concatenate in order only (2 0→20, never 150). ",
                "last_restock: keep valid YYYY-MM-DD; empty only if invalid. category: Electronics or Food. ",
                "Empty string means missing—do not write NaN."
              )
            ),
            expected_old_value = list(
              type = "string",
              description = "If set, update only when current value equals this string."
            )
          ),
          required = list("row_id", "column_name", "new_value")
        )
      )
    ),
    list(
      type = "function",
      `function` = list(
        name = "write_checkpoint",
        description = paste0("Write the current working table to disk (", basename(WORK_PATH), ")."),
        parameters = list(
          type = "object",
          properties = structure(list(), names = character(0)),
          required = list()
        )
      )
    )
  )
}

#' @name dispatch_fixer_tool
#' @title Dispatch set_cell or write_checkpoint
dispatch_fixer_tool = function(name, args, api_round) {
  if (name == "set_cell") {
    rid = args$row_id %||% "?"
    col = args$column_name %||% "?"
    cat("      ✏️  set_cell row_id=", rid, " col=", col, "\n", sep = "")
    return(run_set_cell(args, api_round))
  }
  if (name == "write_checkpoint") {
    cat("      💾 write_checkpoint\n", sep = "")
    return(run_write_checkpoint())
  }
  cat("      ❓ unknown tool: ", name, "\n", sep = "")
  paste0("Unknown tool: ", name)
}

#' @name call_chunk_ollama
#' @title One Ollama chat for a chunk (runs inside future workers)
#' @description Sources functions.R in the worker and returns parsed tool_calls (no mutation).
call_chunk_ollama = function(
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
    "Data dictionary + cleaning rules:\n\n",
    data_blurb,
    "\n\n---\nChunk ",
    chunk_index,
    " of ",
    n_chunks,
    " (inventory CSV; columns must keep their semantics):\n\n",
    chunk_csv_text,
    "\n\n---\n",
    "Emit **set_cell** only where the rules require a change (skip if new_value would equal current). ",
    "Use **expected_old_value** when possible (match the cell text exactly as shown in the CSV). ",
    "Remember: **missing** = **new_value \"\"** (empty). Never **NaN** / **NA** / **null** as text. ",
    "**qty_on_hand**: **`0` → `\"\"`**; spaced digits = **concatenate in order** (`2 0`→`20`), **never** a made-up number like **150**. Must never hold a date; if you see a date there, clear qty to **\"\"** (do not guess **123**). ",
    "**\"1 2 3\"** in qty → **\"123\"** (concatenation only), not a date string. ",
    "**last_restock**: **do not blank** plausible **YYYY-MM-DD** dates (e.g. **2025-01-01**); blank only invalid/junk. ",
    "**cafeteria** / food-service labels → category **Food**. ",
    "You may call **write_checkpoint** once after edits. ",
    "Reply with tool calls only (minimal prose)."
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

cat("   ✅ Tool helpers ready.\n\n")

# 1. PREPARE FILES AND DATA ###################################

cat("-----------------------------------------------------------------\n")
cat("📂 Step 1 — Prepare files and load working copy\n")
cat("-----------------------------------------------------------------\n")

cat("📁 Ensuring output/ exists ...\n")
invisible(dir.create(file.path(FIXER_ROOT, "output"), showWarnings = FALSE, recursive = TRUE))
cat("   ✅ output/ OK.\n")

cat("📥 Copying raw CSV ➡️ working copy ...\n")
if (!file.copy(RAW_PATH, WORK_PATH, overwrite = TRUE)) {
  stop("Could not copy raw CSV to output: ", RAW_PATH, " -> ", WORK_PATH)
}
cat("   ✅ Copied.\n")

cat("📊 Reading working CSV (all columns as character) ...\n")
tool_state$df = WORK_PATH |>
  readr::read_csv(col_types = readr::cols(.default = readr::col_character()))
cat("   ✅ Loaded ", nrow(tool_state$df), " rows × ", ncol(tool_state$df), " cols.\n", sep = "")
cat("🔍 Preview:\n")
tool_state$df |>
  dplyr::slice_head(n = 3L) |>
  print()

cat("🗑️  Resetting audit log ...\n")
if (file.exists(LOG_PATH)) {
  invisible(file.remove(LOG_PATH))
}
cat("   ✅ Audit log fresh.\n\n")

chunks = split_df_into_row_chunks(tool_state$df, ROWS_PER_BATCH)
n_chunks = length(chunks)
chunk_csv_texts = purrr::map_chr(chunks, \(ch) readr::format_csv(ch))

cat("✂️  Split into ", n_chunks, " chunk(s) of up to ", ROWS_PER_BATCH, " rows.\n\n", sep = "")

# 2. BATCH PROMPTS + TOOLS ###################################

SYSTEM_BATCH = paste0(
  "You are a **batch** CSV cleaning assistant for a **retail inventory** table (SKU stock counts, restock dates, Electronics vs Food). ",
  "Each user message is one row chunk plus a data dictionary. Fix cells using **set_cell** only (plus optional **write_checkpoint**). ",
  "Prefer **expected_old_value** on each set_cell. ",
  "**qty_on_hand** = positive digits or **empty**; **`0` → empty** (placeholder). Spaced digits: **concatenate in order only** (`2 0`→`20`), **never** invent unrelated numbers (`2 0`≠`150`). ",
  "**last_restock** = keep **valid YYYY-MM-DD** unchanged; blank **only** invalid/junk dates. **category** = Electronics or Food only. ",
  "Never put dates in qty_on_hand or invent numbers when qty is wrong—use **empty string** for missing. ",
  "Never write the text **NaN**, **NA**, or **null** as a cell value—use **empty string** for missing. ",
  "**Cafeteria / grocery / food_service** → category **Food**, not Electronics. ",
  "\"1 2 3\" in qty → **\"123\"** (concatenation), never a date. ",
  "Skip set_cell when new_value would equal the current value. Do not invent row_ids."
)

tools = fixer_tool_definitions()

# 3. PARALLEL CHUNK API CALLS ###################################

cat("-----------------------------------------------------------------\n")
cat("🔄 Step 2 — Ollama /api/chat per chunk (furrr, workers = ", FIXER_CHUNK_WORKERS, ")\n", sep = "")
cat("-----------------------------------------------------------------\n\n")

future::plan(future::multisession, workers = FIXER_CHUNK_WORKERS)

chunk_results = furrr::future_map(
  seq_len(n_chunks),
  function(i) {
    call_chunk_ollama(
      chunk_index = i,
      n_chunks = n_chunks,
      chunk_csv_text = chunk_csv_texts[[i]],
      fixer_root = FIXER_ROOT,
      ollama_host = OLLAMA_HOST,
      ollama_key = OLLAMA_API_KEY,
      ollama_model = OLLAMA_MODEL,
      system_prompt = SYSTEM_BATCH,
      data_blurb = DATA_QUALITY_BLURB,
      tools = tools,
      max_output_tokens = MAX_OUT
    )
  },
  .options = furrr::furrr_options(seed = TRUE)
)

future::plan(future::sequential)

# Report chunk-level errors (HTTP etc.)
purrr::walk(chunk_results, function(cr) {
  if (!is.null(cr$error)) {
    cat("   ❌ Chunk ", cr$chunk_index, " API error: ", cr$error, "\n", sep = "")
  }
})

# 4. APPLY TOOL CALLS ON MAIN PROCESS (ORDERED) ###################################

cat("\n-----------------------------------------------------------------\n")
cat("🔧 Step 3 — Execute tool calls on main process (chunk order)\n")
cat("-----------------------------------------------------------------\n\n")

api_round_counter = 0L
n_tools_executed = 0L

for (cr in chunk_results) {
  ci = cr$chunk_index
  tcalls = cr$tool_calls %||% list()
  if (!length(tcalls)) {
    cat("   ⚠️  Chunk ", ci, ": no tool calls", if (nzchar(cr$content %||% "")) paste0(" (assistant text: ", substr(cr$content, 1L, 80L), "...") else "", "\n", sep = "")
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
    dispatch_fixer_tool(name, args, api_round_counter)
    n_tools_executed = n_tools_executed + 1L
  }
}

# 5. WRITE FINAL TABLE ###################################

cat("\n-----------------------------------------------------------------\n")
cat("💾 Step 4 — Writing final working table\n")
cat("-----------------------------------------------------------------\n")
readr::write_csv(tool_state$df, WORK_PATH, na = "")
cat("   ✅ Saved ", nrow(tool_state$df), " rows ➡️ ", WORK_PATH, "\n\n", sep = "")

# 6. SUMMARY ###################################

n_audit = if (file.exists(LOG_PATH)) {
  sum(nzchar(readr::read_lines(LOG_PATH)))
} else {
  0L
}

cat("=================================================================\n")
cat("📊 Summary\n")
cat("=================================================================\n")
cat("📦 Chunks (API calls):     ", n_chunks, "\n", sep = "")
cat("🔧 Tool calls executed:   ", n_tools_executed, "\n", sep = "")
cat("✏️  Audit lines (set_cell): ", n_audit, "\n", sep = "")
cat("👷 Chunk workers used:    ", FIXER_CHUNK_WORKERS, "\n", sep = "")
cat("💾 Working file:          ", WORK_PATH, "\n", sep = "")
cat("📝 Audit log:             ", LOG_PATH, "\n", sep = "")
cat("=================================================================\n")
