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
#* @apiDescription Teaching API for bounded disaster situational briefs with the same routes and behaviors as agentpy FastAPI.
#* @apiVersion 0.1.0

#* Health check
#* @tag health
#* @response 200 Health metadata (ok, run_enabled, model, turn caps).
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
#* @tag agent
#* @response 200 Updated run_enabled flag after start/stop action.
#* @response 400 Invalid control action; action must be start or stop.
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
#* @tag agent
#* @response 200 Brief result payload (`ok` or `paused_for_human`) with session metadata.
#* @response 403 Invalid or missing resume_token for paused session.
#* @response 404 Unknown session_id when resume_token is provided.
#* @response 500 Agent/server error (missing API key or model/tool failure).
#* @response 503 Agent currently stopped; call /hooks/control with action=start.
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

enhance_openapi_spec = function(spec) {
  max_autonomous_turns = as.integer(get("MAX_AUTONOMOUS_TURNS", envir = .GlobalEnv, inherits = TRUE))

  if (is.null(spec$info)) {
    spec$info = list()
  }
  spec$info$title = "Disaster Situational Brief Agent (R)"
  spec$info$version = "0.1.0"
  spec$info$description = paste(
    "Teaching API for a **disaster situational brief agent**: short, structured open-source summaries aimed at",
    "**coordination / resilience** audiences (e.g. morning-style snapshots of a named incident and follow-up questions).",
    "",
    "> Built for **Cornell SYSEN 5381** — [**Module 10 (Data Management)**](https://github.com/timothyfraser/dsai/tree/main/10_data_management).",
    "> <br>Author: Tim Fraser <tmf77@cornell.edu>",
    "> <br>GitHub: [@timothyfraser](https://github.com/timothyfraser)",
    "",
    "---",
    "",
    "### Runtime behavior",
    "",
    "- **Tools:** Ollama-native function calling; **web_search** uses CrewAI **SerperDevTool** (Serper API).",
    "- **Sessions:** omit `session_id` on the first request and the server generates a UUID.",
    "  Reuse that `session_id` only when resuming after `paused_for_human` together with the matching `resume_token`.",
    "  Successful `ok` runs clear server-side session state.",
    "",
    "### Intended deployment",
    "",
    "- Primary target is **Posit Connect** as a **Plumber** content item.",
    "- Run locally with `Rscript 10_data_management/agentr/runme.R`.",
    "- Environment variables such as `OLLAMA_API_KEY`, optional `SERPER_API_KEY`, and Connect settings are configured on host.",
    sep = "\n"
  )
  spec$info$contact = list(name = "Tim Fraser", email = "tmf77@cornell.edu")

  spec$tags = list(
    list(
      name = "health",
      description = "Liveness and runtime flags."
    ),
    list(
      name = "agent",
      description = "JSON POST endpoints for control and situational briefs (no shared-secret header)."
    )
  )

  if (is.null(spec$components)) {
    spec$components = list()
  }
  spec$components$schemas = list(
    ControlBody = list(
      type = "object",
      required = list("action"),
      properties = list(
        action = list(
          type = "string",
          enum = list("start", "stop"),
          description = paste(
            "**`start`** allow new `/hooks/agent` runs.",
            "**`stop`** reject new runs with **503** until restarted.",
            "Case-insensitive input is accepted.",
            sep = " "
          ),
          example = "start"
        )
      ),
      example = list(action = "start")
    ),
    AgentBody = list(
      type = "object",
      required = list("task"),
      properties = list(
        task = list(
          type = "string",
          minLength = 1L,
          description = paste(
            "Instruction for the brief or follow-up.",
            "On resume, this is appended as the next user message in the saved thread.",
            sep = " "
          ),
          example = "Morning brief: wildfire perimeter and evacuation zones near Linn County, Iowa."
        ),
        session_id = list(
          type = "string",
          nullable = TRUE,
          description = paste(
            "Omit on first request so server generates a UUID.",
            "Provide same value only when resuming a paused session.",
            sep = " "
          ),
          example = "8f1c2b3a-4d5e-6f70-89ab-c0def1234567"
        ),
        resume_token = list(
          type = "string",
          nullable = TRUE,
          description = paste(
            "Required only when resuming after `paused_for_human`.",
            "Must match token returned in prior paused response.",
            sep = " "
          ),
          example = "paste-the-resume_token-from-previous-response"
        ),
        max_turns = list(
          type = "integer",
          nullable = TRUE,
          minimum = 1L,
          maximum = max_autonomous_turns,
          description = paste(
            "Optional per-request limit on Ollama /api/chat rounds.",
            paste0("Must be between 1 and ", max_autonomous_turns, "."),
            sep = " "
          ),
          example = 6L
        )
      )
    ),
    HealthResponse = list(
      type = "object",
      required = list("ok", "run_enabled", "model", "max_autonomous_turns", "min_completion_turns"),
      properties = list(
        ok = list(type = "boolean", example = TRUE),
        run_enabled = list(type = "boolean", example = TRUE),
        model = list(type = "string", example = "nemotron-3-nano:30b-cloud"),
        max_autonomous_turns = list(type = "integer", example = max_autonomous_turns),
        min_completion_turns = list(type = "integer", example = 1L)
      )
    ),
    ControlResponse = list(
      type = "object",
      required = list("ok", "run_enabled"),
      properties = list(
        ok = list(type = "boolean", example = TRUE),
        run_enabled = list(type = "boolean", example = TRUE)
      )
    ),
    AgentResponse = list(
      type = "object",
      required = list(
        "status",
        "reply",
        "turns_used",
        "turn_cap",
        "session_id",
        "prefetch_search_used",
        "forced_tool_round",
        "min_completion_turns"
      ),
      properties = list(
        status = list(type = "string", enum = list("ok", "paused_for_human", "error"), example = "ok"),
        reply = list(type = "string"),
        turns_used = list(type = "integer", example = 4L),
        turn_cap = list(type = "integer", example = 6L),
        session_id = list(type = "string", nullable = TRUE, example = "8f1c2b3a-4d5e-6f70-89ab-c0def1234567"),
        prefetch_search_used = list(type = "boolean", example = TRUE),
        forced_tool_round = list(type = "boolean", example = FALSE),
        min_completion_turns = list(type = "integer", example = 1L),
        resume_token = list(type = "string", nullable = TRUE, example = NULL),
        detail = list(type = "string", nullable = TRUE, example = "Optional error detail.")
      )
    ),
    DetailOnlyError = list(
      type = "object",
      required = list("detail"),
      properties = list(
        detail = list(type = "string", example = "Invalid or missing resume_token for paused session")
      )
    )
  )

  spec$paths$`/health`$get$summary = "Health check"
  spec$paths$`/health`$get$description = "Returns `ok`, whether new agent runs are allowed, model name, and turn caps."
  spec$paths$`/health`$get$tags = list("health")
  spec$paths$`/health`$get$responses = list(
    `200` = list(
      description = "Health metadata and runtime flags.",
      content = list(
        `application/json` = list(
          schema = list(`$ref` = "#/components/schemas/HealthResponse")
        )
      )
    )
  )

  spec$paths$`/hooks/control`$post$summary = "Start or stop accepting new agent work"
  spec$paths$`/hooks/control`$post$description = paste(
    "**`start`** accepts new `POST /hooks/agent` work.",
    "**`stop`** rejects new runs with **503** until restarted.",
    sep = "\n\n"
  )
  spec$paths$`/hooks/control`$post$tags = list("agent")
  spec$paths$`/hooks/control`$post$requestBody = list(
    required = TRUE,
    content = list(
      `application/json` = list(
        schema = list(`$ref` = "#/components/schemas/ControlBody"),
        examples = list(
          start_accepting_work = list(
            summary = "Start processing new tasks",
            description = "After this call, `POST /hooks/agent` can run (subject to API key and other checks).",
            value = list(action = "start")
          ),
          stop_new_tasks = list(
            summary = "Stop processing new tasks",
            description = "Useful for maintenance windows or classroom demos.",
            value = list(action = "stop")
          )
        )
      )
    )
  )
  spec$paths$`/hooks/control`$post$responses = list(
    `200` = list(
      description = "Control state updated.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/ControlResponse")))
    ),
    `400` = list(
      description = "Invalid action value.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/DetailOnlyError")))
    )
  )

  spec$paths$`/hooks/agent`$post$summary = "Run a situational brief (or resume a paused thread)"
  spec$paths$`/hooks/agent`$post$description = paste(
    "Runs the bounded Ollama loop for one user `task`.",
    "",
    "Typical flow:",
    "1. Send `task` only and server assigns `session_id`.",
    "2. If `status` is `ok`, session state is cleared.",
    "3. If `status` is `paused_for_human`, send `session_id`, `resume_token`, and a follow-up `task`.",
    sep = "\n"
  )
  spec$paths$`/hooks/agent`$post$tags = list("agent")
  spec$paths$`/hooks/agent`$post$requestBody = list(
    required = TRUE,
    content = list(
      `application/json` = list(
        schema = list(`$ref` = "#/components/schemas/AgentBody"),
        examples = list(
          new_brief = list(
            summary = "New brief (server assigns session_id)",
            description = "Omit `session_id` and `resume_token` on first call.",
            value = list(
              task = "Situational snapshot: flooding along the Cedar River in eastern Iowa, last 24 hours.",
              max_turns = 6L
            )
          ),
          resume_after_pause = list(
            summary = "Resume after paused_for_human",
            description = "Provide matching `session_id` and `resume_token` from the paused response.",
            value = list(
              task = "Add detail for the west-side river wards since yesterday 18:00 local.",
              session_id = "8f1c2b3a-4d5e-6f70-89ab-c0def1234567",
              resume_token = "paste-the-resume_token-from-previous-response"
            )
          )
        )
      )
    )
  )
  spec$paths$`/hooks/agent`$post$responses = list(
    `200` = list(
      description = "Successful brief result or paused-for-human response.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/AgentResponse")))
    ),
    `403` = list(
      description = "Invalid or missing resume_token for paused session.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/DetailOnlyError")))
    ),
    `404` = list(
      description = "Unknown session_id when resume_token is provided.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/DetailOnlyError")))
    ),
    `500` = list(
      description = "Server-side error (missing OLLAMA_API_KEY or model/tool failure).",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/AgentResponse")))
    ),
    `503` = list(
      description = "Agent stopped; call /hooks/control with action=start.",
      content = list(`application/json` = list(schema = list(`$ref` = "#/components/schemas/AgentResponse")))
    )
  )

  spec
}

#* @plumber
function(pr) {
  pr %>%
    pr_set_serializer(serializer_unboxed_json()) %>%
    pr_set_api_spec(enhance_openapi_spec)
}
