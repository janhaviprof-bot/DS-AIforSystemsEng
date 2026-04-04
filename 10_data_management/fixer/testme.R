#' @name testme.R
#' @title Smoke test Ollama Cloud chat from the fixer folder (no tools)
#' @author Prof. Tim Fraser
#' @description
#' One POST to **`/api/chat`** with a tiny user message — verifies **`OLLAMA_API_KEY`**,
#' **`OLLAMA_HOST`**, and **`OLLAMA_MODEL`** without tool calling or **`num_predict`**
#' (helps isolate HTTP 400s from the full **`fixer_csv.R`** loop).

# 0. SETUP ###################################

resolve_fixer_root = function() {
  r = Sys.getenv("FIXER_ROOT", unset = "")
  if (nzchar(r) && dir.exists(r)) {
    return(normalizePath(r, winslash = "/", mustWork = TRUE))
  }
  wd = normalizePath(getwd(), winslash = "/", mustWork = TRUE)
  if (file.exists(file.path(wd, "functions.R"))) {
    return(wd)
  }
  cand = file.path(wd, "10_data_management", "fixer")
  if (file.exists(file.path(cand, "functions.R"))) {
    return(normalizePath(cand, winslash = "/", mustWork = TRUE))
  }
  stop("Run from fixer/, dsai repo root, or set FIXER_ROOT.")
}

FIXER_ROOT = resolve_fixer_root()
env_path = file.path(FIXER_ROOT, ".env")
if (file.exists(env_path)) {
  readRenviron(env_path)
}

OLLAMA_HOST = trimws(Sys.getenv("OLLAMA_HOST", unset = "https://ollama.com"))
OLLAMA_API_KEY = trimws(Sys.getenv("OLLAMA_API_KEY", unset = ""))
OLLAMA_MODEL = trimws(Sys.getenv("OLLAMA_MODEL", unset = ""))
if (!nzchar(OLLAMA_MODEL)) {
  OLLAMA_MODEL = "gpt-oss:120b"
}

if (!nzchar(OLLAMA_API_KEY)) {
  stop("Set OLLAMA_API_KEY in fixer/.env (copy from .env.example).")
}

source(file.path(FIXER_ROOT, "functions.R"), local = FALSE)

# 1. MINIMAL CHAT (test query) ###################################

# Deliberately tiny: model should answer in a few tokens; no tools, no options.
messages = list(
  list(
    role = "user",
    content = "Reply with exactly one word: pong"
  )
)

cat("Test query: POST ", OLLAMA_HOST, "/api/chat\n", sep = "")
cat("Model: ", OLLAMA_MODEL, "\n\n", sep = "")

out = tryCatch(
  ollama_chat_once(
    OLLAMA_HOST,
    OLLAMA_API_KEY,
    OLLAMA_MODEL,
    messages,
    tools = NULL,
    format = NULL,
    max_output_tokens = NULL
  ),
  error = function(e) {
    lr = tryCatch(httr2::last_response(), error = function(e2) NULL)
    if (!is.null(lr)) {
      cat("HTTP status:", httr2::resp_status(lr), "\n")
      b = tryCatch(httr2::resp_body_string(lr), error = function(e3) "(no body)")
      cat("Response body:\n", b, "\n", sep = "")
    }
    stop(e)
  }
)

cat("Assistant content:\n", out$content, "\n\n", sep = "")
cat("Smoke test OK.\n")
