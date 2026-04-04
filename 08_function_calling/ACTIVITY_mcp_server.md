# 📌 ACTIVITY

## Build and Deploy an MCP Server

🕒 *Estimated Time: 20-30 minutes*

---

## Background

So far, the tools your agents use live in the same script. **MCP (Model Context Protocol)** lets you host tools as HTTP endpoints — any LLM client can discover and call them automatically, whether they're running locally or on a server.

The pattern is identical in R and Python:

```
POST /mcp  →  JSON-RPC handler  →  your function  →  JSON result
```

---

## ✅ Your Task

### 🧱 Stage 1: Run the Server Locally

**R path:**

- [ ] Open [`mcp_plumber/plumber.R`](mcp_plumber/plumber.R) — read through the three sections: tool definitions, tool logic, and the JSON-RPC router
- [ ] Start the server: `Rscript -e "plumber::plumb('08_function_calling/mcp_plumber/plumber.R')$run(port=8000)"`

**Python path:**

- [ ] Open [`mcp_fastapi/server.py`](mcp_fastapi/server.py) — compare it side-by-side with `plumber.R`; the structure is the same
- [ ] Start the server: `uvicorn server:app --port 8000 --reload` from `mcp_fastapi/`, or `python 08_function_calling/mcp_fastapi/runme.py` from the repo root

### 🧱 Stage 2: Test the Server by Hand

- [ ] Open [`mcp_plumber/testme.R`](mcp_plumber/testme.R) or [`mcp_fastapi/testme.py`](mcp_fastapi/testme.py)
- [ ] Run Steps 1–3 (initialize → tools/list → tools/call) and confirm you get summary output
- [ ] Run Step 4 and confirm the LLM selects the right tool on its own

### 🧱 Stage 3: Add Your Own Tool

- [ ] Add a second tool to `mcp_plumber/plumber.R` or `mcp_fastapi/server.py` — something that returns data you care about (e.g., filter rows, compute a regression, look up a value)
- [ ] Test it with `mcp_request("tools/call", ...)` directly
- [ ] Verify the LLM can call it when asked naturally

### 🧱 Stage 4 (Optional): Deploy

- [ ] Review [`mcp_plumber/deployme.R`](mcp_plumber/deployme.R) or [`mcp_fastapi/deployme.py`](mcp_fastapi/deployme.py)
- [ ] If you have Posit Connect access, deploy your server and update the `SERVER` URL in your test script

---

## Key Concepts

| Term | Meaning |
|------|---------|
| **MCP** | Model Context Protocol — a standard for AI tool APIs |
| **Stateless HTTP** | Every request is independent — no session state needed |
| **JSON-RPC** | The message format MCP uses (method + params → result) |
| **tools/list** | The method clients call to discover available tools |
| **tools/call** | The method that actually runs your function |

---

## 📤 To Submit

- For credit: Submit a screenshot showing your new tool being called (either directly or via the LLM in Step 4).

---

![](../../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
