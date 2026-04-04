# R/context.R
# Load AGENT.md and enumerate skill files for the system prompt
# Tim Fraser
#
# Parity with agentpy/app/context.py

FALLBACK_AGENT = paste0(
  "You assist disaster response coordinators with brief open-source situational summaries.\n\n",
  "Produce markdown sections:\n",
  "## Question restatement (incident, geography, time window if any)\n",
  "## Key points (3 bullets max; never invent numbers or quotes; tie claims to retrieved text only)\n",
  "## References (numbered list: verbatim URLs only from Retrieved URLs for References blocks, ",
  "or state no URLs retrieved)\n",
  "## Confidence (low/medium/high + one sentence)\n\n",
  "End with a line containing only: END_BRIEF\n\n",
  "Use read_skill and web_search when available. Never invent URLs."
)

load_agent_instructions = function() {
  path = file.path(agent_root(), "AGENT.md")
  if (file.exists(path)) {
    paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  } else {
    FALLBACK_AGENT
  }
}

list_skill_basenames = function() {
  root = skills_dir()
  if (!dir.exists(root)) {
    return(character())
  }
  files = list.files(root, pattern = "\\.md$", full.names = FALSE)
  files = sort(files)
  files[files != "README.md"]
}

build_system_prompt = function() {
  base = trimws(load_agent_instructions())
  skills = list_skill_basenames()
  if (length(skills) == 0L) {
    appendix = paste0(
      "\n\n## Available skills\n\n",
      "_No skill `.md` files found under `skills/`._"
    )
  } else {
    lines = paste0("- `", skills, "`", collapse = "\n")
    appendix = paste0(
      "\n\n## Available skills (load with read_skill)\n\n",
      lines,
      "\n\nCall `read_skill` with the **filename** exactly as listed ",
      "(e.g. `disaster_situational_brief.md`)."
    )
  }
  paste0(base, appendix)
}
