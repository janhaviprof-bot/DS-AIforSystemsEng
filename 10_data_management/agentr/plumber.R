# plumber.R
# Plumber API — disaster situational brief agent (parity with agentpy FastAPI)
# Tim Fraser
#
# Run locally (repository root = getwd(), same convention as mcp_plumber/runme.R):
#   Rscript 10_data_management/agentr/runme.R
# Or from R: plumber::plumb("10_data_management/agentr/plumber.R")$run(host="0.0.0.0", port=8000)

library(plumber)
library(jsonlite)
library(httr2)
library(reticulate)

# Resolve activity root: explicit AGENTR_ROOT, else cwd if already agentr/, else repo-relative path.
agentr_app_root = function() {
  e = Sys.getenv("AGENTR_ROOT", unset = "")
  if (nzchar(e)) {
    return(normalizePath(e, winslash = "/", mustWork = FALSE))
  }
  if (file.exists("plumber.R") && dir.exists("R") && dir.exists("skills")) {
    return(normalizePath(getwd(), winslash = "/", mustWork = FALSE))
  }
  cand = normalizePath("10_data_management/agentr", winslash = "/", mustWork = FALSE)
  if (dir.exists(cand) && file.exists(file.path(cand, "plumber.R"))) {
    return(cand)
  }
  normalizePath(getwd(), winslash = "/", mustWork = FALSE)
}
Sys.setenv(AGENTR_ROOT = agentr_app_root())

if (file.exists(file.path(Sys.getenv("AGENTR_ROOT"), ".env"))) {
  readRenviron(file.path(Sys.getenv("AGENTR_ROOT"), ".env"))
}

root = Sys.getenv("AGENTR_ROOT")
source(file.path(root, "R", "guardrails.R"), local = FALSE)
source(file.path(root, "R", "logging.R"), local = FALSE)
source(file.path(root, "R", "context.R"), local = FALSE)
source(file.path(root, "R", "tools_reticulate.R"), local = FALSE)
source(file.path(root, "R", "ollama_chat.R"), local = FALSE)
source(file.path(root, "R", "loop.R"), local = FALSE)

configure_agent_logging()

.agent_api = new.env(parent = emptyenv())
.agent_api$run_enabled = TRUE
.agent_sessions = new.env(parent = emptyenv())

new_session_id = function() {
  hex = c(as.character(0:9), letters[1:6])
  chunk = function(n) paste0(sample(hex, n, replace = TRUE), collapse = "")
  paste(chunk(8L), chunk(4L), chunk(4L), chunk(4L), chunk(12L), sep = "-")
}

parse_post_json = function(req) {
  raw = req$postBody
  if (is.null(raw) || (is.character(raw) && !nzchar(raw))) {
    br = req$bodyRaw
    if (!is.null(br) && length(br) > 0L) {
      raw = rawToChar(br)
    }
  }
  if (is.null(raw) || !nzchar(as.character(raw))) {
    return(list())
  }
  jsonlite::fromJSON(as.character(raw), simplifyVector = FALSE, simplifyDataFrame = FALSE)
}

scalar_chr = function(x, default = "") {
  if (is.null(x)) {
    return(default)
  }
  if (is.character(x) && length(x) >= 1L) {
    return(x[[1L]])
  }
  as.character(x)[[1L]]
}

#* Disaster situational brief agent (Plumber) — Cornell SYSEN 5381 Module 10
#* @apiTitle Disaster Situational Brief Agent (R)
#* @apiDescription Teaching API: bounded Ollama loop with read_skill and web_search (CrewAI SerperDevTool via reticulate). Same routes as agentpy FastAPI.
#* @apiVersion 0.1.0

#* Health check
#* @get /health
function() {
  list(
    ok = TRUE,
    run_enabled = .agent_api$run_enabled,
    model = trimws(Sys.getenv("OLLAMA_MODEL", unset = "nemotron-3-nano:30b-cloud")),
    max_autonomous_turns = MAX_AUTONOMOUS_TURNS,
    min_completion_turns = min_completion_turns()
  )
}

#* Start or stop accepting new agent work
#* @post /hooks/control
function(req, res) {
  b = parse_post_json(req)
  act = tolower(trimws(scalar_chr(b$action, "")))
  if (act == "start") {
    .agent_api$run_enabled = TRUE
    return(list(ok = TRUE, run_enabled = TRUE))
  }
  if (act == "stop") {
    .agent_api$run_enabled = FALSE
    return(list(ok = TRUE, run_enabled = FALSE))
  }
  res$status = 400
  list(ok = FALSE, detail = "action must be start or stop")
}

#* Run a situational brief (or resume a paused thread)
#* @post /hooks/agent
function(req, res) {
  b = parse_post_json(req)
  task = scalar_chr(b$task, "")
  session_id_in = b$session_id
  resume_tok_in = b$resume_token
  max_turns = b$max_turns

  turn_cap = clamp_turns(
    if (is.null(max_turns)) {
      NULL
    } else {
      suppressWarnings(as.integer(max_turns[[1L]]))
    }
  )

  if (!isTRUE(.agent_api$run_enabled)) {
    res$status = 503
    return(list(
      status = "error",
      reply = "",
      turns_used = 0L,
      turn_cap = turn_cap,
      min_completion_turns = min(min_completion_turns(), turn_cap),
      session_id = NULL,
      detail = "Agent is stopped; POST /hooks/control with start."
    ))
  }

  ollama_key = trimws(Sys.getenv("OLLAMA_API_KEY", unset = ""))
  if (!nzchar(ollama_key)) {
    res$status = 500
    sid_out = if (is.null(session_id_in)) {
      NULL
    } else {
      scalar_chr(session_id_in, "")
    }
    return(list(
      status = "error",
      reply = "",
      turns_used = 0L,
      turn_cap = turn_cap,
      min_completion_turns = min(min_completion_turns(), turn_cap),
      session_id = sid_out,
      detail = "OLLAMA_API_KEY is not set. Add it to .env for Ollama Cloud."
    ))
  }

  ollama_host = trimws(Sys.getenv("OLLAMA_HOST", unset = "https://ollama.com"))
  ollama_model = trimws(Sys.getenv("OLLAMA_MODEL", unset = "nemotron-3-nano:30b-cloud"))

  sid = if (is.null(session_id_in) || !nzchar(scalar_chr(session_id_in, ""))) {
    new_session_id()
  } else {
    scalar_chr(session_id_in, "")
  }

  state = if (exists(sid, envir = .agent_sessions, inherits = FALSE)) {
    get(sid, envir = .agent_sessions)
  } else {
    NULL
  }

  if (!is.null(state) && isTRUE(state$paused)) {
    rt = scalar_chr(resume_tok_in, "")
    if (!nzchar(rt) || !identical(rt, state$resume_token %||% "")) {
      res$status = 403
      return(list(detail = "Invalid or missing resume_token for paused session"))
    }
    result = run_research_loop(
      task,
      ollama_host = ollama_host,
      ollama_api_key = ollama_key,
      model = ollama_model,
      max_turns = if (is.null(max_turns)) {
        NULL
      } else {
        suppressWarnings(as.integer(max_turns[[1L]]))
      },
      existing_messages = state$messages,
      continue_thread = TRUE
    )
  } else {
    if (!is.null(resume_tok_in) && nzchar(scalar_chr(resume_tok_in, "")) && is.null(state)) {
      res$status = 404
      return(list(detail = "Unknown session_id for resume_token"))
    }
    result = run_research_loop(
      task,
      ollama_host = ollama_host,
      ollama_api_key = ollama_key,
      model = ollama_model,
      max_turns = if (is.null(max_turns)) {
        NULL
      } else {
        suppressWarnings(as.integer(max_turns[[1L]]))
      },
      existing_messages = NULL,
      continue_thread = FALSE
    )
  }

  payload = list(
    status = result$status,
    reply = result$reply %||% "",
    turns_used = result$turns_used %||% 0L,
    turn_cap = turn_cap,
    session_id = sid,
    prefetch_search_used = isTRUE(result$prefetch_search_used),
    forced_tool_round = isTRUE(result$forced_tool_round),
    min_completion_turns = result$min_completion_turns %||% 1L
  )
  if (!is.null(result$detail) && nzchar(as.character(result$detail))) {
    payload$detail = result$detail
  }

  if (identical(result$status, "paused_for_human")) {
    resume = result$resume_token
    assign(
      sid,
      list(
        messages = result$messages %||% list(),
        paused = TRUE,
        resume_token = resume
      ),
      envir = .agent_sessions
    )
    payload$resume_token = resume
  } else if (identical(result$status, "ok")) {
    if (exists(sid, envir = .agent_sessions, inherits = FALSE)) {
      rm(list = sid, envir = .agent_sessions)
    }
    payload$resume_token = NULL
  } else {
    if (exists(sid, envir = .agent_sessions, inherits = FALSE)) {
      rm(list = sid, envir = .agent_sessions)
    }
  }

  if (identical(result$status, "error")) {
    res$status = 500
  }
  payload
}

#* @plumber
function(pr) {
  pr %>%
    pr_set_serializer(serializer_unboxed_json())
}
