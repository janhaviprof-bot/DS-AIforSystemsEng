![Banner Image](../../docs/images/icons.png)

# README `08_function_calling/mcp_fastapi/`

> Host your tools as a live HTTP server using the **Model Context Protocol (MCP)**. Any MCP client (Cursor, Claude Desktop, a local Ollama agent, etc.) can discover and call your tools over **`POST /mcp`** with JSON-RPC.

The R twin of this folder is [`mcp_plumber/`](../mcp_plumber/) — same tools and protocol, different stack.

---

## What is an MCP server?

When tools live in-process (scripts 02–04), the agent and the tool share one runtime. An MCP server moves the tool behind HTTP: the LLM still chooses *when* to call it, but the code can run on another host or behind Posit Connect.

**Stateless HTTP (Streamable HTTP)** means each request is independent: the client sends one JSON-RPC envelope per `POST`, and the server returns JSON (or **202** with an empty body for notifications).

---

## Files

| File | Purpose |
|------|---------|
| [`server.py`](server.py) | MCP server — tool definitions, `run_tool()`, JSON-RPC router, `POST/GET/OPTIONS /mcp` |
| [`testme.py`](testme.py) | Hand-test JSON-RPC and optional Ollama agent loop |
| [`deployme.py`](deployme.py) | Example `rsconnect deploy fastapi` invocation (path: this folder) |
| [`runme.py`](runme.py) | Run uvicorn locally on port 8000 with reload |
| [`requirements.txt`](requirements.txt) | Dependencies for local run and Connect |

---

## Quickstart (from repo root)

**Terminal 1 — start the API**

```bash
cd 08_function_calling/mcp_fastapi
uvicorn server:app --port 8000 --reload
```

Or from the repo root:

```bash
python 08_function_calling/mcp_fastapi/runme.py
```

**Terminal 2 — exercise the MCP contract**

```bash
python 08_function_calling/mcp_fastapi/testme.py
```

In `testme.py`, set `SERVER = "http://127.0.0.1:8000/mcp"` for local use.

---

## Cursor and Streamable HTTP (practical notes)

Remote MCP clients validate JSON closely. When extending `server.py`, keep the following in mind:

- **URL** — The MCP entrypoint is **`/mcp`**. In Cursor `mcp.json`, the `url` must end with `/mcp`.
- **`initialize`** — `capabilities.tools` must be a JSON **object** (e.g. `{"tools": {}}`), not an array `[]`.
- **`ping`** — Result must be `{}`, not `[]`.
- **Notifications** — Methods under `notifications/` should get **202** with an empty body.
- **`OPTIONS /mcp`** — Some stacks send a preflight; respond with **204** and `Allow: GET, POST, OPTIONS`.
- **Redeploy** after changing `server.py` so remote clients pick up fixes.

More detail: [Model Context Protocol — transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

---

## Activities

- [ACTIVITY: Build and Deploy an MCP Server](../ACTIVITY_mcp_server.md)

---

## Tradeoffs: FastAPI vs Plumber

| | FastAPI (this folder) | Plumber ([`mcp_plumber/`](../mcp_plumber/)) |
|---|---|---|
| **Deployment** | `rsconnect deploy fastapi` or Docker | `rsconnect::deployAPI()` |
| **Tool logic** | pandas, Python packages | tidyverse, R packages |
| **Server name in MCP** | `py-summarizer` | `r-summarizer` |

---

![Footer Image](../../docs/images/icons.png)

← 🏠 [Back to `08_function_calling`](../README.md)
