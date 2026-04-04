# R/guardrails.R
# Limits and safe paths for the course autonomous agent (Plumber edition)
# Tim Fraser
#
# Topic: AI for Data Management — parity with agentpy/app/guardrails.py

`%||%` = function(a, b) {
  if (is.null(a)) {
    b
  } else {
    a
  }
}

# 0. CONSTANTS ###############################################################

MAX_AUTONOMOUS_TURNS = 10L
MAX_WEB_SEARCHES_PER_REQUEST = 3L
MAX_SKILL_READS_PER_REQUEST = 8L

SKILLS_DIR_NAME = "skills"

# 1. PATHS ###################################################################

#' Activity root: AGENT.md, skills/, logs/ (agentr/ folder when cwd is set correctly).
agent_root = function() {
  o = Sys.getenv("AGENTR_ROOT", unset = "")
  if (nzchar(o)) {
    return(normalizePath(o, winslash = "/", mustWork = FALSE))
  }
  normalizePath(getwd(), winslash = "/", mustWork = FALSE)
}

skills_dir = function() {
  file.path(agent_root(), SKILLS_DIR_NAME)
}

# 2. SKILL FILES #############################################################

skill_basename_ok = function(basename) {
  grepl("^[a-zA-Z0-9_-]+\\.md$", basename)
}

read_skill_file = function(basename) {
  if (is.null(basename) || !nzchar(as.character(basename))) {
    stop("Skill name must be a non-empty string.")
  }
  basename = as.character(basename)
  if (!skill_basename_ok(basename)) {
    stop("Invalid skill filename (use basename like evidence_brief.md).")
  }
  full = normalizePath(file.path(skills_dir(), basename), winslash = "/", mustWork = FALSE)
  root_resolved = normalizePath(skills_dir(), winslash = "/", mustWork = FALSE)
  if (!startsWith(full, root_resolved)) {
    stop("Skill path must stay inside skills/.")
  }
  if (!file.exists(full)) {
    stop(paste0("Skill not found: ", basename))
  }
  paste(readLines(full, encoding = "UTF-8", warn = FALSE), collapse = "\n")
}

clamp_turns = function(requested) {
  if (is.null(requested)) {
    return(as.integer(MAX_AUTONOMOUS_TURNS))
  }
  n = suppressWarnings(as.integer(requested))
  if (is.na(n)) {
    return(as.integer(MAX_AUTONOMOUS_TURNS))
  }
  max(1L, min(n, as.integer(MAX_AUTONOMOUS_TURNS)))
}

min_completion_turns = function() {
  raw = trimws(Sys.getenv("AGENT_MIN_COMPLETION_TURNS", unset = ""))
  if (nzchar(raw) && grepl("^[0-9]+$", raw)) {
    n = as.integer(raw)
    return(max(1L, min(n, as.integer(MAX_AUTONOMOUS_TURNS))))
  }
  if (nzchar(trimws(Sys.getenv("SERPER_API_KEY", unset = "")))) {
    return(min(2L, as.integer(MAX_AUTONOMOUS_TURNS)))
  }
  1L
}

task_size_ok = function(task, max_chars = NULL) {
  if (is.null(max_chars)) {
    mc = Sys.getenv("AGENT_MAX_TASK_CHARS", unset = "8000")
    max_chars = suppressWarnings(as.integer(mc))
    if (is.na(max_chars)) {
      max_chars = 8000L
    }
  }
  is.character(task) && length(task) == 1L && nzchar(task) && nchar(task) <= max_chars
}
