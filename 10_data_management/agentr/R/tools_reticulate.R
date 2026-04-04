# R/tools_reticulate.R
# CrewAI SerperDevTool via reticulate + read_skill for Ollama tool calling
# Tim Fraser
#
# Parity with agentpy/app/tools.py

MAX_TOOL_OUTPUT_CHARS = 4000L

ollama_tool_definitions = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "read_skill",
        description = paste0(
          "Load a markdown skill from the skills/ folder (disaster briefs, sourcing rules). ",
          "Exact basename only (e.g. disaster_situational_brief.md, references_section.md)."
        ),
        parameters = list(
          type = "object",
          properties = list(
            filename = list(
              type = "string",
              description = "Filename only, must end with .md"
            )
          ),
          required = list("filename")
        )
      )
    ),
    list(
      type = "function",
      `function` = list(
        name = "web_search",
        description = paste0(
          "Search the web for current disaster or incident reporting. ",
          "If search is disabled, the result explains that—do not invent URLs."
        ),
        parameters = list(
          type = "object",
          properties = list(
            query = list(
              type = "string",
              description = paste0(
                "Focused query: event name, location, date or 'today', ",
                "optional keywords (evacuation, outage, shelter, OEM)."
              )
            )
          ),
          required = list("query")
        )
      )
    )
  )
}

parse_function_arguments = function(raw) {
  if (is.null(raw)) {
    return(list())
  }
  if (is.list(raw) && !is.character(raw)) {
    return(raw)
  }
  if (is.character(raw)) {
    s = trimws(raw)
    if (!nzchar(s)) {
      return(list())
    }
    parsed = tryCatch(
      jsonlite::fromJSON(s, simplifyVector = FALSE),
      error = function(e) list()
    )
    if (is.list(parsed)) {
      return(parsed)
    }
    return(list())
  }
  list()
}

truncate_tool_output = function(s, limit = MAX_TOOL_OUTPUT_CHARS) {
  if (nchar(s) <= limit) {
    return(s)
  }
  paste0(substr(s, 1L, as.integer(limit) - 20L), "\n...[truncated]")
}

extract_urls_from_text = function(text) {
  if (is.null(text) || !nzchar(text)) {
    return(character())
  }
  m = gregexpr("https?://[^\\s\\)\\]\\\"'<>]+", text, perl = TRUE, ignore.case = TRUE)
  reg = regmatches(text, m)[[1L]]
  if (length(reg) == 0L) {
    return(character())
  }
  reg = sub("[.,;\\)\\]>\\\"']+$", "", reg)
  out = character()
  for (u in reg) {
    if (!u %in% out) {
      out = c(out, u)
    }
    if (length(out) >= 10L) {
      break
    }
  }
  out
}

title_url_pairs_from_raw = function(raw) {
  text = trimws(raw %||% "")
  if (!nzchar(text)) {
    return(list())
  }
  pairs = tryCatch(
    {
      data = jsonlite::fromJSON(text, simplifyVector = FALSE)
      if (is.list(data) && !is.null(data$organic) && is.list(data$organic)) {
        org = data$organic
        out = list()
        for (item in org[seq_len(min(length(org), 10L))]) {
          if (!is.list(item)) {
            next
          }
          url = trimws(as.character(item$link %||% ""))
          if (!nzchar(url)) {
            next
          }
          title = trimws(as.character(item$title %||% ""))
          if (!nzchar(title)) {
            title = url
          }
          out[[length(out) + 1L]] = list(title = title, url = url)
        }
        if (length(out) > 0L) {
          return(out)
        }
      }
      NULL
    },
    error = function(e) NULL
  )
  if (!is.null(pairs)) {
    return(pairs)
  }
  urls = extract_urls_from_text(text)
  lapply(urls, function(u) list(title = u, url = u))
}

reference_block_for_model = function(pairs) {
  lines = c(
    "### Retrieved URLs for References",
    "",
    paste0(
      "_Every URL below is safe to cite. Copy each **URL** exactly into your `## References` section ",
      "(numbered list). Do not add URLs that are not listed here or in another search block in this thread._"
    ),
    ""
  )
  if (length(pairs) == 0L) {
    lines = c(
      lines,
      paste0(
        "_No URLs were extracted from this search output. In `## References` write exactly one line: ",
        "**No URLs retrieved from search results.** Do not invent links._"
      )
    )
    return(paste(lines, collapse = "\n"))
  }
  for (i in seq_along(pairs)) {
    p = pairs[[i]]
    lines = c(
      lines,
      paste0(i, ". **", p$title, "**"),
      paste0("   - URL (verbatim): `", p$url, "`")
    )
  }
  lines = c(
    lines,
    "",
    "_In the brief: `## References` must list the same URLs (markdown links or bare URLs)._"
  )
  paste(lines, collapse = "\n")
}

assemble_search_payload = function(ref_block, body) {
  body = trimws(body %||% "")
  if (!nzchar(body)) {
    return(truncate_tool_output(ref_block))
  }
  combined = paste0(ref_block, "\n\n### Search tool output (raw)\n\n", body)
  truncate_tool_output(combined)
}

run_read_skill = function(filename) {
  fn = trimws(as.character(filename %||% ""))
  out = tryCatch(
    truncate_tool_output(read_skill_file(fn)),
    error = function(e) {
      paste0("read_skill error: ", conditionMessage(e))
    }
  )
  out
}

run_web_search = function(query) {
  key = trimws(Sys.getenv("SERPER_API_KEY", unset = ""))
  if (!nzchar(key)) {
    return(paste0(
      "Web search is disabled: SERPER_API_KEY is not set on the server. ",
      "Do not invent URLs; use your training data and state low confidence.\n\n",
      "### Retrieved URLs for References\n\n",
      "_Search is **disabled**. In `## References` write exactly one numbered item: ",
      "**No URLs retrieved from live search in this session (search disabled).** ",
      "Do not add any http(s) links._\n"
    ))
  }
  q = trimws(as.character(query %||% ""))
  if (!nzchar(q)) {
    return("web_search error: empty query.")
  }

  raw = tryCatch(
    {
      ct = reticulate::import("crewai_tools")
      tool = ct$SerperDevTool(n_results = 5L)
      out = tool$run(search_query = q)
      if (is.null(out)) {
        "(No results.)"
      } else {
        trimws(as.character(out))
      }
    },
    error = function(e) {
      paste0("web_search error: ", conditionMessage(e))
    }
  )

  body = if (nzchar(raw)) {
    raw
  } else {
    "(No results.)"
  }
  pairs = title_url_pairs_from_raw(body)
  ref_block = reference_block_for_model(pairs)
  assemble_search_payload(ref_block, body)
}
