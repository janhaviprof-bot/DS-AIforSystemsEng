# R/logging.R
# Optional file logging for agent turn trace — parity with agentpy/app/logging_setup.py
# Tim Fraser

.agent_log_path = NULL
.agent_logger_configured = FALSE

configure_agent_logging = function() {
  if (.agent_logger_configured) {
    return(invisible(NULL))
  }
  .agent_logger_configured <<- TRUE

  raw = Sys.getenv("AGENT_LOG_FILE", unset = NA_character_)
  path = NULL
  if (is.na(raw)) {
    log_dir = file.path(agent_root(), "logs")
    if (!dir.exists(log_dir)) {
      dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
    }
    path = file.path(log_dir, "agent.log")
  } else {
    stripped = trimws(raw)
    if (!nzchar(stripped) || tolower(stripped) %in% c("0", "off", "false", "no")) {
      .agent_log_path <<- NULL
      return(invisible(NULL))
    }
    path = stripped
    if (!grepl("^(/|[A-Za-z]:)", path)) {
      path = normalizePath(file.path(agent_root(), path), winslash = "/", mustWork = FALSE)
    }
    log_dir = dirname(path)
    if (nzchar(log_dir) && !dir.exists(log_dir)) {
      dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
    }
  }

  con = tryCatch(
    file(path, open = "a", encoding = "UTF-8"),
    error = function(e) {
      message("agent logging: could not open ", path, ": ", conditionMessage(e))
      NULL
    }
  )
  if (!is.null(con)) {
    close(con)
    .agent_log_path <<- path
  }
  invisible(NULL)
}

agent_log_line = function(level, msg) {
  if (is.null(.agent_log_path)) {
    return(invisible(NULL))
  }
  line = paste0(format(Sys.time(), usetz = TRUE), " ", level, " ", msg, "\n")
  tryCatch(
    cat(line, file = .agent_log_path, append = TRUE),
    error = function(e) invisible(NULL)
  )
}

agent_log_info = function(msg) {
  agent_log_line("INFO", msg)
}

agent_log_warn = function(msg) {
  agent_log_line("WARN", msg)
}
