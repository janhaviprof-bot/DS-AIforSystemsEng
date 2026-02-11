# 📌 ACTIVITY

## Add Documentation to Cursor

🕒 *Estimated Time: 10 minutes*

---

## ✅ Your Task: Add Custom Documentation to Cursor

Add documentation libraries to **Cursor** so the AI agent can reference them when helping you code. This activity covers adding web-based documentation for **httr2** (R) and **Python Requests**, then using them in examples.

---

## 🧱 Stage 1: Access Cursor Documentation Settings

- [ ] Open **Cursor**.
- [ ] Go to **Settings** (use `Ctrl+,` on Windows/Linux or `Cmd+,` on Mac, or click the gear icon).
- [ ] In the settings search bar, type `docs`.
- [ ] Select **Indexing & Docs** → **Docs** from the results.

You should see the **Docs** configuration panel where you can manage documentation sources.

---

## 🧱 Stage 2A: Add `httr2` Documentation for R

- [ ] In the **Docs** settings panel, click **Add new doc**.
- [ ] Fill in the following:
  - **Name**: `httr2`
  - **Prefix**: `https://httr2.r-lib.org`
  - **Entrypoint**: `https://httr2.r-lib.org`
- [ ] Click **Save** or **Add**.

**Cursor** will index the httr2 documentation. This may take a minute.

---

## 🧱 Stage 2B: Add `Requests` Documentation for Python

- [ ] In the **Docs** settings panel, click **Add new doc** again.
- [ ] Fill in the following:
  - **Name**: `requests`
  - **Prefix**: `https://requests.readthedocs.io`
  - **Entrypoint**: `https://requests.readthedocs.io/en/latest/`
- [ ] Click **Save** or **Add**.

**Cursor** will index the Requests documentation. This may take a minute.

---

## 🧱 Stage 3A: Test Documentation in Chat (R Example)

- [ ] Open a new chat in **Cursor** (use `Ctrl+L` or `Cmd+L`).
- [ ] Type: `@Docs httr2 How do I make a GET request?`
- [ ] Press Enter and review the response.

The agent should reference httr2 documentation when answering.

- [ ] Create a new R file called `test_httr2.R`.
- [ ] In the chat, type: `@Docs httr2 Write R code to make a GET request to https://api.github.com/users/octocat`
- [ ] Review the generated code and verify it uses httr2 functions.

Example of what you might see:

```r
# Example using httr2 with @Docs context
library(httr2)

# Make a GET request
response = request("https://api.github.com/users/octocat") |>
  req_perform()

# Get the response body
body = resp_body_json(response)
print(body)
```

---

## 🧱 Stage 3B: Test Documentation in Chat (Python Example)

- [ ] Open a new chat in **Cursor**.
- [ ] Type: `@Docs requests How do I make a POST request with JSON data?`
- [ ] Press Enter and review the response.

The agent should reference Requests documentation when answering.

- [ ] Create a new Python file called `test_requests.py`.
- [ ] In the chat, type: `@Docs requests Write Python code to make a POST request to https://httpbin.org/post with JSON data {"name": "test"}`
- [ ] Review the generated code and verify it uses the requests library.

Example of what you might see:

```python
# Example using requests with @Docs context
import requests

# Make a POST request with JSON data
url = "https://httpbin.org/post"
data = {"name": "test"}
response = requests.post(url, json=data)

# Get the response
print(response.status_code)
print(response.json())
```

---

## 💡 Tips

- **Multiple docs**: Add documentation for all libraries you use regularly.
- **Naming**: Use clear, memorable names for your documentation sources.
- **Combining context**: Use `@Docs` with `@filename` to combine documentation with your code context.
- **Updating docs**: If documentation sites change, update the **Entrypoint** URL in settings.
- **Local docs**: For project-specific documentation, you can also add local markdown files by referencing them directly with `@filename.md` in chat.

---

## 📤 To Submit

- For credit: Submit screenshots showing:
  1. Your **Cursor Settings** → **Indexing & Docs** → **Docs** panel with both `httr2` and `requests` documentation added.
  2. A chat conversation where you used `@Docs httr2` or `@Docs requests` to get help with code.
  3. The resulting code file (either `test_httr2.R` or `test_requests.py`) that was generated with documentation assistance.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
