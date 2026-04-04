# 📌 ACTIVITY

## Run the CSV Fixer (R or Python + Ollama Cloud)

🕒 *Estimated Time: 10–15 minutes*

---

## 📋 Overview

You will run **[`fixer/fixer_csv.R`](fixer/fixer_csv.R)** *or* **[`fixer/fixer_csv.py`](fixer/fixer_csv.py)**, which gives an LLM **tools** to **`set_cell`** on a messy inventory table in **batches**: the script splits the table into chunks of **ROWS_PER_BATCH** rows (default **10**), sends **one** `/api/chat` per chunk with a shared **data-quality blurb** in the script, and the model returns many **`set_cell`** calls per chunk. Patches run on the main R process (**furrr** optional parallelism) or the main Python thread (**ThreadPoolExecutor** for chunk HTTP only; **`FIXER_CHUNK_WORKERS`**). Each successful edit is logged in **`fixer/output/fix_audit.jsonl`**. The raw teaching file in **`fixer/data/messy_inventory_raw.csv`** stays unchanged on disk (a working copy is written under **`fixer/output/messy_inventory_working.csv`**).

More detail: **[`fixer/README.md`](fixer/README.md)**.

---

## ✅ Your Task

### 🧱 Stage 1: Environment

- [ ] **R track:** Install **`dplyr`**, **`readr`**, **`httr2`**, **`jsonlite`**, **`future`**, **`furrr`** (see **[`fixer/README.md`](fixer/README.md)** for the full list used across fixer scripts).
- [ ] **Python track:** Install dependencies with **`pip install -r 10_data_management/fixer/requirements.txt`** (from repo root or the **`fixer/`** folder).
- [ ] Copy **[`fixer/.env.example`](fixer/.env.example)** to **`fixer/.env`** and set **`OLLAMA_API_KEY`** from [ollama.com](https://ollama.com). Keep **`OLLAMA_HOST`** and **`OLLAMA_MODEL`** aligned with the course default unless your instructor says otherwise. Use a model that supports **tool calling** on your host (see **`fixer/.env.example`**).
- [ ] From the **`dsai`** repository root, confirm **`fixer/data/messy_inventory_raw.csv`** exists (30 rows).

### 🧱 Stage 2: Run and verify

- [ ] **R:** Run **`Rscript 10_data_management/fixer/fixer_csv.R`** (from the repo root). The console should report **Chunks (API calls)** — for 30 rows and default **ROWS_PER_BATCH=10**, expect **3** chunks.
- [ ] **Python:** Run **`python 10_data_management/fixer/fixer_csv.py`**. Expect the same chunk count and the same **`output/`** artifacts as the R script.
- [ ] Open **`fixer/output/messy_inventory_working.csv`** and compare a few rows to the raw file.
- [ ] Open **`fixer/output/fix_audit.jsonl`** and read one line: identify **`row_id`**, **`column`**, **`old_value`**, and **`new_value`**.

---

# 📤 To Submit

- Screenshot of your terminal showing the script’s **summary** (chunk count and audit line count) or a clear success message.
- Screenshot of **one** parsed line (or pretty-printed object) from **`fixer/output/fix_audit.jsonl`** showing a real **`set_cell`** change.


---

## 💡 Building similar scripts (Cursor)

If you use **Cursor** with this repository, these **Agent Skills** under [`.cursor/skills/`](../.cursor/skills/) can help when you write your own batched Ollama + R workflows:

- **[`data-science-agent-loop`](../.cursor/skills/data-science-agent-loop/SKILL.md)** — short-lived agent loops: `.env`, batch size, tool schemas, main-process patches, and how this pattern differs from **`agentr`** / **`agentpy`**.
- **[`console-message`](../.cursor/skills/console-message/SKILL.md)** — clear console progress (section dividers, paths, row counts, previews) for debuggable runs.
- **[`tidyverse-elegant-r`](../.cursor/skills/tidyverse-elegant-r/SKILL.md)** — course R style: **`=`** assignment, native **`|>`**, explicit **`library()`**, **httr2**, dplyr 1.1+ idioms.
- **Python:** mirror the same agent-loop ideas with **pandas** chains, **`httpx`**, and **`geopandas`** where scripts touch maps (see **[`fixer/README.md`](fixer/README.md)**).


---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
