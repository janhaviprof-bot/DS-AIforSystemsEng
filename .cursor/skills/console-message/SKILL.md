---
name: console-message
description: Adds clear console progress and status output for R and Python scripts using section dividers, Unicode emoji icons, dimensions (nrow/length), paths, and previews so runs are debuggable from logs pasted into AI chats. Use when polishing scripts, improving observability, or when the user asks for progress messages, status lines, or emoji console UX.
---

# Console messaging for R and Python scripts

## Goal

End each script with **human-readable, machine-parseable** console output: what step ran, row counts, file paths, and quick previews. Logs should be useful when pasted into an AI assistant for debugging.

## Patterns (both languages)

1. **Banner** — Top-level title in a heavy rule line (`====` or `----`).
2. **Steps** — Numbered or named phases with a horizontal rule before each (`Step 1 — Load data`).
3. **Status line** — One line per sub-action: leading emoji + short label + key fact (`✅ Loaded 30 rows × 5 cols`).
4. **Indents** — Use 3 spaces after top-level cats so nested detail reads as a tree (`   ✅`, `      ✏️`).
5. **Paths** — Print full or workspace-relative paths on their own lines when I/O matters.
6. **Dimensions** — After every load or split: `nrow`, `ncol`, `length`, chunk counts.
7. **Previews** — `head`, `str`, or first 80 chars of text for sanity checks (small tables only).
8. **Summary block** — Final boxed list: artifacts written, counts, config (workers, batch size).
9. **Failures** — On errors, print HTTP status, response snippet, or `conditionMessage` when safe (no secrets).

## Emoji palette (intuitive, not exotic)

Use **plain Unicode emoji** in source (not `\U000` escapes). Prefer familiar symbols:

| Meaning | Emoji | Example |
|--------|-------|---------|
| Script / document | 📋 | Script title line |
| Packages | 📦 | Loading libraries |
| Folder / paths | 📁 📄 💾 📝 | Paths, CSV, audit |
| Cloud / API | ☁️ | Remote model call |
| OK / done | ✅ | Step succeeded |
| Work / tools | 🔧 ✏️ 💾 | Tool dispatch, writes |
| Warning | ⚠️ | Empty tool list |
| Error | ❌ | HTTP or fatal |
| Split / chunk | ✂️ 📦 | Batching |
| Map / geo | 🗺️ 🌍 | GIS |
| Chart | 🎨 🖼️ | Plots saved |
| Summary | 📊 | Final counts |

Stay consistent within one repo; avoid rare symbols that render as tofu in some terminals.

## R specifics

- Use **`cat(..., sep = "")`** for controlled newlines; **`message()`** if you want timestamp prefix.
- **`print(dplyr::slice_head(df, n))`** or **`utils::head()`** for tibble previews.
- After **`readr::read_csv`**: report **`nrow`**, **`ncol`**, then preview.
- For **`purrr` / `furrr`**: log **`workers`**, **`n_chunks`**, then per-chunk tool counts.
- Keep **`=`** assignment if that is the project standard.

## Python specifics

- Prefer **`print(f"...")`** with same structure; optional **`logging`** for libraries.
- After **`pandas.read_csv`**: **`len(df)`**, **`df.shape`**, **`df.head(3)`**.
- Use the same emoji palette; avoid ANSI color unless the project already standardizes it.

## Anti-patterns

- Flooding the console every iteration of a tight loop (sample or throttle).
- Printing secrets (API keys, tokens); mask like `abcd...wxyz`.
- Dumping entire large tables.

## Checklist before merge

- [ ] Banner + step sections for the main phases
- [ ] Row/column or length counts after loads and splits
- [ ] Output paths printed when files are written
- [ ] Final summary block with paths and totals
- [ ] Emoji set is readable and consistent
