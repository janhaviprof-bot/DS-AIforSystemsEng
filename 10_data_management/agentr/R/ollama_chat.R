# R/ollama_chat.R
# Single-round Ollama /api/chat via httr2
# Tim Fraser

ollama_chat_once = function(
  base_url,
  api_key,
  model,
  messages,
  tools,
  max_output_tokens = NULL
) {
  url = paste0(sub("/$", "", base_url), "/api/chat")
  body = list(
    model = model,
    messages = messages,
    stream = FALSE,
    tools = tools
  )
  if (!is.null(max_output_tokens)) {
    body$options = list(num_predict = as.integer(max_output_tokens))
  }

  req = httr2::request(url) |>
    httr2::req_headers("Content-Type" = "application/json")
  ak = trimws(as.character(api_key %||% ""))
  if (nzchar(ak)) {
    req = req |> httr2::req_headers(Authorization = paste("Bearer", ak))
  }
  req = req |>
    httr2::req_body_json(body) |>
    httr2::req_timeout(120)

  resp = httr2::req_perform(req)
  data = httr2::resp_body_json(resp, simplifyVector = FALSE, simplifyDataFrame = FALSE)
  msg = data$message %||% list()
  content = msg$content
  if (is.null(content)) {
    content = ""
  }
  if (!is.character(content)) {
    content = as.character(content)
  }
  content = trimws(paste(content, collapse = ""))
  list(content = content, message = msg, raw = data)
}
