# R/loop.R
# Multi-turn disaster situational brief loop against Ollama — parity with agentpy/app/loop.py
# Tim Fraser

END_MARKER = "END_BRIEF"

VERIFICATION_NUDGE = paste0(
  "Do **not** finish yet: the server requires more **model rounds** before it accepts END_BRIEF. ",
  "Compare **Key points** to **Retrieved URLs for References** (and any **web_search** tool output). ",
  "Revise or soften claims that are not clearly supported; call **web_search** again if you need to check a fact. ",
  "Then output the **complete** brief again (all sections) and end with a line containing only END_BRIEF."
)

random_hex_chunk = function(n) {
  paste0(format(as.hexmode(sample.int(2^31 - 1L, n, replace = TRUE)), width = 8))
}

new_resume_token_uuid = function() {
  paste0(
    random_hex_chunk(1), "-", random_hex_chunk(1), "-", random_hex_chunk(1), "-",
    random_hex_chunk(1), "-", random_hex_chunk(1)
  )
}

BEARER_RE_PATTERN = "(?i)Bearer\\s+[A-Za-z0-9._\\-~+/=]{12,}"
SK_RE_PATTERN = "\\b(sk-[A-Za-z0-9]{20,})\\b"
KV_SECRET_RE_PATTERN = "(?i)\\b(apikey|api_key|authorization|secret|password|token)\\s*[=:]\\s*\\S{8,}"

redact_for_log = function(text) {
  s = as.character(text %||% "")
  if (!nzchar(s)) {
    return(s)
  }
  s = gsub(BEARER_RE_PATTERN, "Bearer [REDACTED]", s, perl = TRUE)
  s = gsub(SK_RE_PATTERN, "[REDACTED]", s, perl = TRUE)
  s = gsub(KV_SECRET_RE_PATTERN, "\\1=[REDACTED]", s, perl = TRUE)
  s
}

preview_log_text = function(text, limit = 200L) {
  s = gsub("\n", " ", text %||% "", fixed = TRUE)
  s = trimws(s)
  if (nchar(s) <= limit) {
    return(s)
  }
  paste0(substr(s, 1L, limit - 3L), "...")
}

args_preview_log = function(args) {
  if (!is.list(args)) {
    return(preview_log_text(as.character(args), 300L))
  }
  js = tryCatch(
    jsonlite::toJSON(args, auto_unbox = TRUE),
    error = function(e) as.character(args)
  )
  preview_log_text(as.character(js), 300L)
}

clone_messages_json = function(messages) {
  jsonlite::fromJSON(
    jsonlite::toJSON(messages, auto_unbox = TRUE, null = "null"),
    simplifyVector = FALSE
  )
}

maybe_prefetch_web = function(task, search_left) {
  flag = tolower(trimws(Sys.getenv("AGENT_PREFETCH_WEB_SEARCH", unset = "1")))
  if (flag %in% c("0", "false", "no", "off")) {
    return(NULL)
  }
  if (search_left[[1L]] <= 0L) {
    return(NULL)
  }
  search_left[[1L]] = search_left[[1L]] - 1L
  q = trimws(task %||% "")
  if (nchar(q) > 800L) {
    q = substr(q, 1L, 800L)
  }
  if (!nzchar(q)) {
    q = "disaster emergency situational update"
  }
  run_web_search(q)
}

wrap_task_with_prefetch = function(task, prefetch) {
  if (is.null(prefetch)) {
    return(task)
  }
  paste0(
    "=== Server web preflight (one automatic search for this request) ===\n",
    "Ground **Key points** only in what this block and later **read_skill** / **web_search** ",
    "outputs actually contain. Use **`### Retrieved URLs for References`** below to build **`## References`** ",
    "(numbered list, verbatim URLs only). ",
    "If search is disabled or no URLs are listed, **`## References`** must state that no URLs were retrieved.\n\n",
    prefetch,
    "\n\n=== Task ===\n",
    task
  )
}

dispatch_tool_call = function(name, args, search_left, skill_left) {
  if (name == "web_search") {
    if (search_left[[1L]] <= 0L) {
      return(paste0(
        "web_search: per-request limit reached; stop calling web_search. ",
        "Finish the brief without new URLs or state that search was capped."
      ))
    }
    search_left[[1L]] = search_left[[1L]] - 1L
    return(run_web_search(as.character(args$query %||% "")))
  }
  if (name == "read_skill") {
    if (skill_left[[1L]] <= 0L) {
      return(paste0(
        "read_skill: per-request limit reached; stop calling read_skill. ",
        "Complete the brief from context already in the thread."
      ))
    }
    skill_left[[1L]] = skill_left[[1L]] - 1L
    return(run_read_skill(as.character(args$filename %||% "")))
  }
  paste0("Unknown tool ", encodeString(name, quote = "\""), "; use read_skill or web_search only.")
}

inject_forced_read_skill_round = function(messages, search_left, skill_left) {
  flag = tolower(trimws(Sys.getenv("AGENT_FORCE_FIRST_TOOL", unset = "1")))
  if (flag %in% c("0", "false", "no", "off")) {
    return(FALSE)
  }
  fn = trimws(Sys.getenv("AGENT_FORCE_FIRST_SKILL", unset = "disaster_situational_brief.md"))
  if (!nzchar(fn)) {
    fn = "disaster_situational_brief.md"
  }
  if (skill_left[[1L]] <= 0L) {
    return(FALSE)
  }

  result = dispatch_tool_call("read_skill", list(filename = fn), search_left, skill_left)
  tid = paste0("forced_read_skill_", random_hex_chunk(1), random_hex_chunk(1))
  messages[[length(messages) + 1L]] = list(
    role = "assistant",
    content = "",
    tool_calls = list(
      list(
        id = tid,
        type = "function",
        `function` = list(
          name = "read_skill",
          arguments = list(filename = fn)
        )
      )
    )
  )
  messages[[length(messages) + 1L]] = list(
    role = "tool",
    content = result,
    name = "read_skill",
    tool_name = "read_skill",
    tool_call_id = tid
  )
  TRUE
}

run_research_loop = function(
  task,
  ollama_host,
  ollama_api_key,
  model,
  max_turns = NULL,
  max_output_tokens = NULL,
  existing_messages = NULL,
  continue_thread = FALSE
) {
  configure_agent_logging()

  if (!task_size_ok(task)) {
    agent_log_info("run_research_loop rejected task (size/empty)")
    return(list(
      status = "error",
      reply = "",
      turns_used = 0L,
      prefetch_search_used = FALSE,
      forced_tool_round = FALSE,
      min_completion_turns = 1L,
      detail = "Task missing, invalid, or too long (see AGENT_MAX_TASK_CHARS)."
    ))
  }

  turns_budget = clamp_turns(max_turns)
  min_done = min(min_completion_turns(), turns_budget)
  fresh_start = is.null(existing_messages)
  system_text = build_system_prompt()
  tools = ollama_tool_definitions()
  search_left = list(as.integer(MAX_WEB_SEARCHES_PER_REQUEST))
  skill_left = list(as.integer(MAX_SKILL_READS_PER_REQUEST))
  prefetch_search_used = FALSE

  if (is.null(existing_messages)) {
    prefetch_block = maybe_prefetch_web(task, search_left)
    prefetch_search_used = !is.null(prefetch_block)
    user_content = wrap_task_with_prefetch(task, prefetch_block)
    messages = list(
      list(role = "system", content = system_text),
      list(role = "user", content = user_content)
    )
  } else {
    messages = clone_messages_json(existing_messages)
    if (isTRUE(continue_thread)) {
      cont_prefetch = maybe_prefetch_web(task, search_left)
      prefetch_search_used = !is.null(cont_prefetch)
      user_content = wrap_task_with_prefetch(task, cont_prefetch)
      messages[[length(messages) + 1L]] = list(role = "user", content = user_content)
    }
  }

  forced_tool_round = FALSE
  if (isTRUE(fresh_start)) {
    forced_tool_round = inject_forced_read_skill_round(messages, search_left, skill_left)
  }

  if (is.null(max_output_tokens)) {
    et = Sys.getenv("AGENT_MAX_OUTPUT_TOKENS", unset = "")
    max_output_tokens = if (nzchar(et) && grepl("^[0-9]+$", et)) {
      as.integer(et)
    } else {
      1024L
    }
  }

  agent_log_info(paste0(
    "loop start task_preview=", redact_for_log(preview_log_text(task)),
    " turns_budget=", turns_budget,
    " min_done=", min_done,
    " prefetch=", prefetch_search_used,
    " forced_read_skill=", forced_tool_round,
    " search_slots_left=", search_left[[1L]],
    " skill_slots_left=", skill_left[[1L]]
  ))

  turns_used = 0L
  last_content = ""

  repeat {
    if (turns_used >= turns_budget) {
      break
    }
    turns_used = turns_used + 1L
    agent_log_info(paste("turn", turns_used, "/", turns_budget, "calling Ollama model=", model))

    out = tryCatch(
      ollama_chat_once(
        ollama_host,
        ollama_api_key,
        model,
        messages,
        tools,
        max_output_tokens
      ),
      error = function(e) {
        list(error = e)
      }
    )

    if (!is.null(out$error)) {
      agent_log_warn(paste("turn", turns_used, "Ollama error:", redact_for_log(conditionMessage(out$error))))
      return(list(
        status = "error",
        reply = last_content,
        turns_used = turns_used,
        prefetch_search_used = prefetch_search_used,
        forced_tool_round = forced_tool_round,
        min_completion_turns = min_done,
        detail = conditionMessage(out$error)
      ))
    }

    msg = out$message %||% list()
    assistant_msg = msg
    messages[[length(messages) + 1L]] = assistant_msg

    tool_calls = msg$tool_calls %||% NULL
    if (!is.null(tool_calls) && length(tool_calls) > 0L) {
      agent_log_info(paste("turn", turns_used, "assistant tool_calls count=", length(tool_calls)))
      for (tc in tool_calls) {
        if (!is.list(tc)) {
          next
        }
        fn = tc[["function"]] %||% list()
        if (!is.list(fn)) {
          fn = list()
        }
        name = as.character(fn$name %||% "")
        args = parse_function_arguments(fn$arguments)
        agent_log_info(paste0(
          "turn ", turns_used, " tool ", name, " args=",
          redact_for_log(args_preview_log(args))
        ))
        result = dispatch_tool_call(name, args, search_left, skill_left)
        agent_log_info(paste0(
          "turn ", turns_used, " tool ", name, " result_len=", nchar(result),
          " preview=", redact_for_log(preview_log_text(result, 120L))
        ))
        tool_message = list(role = "tool", content = result)
        if (nzchar(name)) {
          tool_message$name = name
          tool_message$tool_name = name
        }
        tid = tc$id
        if (!is.null(tid) && nzchar(as.character(tid))) {
          tool_message$tool_call_id = tid
        }
        messages[[length(messages) + 1L]] = tool_message
      }
      next
    }

    last_content = out$content %||% ""
    agent_log_info(paste0(
      "turn ", turns_used, " assistant text_len=", nchar(last_content),
      " end_brief=", grepl(END_MARKER, last_content, fixed = TRUE),
      " preview=", redact_for_log(preview_log_text(last_content, 160L))
    ))

    if (grepl(END_MARKER, last_content, fixed = TRUE)) {
      if (turns_used < min_done) {
        agent_log_info(paste(
          "turn", turns_used, "END_BRIEF before min_done (", min_done,
          "); injecting verification nudge"
        ))
        messages[[length(messages) + 1L]] = list(role = "user", content = VERIFICATION_NUDGE)
        next
      }
      cleaned = trimws(gsub(END_MARKER, "", last_content, fixed = TRUE))
      agent_log_info(paste("loop finished ok turns_used=", turns_used))
      return(list(
        status = "ok",
        reply = cleaned,
        turns_used = turns_used,
        prefetch_search_used = prefetch_search_used,
        forced_tool_round = forced_tool_round,
        min_completion_turns = min_done,
        messages = messages
      ))
    }

    messages[[length(messages) + 1L]] = list(
      role = "user",
      content = paste0(
        "Continue and complete the disaster situational brief. ",
        "When finished, end with a line containing only END_BRIEF."
      )
    )
  }

  resume_token = new_resume_token_uuid()
  agent_log_info(paste("loop paused_for_human turns_used=", turns_used, "budget=", turns_budget))
  list(
    status = "paused_for_human",
    reply = last_content,
    turns_used = turns_used,
    prefetch_search_used = prefetch_search_used,
    forced_tool_round = forced_tool_round,
    min_completion_turns = min_done,
    resume_token = resume_token,
    messages = messages,
    detail = paste0(
      "Model did not finish within ", turns_budget,
      " turns in this request; send the same session_id with resume_token ",
      "and a short continuation task."
    )
  )
}
