# plumber.R
# Stateless MCP Server — Plumber API (R)
# Pairs with mcp_fastapi/server.py
# Tim Fraser
#
# What this file is:
#   A Plumber API that speaks the Model Context Protocol (MCP) over HTTP.
#   It is stateless: every POST to /mcp is a self-contained JSON-RPC call.
#   Cursor and other MCP clients use Streamable HTTP (spec 2025-03-26+): they
#   POST JSON-RPC and expect a real JSON object body — not a JSON *string* that
#   contains escaped JSON. Do not run the response through Plumber's JSON
#   serializer twice (see POST /mcp handler).
#
# How to run locally:
#   Rscript -e "plumber::plumb('08_function_calling/mcp_plumber/plumber.R')$run(port=8000)"
#
# How to deploy to Posit Connect:
#   See deployme.R
#
# MCP client config (e.g., Claude Desktop):
#   {
#     "mcpServers": {
#       "r-summarizer": {
#         "url": "https://your-connect-server.com/content/<id>/mcp",
#         "headers": { "Authorization": "Key YOUR_CONNECT_API_KEY" }
#       }
#     }
#   }

library(plumber)
library(dplyr)
library(jsonlite)

# ── Tool definitions (what the LLM sees) ────────────────────

TOOLS <- list(
  list(
    name        = "summarize_dataset",
    description = "Returns mean, sd, min, and max for each numeric column in a dataset.",
    inputSchema = list(
      type       = "object",
      properties = list(
        dataset_name = list(
          type        = "string",
          description = "Dataset to summarize. Options: 'mtcars' or 'iris'."
        )
      ),
      required = list("dataset_name")
    )
  )
)

# ── Tool logic (your actual R code) ─────────────────────────

run_tool <- function(name, args) {
  if (name == "summarize_dataset") {

    datasets <- list(mtcars = mtcars, iris = iris)
    nm <- args$dataset_name

    if (!nm %in% names(datasets)) {
      stop(paste("Unknown dataset:", nm, "- choose 'mtcars' or 'iris'"))
    }

    result <- datasets[[nm]] |>
      summarise(across(where(is.numeric), list(
        mean = \(x) round(mean(x, na.rm = TRUE), 2),
        sd   = \(x) round(sd(x,   na.rm = TRUE), 2),
        min  = \(x) min(x,  na.rm = TRUE),
        max  = \(x) max(x,  na.rm = TRUE)
      ))) |>
      tidyr::pivot_longer(
        everything(),
        names_to  = c("variable", "stat"),
        names_sep = "_(?=[^_]+$)"
      ) |>
      tidyr::pivot_wider(names_from = stat, values_from = value)

    return(toJSON(result, auto_unbox = TRUE, pretty = TRUE))
  }

  stop(paste("Unknown tool:", name))
}

# jsonlite maps bare list() to JSON [] — MCP expects {} for ping result and
# InitializeResult.capabilities.tools (an object, not an array).
empty_json_object <- function() structure(list(), names = character(0))

# ── MCP JSON-RPC router ──────────────────────────────────────

handle_jsonrpc <- function(req) {
  body <- fromJSON(rawToChar(req$bodyRaw %||% chartr("", "", req$body)),
                   simplifyVector = FALSE)

  method <- body$method
  id     <- body$id      # NULL for notifications

  # JSON-RPC notifications have no id; MCP uses 202 Accepted with empty body.
  if (!is.null(method) && startsWith(method, "notifications/")) {
    return(list(status = 202L, body = NULL))
  }

  result <- tryCatch({

    if (method == "initialize") {
      list(
        protocolVersion = "2025-03-26",
        capabilities    = list(tools = empty_json_object()),
        serverInfo      = list(name = "r-summarizer", version = "0.1.0")
      )

    } else if (method == "ping") {
      empty_json_object()

    } else if (method == "tools/list") {
      list(tools = TOOLS)

    } else if (method == "tools/call") {
      tool_result <- run_tool(body$params$name, body$params$arguments)
      list(
        content = list(list(type = "text", text = tool_result)),
        isError = FALSE
      )

    } else {
      stop(paste("Method not found:", method))
    }

  }, error = function(e) {
    list(`__jsonrpc_error` = TRUE, code = -32601L, message = conditionMessage(e))
  })

  if (!is.null(result$`__jsonrpc_error`)) {
    response <- list(jsonrpc = "2.0", id = id,
                     error = list(code = result$code, message = result$message))
  } else {
    response <- list(jsonrpc = "2.0", id = id, result = result)
  }

  list(status = 200L, body = toJSON(response, auto_unbox = TRUE, null = "null"))
}

# ── Plumber endpoints ────────────────────────────────────────

#* @post /mcp
function(req, res) {
  out <- handle_jsonrpc(req)
  res$status <- out$status
  # MCP clients parse the HTTP body as one JSON-RPC object. If we used
  # @serializer unboxedJSON on a value from toJSON(), Plumber would emit a
  # quoted JSON string (invalid_union / "expected object, received string").
  if (is.null(out$body)) {
    res$body <- raw(0)
    return(res)
  }
  res$setHeader("Content-Type", "application/json; charset=UTF-8")
  res$body <- charToRaw(enc2utf8(out$body))
  res
}

#* CORS / proxy preflight (some HTTP stacks probe OPTIONS before POST).
#* @options /mcp
function(res) {
  res$status <- 204L
  res$setHeader("Allow", "GET, POST, OPTIONS")
  res$body <- raw(0)
  res
}

#* GET /mcp — Streamable HTTP: 405 means no standalone SSE stream here.
#* @get /mcp
function(res) {
  res$status <- 405L
  res$setHeader("Allow", "GET, POST, OPTIONS")
  list(error = "This MCP server uses stateless HTTP. Use POST.")
}

