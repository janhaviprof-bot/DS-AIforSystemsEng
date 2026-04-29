# testme.R
# Smoke-test the Brussels Plumber prediction endpoint.
# Tim Fraser
# Rscript 12_end/03_plumber/testme.R

# Load packages and vars
library(httr2)
readRenviron(".env")

# Set base URL
base = trimws(Sys.getenv("API_PUBLIC_URL", unset = "http://localhost:8000"))
# Remove trailing slash if present
base = sub("/$", "", base)

# Send request
r = httr2::request(paste0(base, "/predict")) |>
  httr2::req_url_query(day_of_week = 1, hour_of_day = 8) |>
  httr2::req_timeout(30) |>
  httr2::req_perform()

# Print response
cat("status:", httr2::resp_status(r), "\n")
print(httr2::resp_body_json(r, simplifyVector = TRUE))
