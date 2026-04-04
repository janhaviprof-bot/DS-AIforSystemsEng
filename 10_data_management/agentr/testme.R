# testme.R
# Smoke-test the deployed agent (Posit Connect or any public base URL)
# Tim Fraser
#
# Same pattern as agentpy/testme.py. Set AGENT_PUBLIC_URL in .env (repository root or agentr/).
#
# 0. SETUP ###################################

library(httr2)

readRenviron(".env")

# 1. REQUESTS ################################################################

base = trimws(Sys.getenv("AGENT_PUBLIC_URL", unset = ""))
base = sub("/$", "", base)
if (!nzchar(base)) {
  stop("Set AGENT_PUBLIC_URL in .env to your deployed base, e.g. https://connect.example.com/content/abc")
}

cat("# Smoke test at", base, "\n\n")

r1 = httr2::request(paste0(base, "/health")) |>
  httr2::req_timeout(30) |>
  httr2::req_perform()
cat("health:", httr2::resp_status(r1), "\n")
print(httr2::resp_body_json(r1, simplifyVector = TRUE))

body = list(
  task = paste0(
    "Training brief: incident 'Exercise Riverdale', River County, last 24h — ",
    "minimal situational sections; note if no live search."
  )
)

r2 = httr2::request(paste0(base, "/hooks/agent")) |>
  httr2::req_method("POST") |>
  httr2::req_headers("Content-Type" = "application/json") |>
  httr2::req_body_json(body) |>
  httr2::req_timeout(120) |>
  httr2::req_perform()

txt = httr2::resp_body_string(r2)
cat("agent:", httr2::resp_status(r2), substr(txt, 1L, min(500L, nchar(txt))), "\n")
