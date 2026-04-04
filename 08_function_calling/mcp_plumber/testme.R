# testme.R
# Build and Test a Stateless MCP Server (R)
# Pairs with mcp_fastapi/testme.py
# Tim Fraser

# What is an MCP server?
#   MCP = Model Context Protocol — a standard that lets LLMs call external tools
#   over HTTP. Instead of defining tools locally, you host them as endpoints.
#   Any MCP-compatible client (Claude Desktop, Cursor, etc.) can discover and
#   call your tools automatically.
#
# This script walks through:
#   1. What the server looks like (plumber.R)
#   2. How to run it locally and test it by hand
#   3. How to connect it to an LLM via httr2


# 0. SETUP ###################################

library(httr2)    # for HTTP requests
library(jsonlite) # for JSON encoding / decoding
library(dplyr)

# Start the Ollama server in a background R process
# system2("R", "-e \"source('08_function_calling/01_ollama.R')\"", stdout = FALSE, stderr = FALSE, wait = FALSE)

# Start the server in a background R process
# system2("R", "-e \"plumber::plumb('08_function_calling/mcp_plumber/plumber.R')$run(port=8000)\"", stdout = FALSE, stderr = FALSE, wait = FALSE)

# Start the server in a background R process before running this script:
#   R -e "plumber::plumb('08_function_calling/mcp_plumber/plumber.R')$run(port=8000)"
# Or, in RStudio: open plumber.R and click the "Run API" button.

if (file.exists(".env")) { readRenviron(".env") }else{ warning(".env file not found. Make sure it exists in the project root.") }

# Set server base URL.
# You can use your local API (if you execut runme.R)
# SERVER <- "http://127.0.0.1:8000/mcp"
# Or you can use my deployed API (or udpate to yours), assuming you provide a Posit Connect viewer API key.
SERVER <- "https://connect.systems-apps.com/plumbermcp/mcp"

# ── Helper: send one JSON-RPC request ───────────────────────

mcp_request <- function(method, params = list(), id = 1L, headers = c()) {
  # Testing values
  # method = "initialize"; params = list( protocolVersion = "2025-03-26",  clientInfo      = list(name = "r-test-client", version = "0.1.0"), capabilities    = list()); id = 1

  body <- list(jsonrpc = "2.0", id = id, method = method, params = params)

  resp <- request(SERVER) |>
    req_headers(
      "Content-Type" = "application/json", 
      # Only need this for Posit Connect, but Ollama doesn't care and will accept it.
      "Authorization" = paste0("Key ", Sys.getenv("CONNECT_API_KEY"))) |>
    req_body_raw(toJSON(body, auto_unbox = TRUE, null = "null")) |>
    req_perform()

  content <- resp |> resp_body_string()
  # Plumber may return the body as JSON text once or double-wrapped as a JSON string.
  x <- fromJSON(content, simplifyVector = FALSE)
  if (is.character(x) && length(x) == 1L && nzchar(x) && startsWith(trimws(x), "{")) {
    x <- fromJSON(x, simplifyVector = FALSE)
  }
  x
}

# First tools/call content block is JSON text (see plumber.R)
mcp_text_block <- function(r) r$result$content[[1]]$text

# 1. HANDSHAKE — initialize ##############################

# Every MCP session begins with an initialize call.
# The server responds with its name, version, and capabilities.
# JSON-RPC wraps that payload under `result` (not at the top level of the response).

init <- mcp_request("initialize", list(
  protocolVersion = "2025-03-26",
  clientInfo      = list(name = "r-test-client", version = "0.1.0"),
  capabilities    = list()
), headers = headers)

cat("Server:", init$result$serverInfo$name, "v", init$result$serverInfo$version, "\n")

# 2. DISCOVER TOOLS — tools/list #########################

# Ask the server what tools it exposes.
# Each tool has a name, description, and inputSchema — same format as local tools.

tools <- mcp_request("tools/list")
cat("Available tools:\n")
print(tools$result) 

# 3. CALL A TOOL — tools/call ############################

# Call the summarize_dataset tool with dataset_name = "mtcars"
result <- mcp_request("tools/call", list(
  name      = "summarize_dataset",
  arguments = list(dataset_name = "mtcars")
))


# Tool output: JSON summary string in first content block
mcp_text_block(result) %>% fromJSON() %>% print()

# 4. CONNECT AN LLM TO THE MCP SERVER ####################

# So far we've called the MCP server directly.
# Now let's let the LLM decide *when* to call it and with *what* arguments.
#
# Pattern:
#   a. Pull tool metadata from the server (tools/list)
#   b. Build tool objects in ollamar's expected format
#   c. Pass them to chat() just like local tools
#   d. When the LLM returns a tool_call, POST it to tools/call ourselves

library(ollamar)

MODEL <- "smollm2:1.7b"

## 4a. Fetch tool metadata from the server ---------------

tools_raw <- mcp_request("tools/list")


tools_raw %>% str()

## 4b. Convert to ollamar tool format --------------------
# Ollamar expects list(type="function", function=list(name, description, parameters))
# MCP tools already carry inputSchema — we just rename it.

mcp_to_ollamar <- function(tool) {
  # jsonlite often simplifies nested JSON Schema to data.frames; Ollama rejects that (HTTP 400).
  schema <- tool$inputSchema
  params <- fromJSON(
    toJSON(schema, auto_unbox = TRUE, null = "null"),
    simplifyVector = FALSE
  )
  list(
    type     = "function",
    "function" = list(
      name        = tool$name,
      description = tool$description,
      parameters  = params
    )
  )
}

# tools/list returns { tools: [ ... ] } → R list result$tools.
# If you lapply(tools_raw$result, ...) you only map over the one name "tools" and get
# ollama_tools$tools (wrong). Always index the array explicitly.
tool_list <- tools_raw$result[["tools"]]
if (is.null(tool_list)) {
  stop("tools/list: missing result$tools. names(tools_raw$result): ",
       paste(names(tools_raw$result), collapse = ", "))
}
# Rare edge case: one tool as object (not JSON array) → R list with name/description/inputSchema
looks_like_tool <- function(x) {
  is.list(x) && !is.null(x[["name"]]) && !is.null(x[["inputSchema"]])
}
if (looks_like_tool(tool_list)) {
  tool_list <- list(tool_list)
}
ollama_tools <- lapply(tool_list, mcp_to_ollamar)
ollama_tools

# Quick printout of ollama_tools (one element per MCP tool):
# > ollama_tools[[1]]
# $type
# [1] "function"
# $function
# $function$name
# [1] "summarize_dataset"
# ... description, parameters (from inputSchema)


## 4c. Ask the LLM a question that requires the tool -----

messages <- create_message(role = "user",
  content = "Give me a summary of the iris dataset.")

# ollamar expects tools = list(tool1, tool2, ...) — same pattern as 02_function_calling.R
resp <- chat(model = MODEL, messages = messages,
             tools = ollama_tools, output = "tools", stream = FALSE)


## 4d. Execute the tool call against the MCP server ------

tool_call <- resp[[1]]

result <- mcp_request("tools/call", list(
  name      = tool_call$name,
  arguments = tool_call$arguments
))

cat("LLM chose tool:", tool_call$name, "\n")
# mcp_request() returns the full JSON-RPC object; tool output lives under result$result
cat(mcp_text_block(result))

# Clean up
rm(list = ls())
