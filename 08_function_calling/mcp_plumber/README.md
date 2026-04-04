![Banner Image](../../docs/images/icons.png)

# README `08_function_calling/mcp_plumber/`

> Host your tools as a live HTTP server using the **Model Context Protocol (MCP)**. Any MCP client (Cursor, Claude Desktop, a local Ollama agent, etc.) can discover and call your tools over **`POST /mcp`** with JSON-RPC.

The Python twin of this folder is [`mcp_fastapi/`](../mcp_fastapi/) — same tools and protocol, different stack.

---

## What is an MCP server?

When tools live in-process (scripts 02–04), the agent and the tool share one runtime. An MCP server moves the tool behind HTTP: the LLM still chooses *when* to call it, but the code can run on another machine or behind Posit Connect.

**Stateless HTTP (Streamable HTTP)** means each request is independent: the client sends one JSON-RPC envelope per `POST`, and the server returns JSON (or a 202 with an empty body for notifications).

---

## Files

| File | Purpose |
|------|---------|
| [`plumber.R`](plumber.R) | MCP server — tool definitions, `run_tool()`, JSON-RPC router, `POST/GET/OPTIONS /mcp` |
| [`testme.R`](testme.R) | Hand-test JSON-RPC (`initialize` → `tools/list` → `tools/call`) and optional Ollama agent loop |
| [`deployme.R`](deployme.R) | Deploy the API to Posit Connect with `rsconnect::deployAPI()` |
| [`runme.R`](runme.R) | One-liner to run the API locally on port 8000 |
| [`pingme.sh`](pingme.sh) | Example `curl` for `ping` (set `MCP_URL` / `CONNECT_API_KEY`; do not commit real keys) |
| [`manifest.json`](manifest.json) | Connect bundle manifest (generated/updated by `rsconnect::writeManifest` as needed) |
| [`rsconnect/`](rsconnect/) | Optional saved Connect publishing metadata |

---

## Quickstart (from repo root)

**Terminal 1 — start the API**

```r
Rscript -e "plumber::plumb('08_function_calling/mcp_plumber/plumber.R')$run(port=8000)"
```

Or open `runme.R` in RStudio and run it (adjust the path if your working directory is not the repo root).

**Terminal 2 — exercise the MCP contract**

```r
source("08_function_calling/mcp_plumber/testme.R")
```

In `testme.R`, set `SERVER <- "http://127.0.0.1:8000/mcp"` for local use, or your deployed `https://.../mcp` URL.

---

## Cursor and Streamable HTTP (practical notes)

Remote MCP clients are strict about JSON shape. When extending `plumber.R`, keep the following in mind:

- **URL** — The MCP entrypoint is **`/mcp`**. In Cursor `mcp.json`, the `url` must end with `/mcp`, not only the app root.
- **`initialize`** — `capabilities.tools` must be a JSON **object** (e.g. `{}`), not an array. In R, a bare `list()` serializes to `[]` via jsonlite; use a zero-field named list (see `empty_json_object()` in `plumber.R`).
- **`ping`** — Result must be `{}`, not `[]`.
- **Response body** — Return one JSON-RPC object. Do not double-encode (e.g. `toJSON()` string passed through Plumber’s JSON serializer again).
- **`notifications/*`** — Reply with **202** and an empty body.
- **Redeploy** Posit Connect after changing `plumber.R` so remote clients pick up fixes.

More detail: [Model Context Protocol — transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

---

## Activities

- [ACTIVITY: Build and Deploy an MCP Server](../ACTIVITY_mcp_server.md)

---

## Tradeoffs: Plumber vs FastAPI

| | Plumber (this folder) | FastAPI ([`mcp_fastapi/`](../mcp_fastapi/)) |
|---|---|---|
| **Deployment** | `rsconnect::deployAPI()` | `rsconnect deploy fastapi` or Docker |
| **Tool logic** | tidyverse, R packages | pandas, Python packages |
| **Server name in MCP** | `r-summarizer` | `py-summarizer` |

---

![Footer Image](../../docs/images/icons.png)

← 🏠 [Back to `08_function_calling`](../README.md)
