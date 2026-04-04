# Reference: env and tool skeletons

Copy patterns into a **task folder** (not into this skill). Adjust names to match the student script.

## `.env.example` (commit this; no secrets)

```bash
# Ollama Cloud
OLLAMA_API_KEY=
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=nemotron-3-nano:30b-cloud

# Batching (example names—align with your script’s Sys.getenv()/os.getenv())
# ROWS_PER_BATCH=10
# CHUNK_WORKERS=1

# Optional: only if your provider accepts num_predict (omit if HTTP 400)
# MAX_OUTPUT_TOKENS=2048

# fixer_spatial_context.R only — override enriched CSV paths if needed
# FIXER_CONTEXT_PARCELS=output/parcels_enriched.csv
# FIXER_CONTEXT_POIS=output/pois_enriched.csv
```

## R — one tool definition (Ollama / OpenAI-style)

`parameters$properties` must be a **JSON object**. For **no** properties, use empty named list:

```r
tool_one = function() {
  list(
    list(
      type = "function",
      `function` = list(
        name = "record_fact",
        description = "Append one audited fact about a single row_id.",
        parameters = list(
          type = "object",
          properties = list(
            row_id = list(type = "integer", description = "Stable primary key."),
            field_name = list(type = "string", description = "Target column to update."),
            new_value = list(type = "string", description = "New cell text; empty string for missing.")
          ),
          required = list("row_id", "field_name", "new_value")
        )
      )
    )
  )
}
```

Single round with tools: build `messages`, then call your `ollama_chat_once(..., tools = tool_one())` (see [`10_data_management/fixer/functions.R`](../../../10_data_management/fixer/functions.R)).

## Python — one tool definition

```python
def tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "record_fact",
                "description": "Append one audited fact about a single row_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "row_id": {"type": "integer", "description": "Stable primary key."},
                        "field_name": {"type": "string", "description": "Target column."},
                        "new_value": {"type": "string", "description": "New text; empty for missing."},
                    },
                    "required": ["row_id", "field_name", "new_value"],
                },
            },
        }
    ]
```

POST body shape (non-streaming): `{"model": ..., "messages": ..., "stream": false, "tools": ...}`.
