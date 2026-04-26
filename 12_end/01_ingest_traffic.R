# 01_ingest_brussels_traffic_counts_realtime.R
# Ingest Brussels Realtime Traffic Counts (1m, t1)
# Tim Fraser
#
# This cron-friendly script fetches the latest traverse-level vehicle counts from
# the Brussels traffic API and stores normalized rows in SQLite.

# Run from inside the 12_end/ directory so the paths resolve correctly.
# Git bash: cd 12_end && Rscript 01_ingest_brussels_traffic_counts_realtime.R
# Powershell: Set-Location 12_end; Rscript 01_ingest_brussels_traffic_counts_realtime.R

# 0. SETUP ###################################

## 0.1 Load Packages #################################

library(httr2)
library(dplyr)
library(tibble)
library(purrr)
library(lubridate)
library(DBI)
library(RSQLite)

if (file.exists(".env")) readRenviron(".env")

# 1. CONFIG ###################################

# Brussels Traffic Vehicle Counts API Documentation here:
# https://data.mobility.brussels/traffic/api/counts/
BASE_URL = "https://data.mobility.brussels/traffic/api/counts/"
BRUSSELS_METRO_ID = 948
script_arg = commandArgs(trailingOnly = FALSE)
script_path = sub("^--file=", "", script_arg[grepl("^--file=", script_arg)][1])
script_dir = if (!is.na(script_path) && nzchar(script_path)) {
  dirname(normalizePath(script_path, winslash = "/", mustWork = FALSE))
} else {
  normalizePath("12_end", winslash = "/", mustWork = FALSE)
}
DATA_DIR = file.path(script_dir, "data")
DB_PATH = file.path(DATA_DIR, "traffic.db")

dir.create(DATA_DIR, showWarnings = FALSE, recursive = TRUE)

cat("\n====================================================\n")
cat("📋 01_ingest_brussels_traffic_counts_realtime.R\n")
cat("====================================================\n")
cat("   🧭 metro_id: ", BRUSSELS_METRO_ID, "\n", sep = "")
cat("   🔗 ", BASE_URL, "\n", sep = "")

# 2. FETCH DATA ###################################

resp = request(BASE_URL) |>
  req_url_query(request = "live", includeLanes = "false", interval = "1") |>
  req_perform()

if (resp_status(resp) != 200) {
  stop("Brussels traffic API failed with status ", resp_status(resp))
}

body = resp_body_json(resp, simplifyVector = FALSE)
if (is.null(body$data) || length(body$data) == 0) {
  stop("Brussels traffic API returned empty data payload")
}

monitors = names(body$data)
cat("   ✅ monitors in payload: ", length(monitors), "\n", sep = "")

# 3. CLEAN DATA ###################################

# Write a function to extract the data for each monitor
extract = function(monitor_id, monitor_payload) {
  one_min = monitor_payload$results[["1m"]]
  t1 = if (is.null(one_min) || is.null(one_min$t1)) list() else one_min$t1
  vehicles = if (is.null(t1$count)) NA else t1$count
  speed = if (is.null(t1$speed)) NA else t1$speed
  occupancy = if (is.null(t1$occupancy)) NA else t1$occupancy
  end_time_raw = if (is.null(t1$end_time)) "" else as.character(t1$end_time)

  tibble(
    monitor_id = monitor_id,
    vehicles = suppressWarnings(as.integer(vehicles)),
    speed = suppressWarnings(as.numeric(speed)),
    occupancy = suppressWarnings(as.numeric(occupancy)),
    observed_at_raw = end_time_raw
  )
}

# For each monitor, extract that monitor's data and bind as dataframe
raw_df = map2_dfr(
  .x = monitors, .y = body$data,
  .f = ~extract(monitor_id = .x, monitor_payload = .y) )

# Convert Brussels timestamp to a valid UTC timestamp
parse_bxl_time = function(x) {
  parsed = suppressWarnings(ymd_hm(x, tz = "Europe/Brussels", quiet = TRUE))
  ifelse(is.na(parsed), NA_character_, format(with_tz(parsed, "UTC"), "%Y-%m-%d %H:%M:%S"))
}

# Clean the data!
df = raw_df |>
  mutate(observed_at = parse_bxl_time(observed_at_raw)) |>
  filter(
    !is.na(vehicles),
    !is.na(observed_at),
    !is.na(monitor_id),
    monitor_id != ""
  ) |>
  mutate(speed = if_else(speed < 0, true = 0, false = speed)) |>
  transmute(
    metro_id = BRUSSELS_METRO_ID,
    monitor_id = monitor_id,
    observed_at = observed_at,
    vehicles = vehicles,
    speed = speed,
    occupancy = occupancy
  )

if (nrow(df) == 0) {
  stop("No valid 1m/t1 monitor rows parsed from Brussels API payload")
}

cat("   ✅ parsed rows: ", nrow(df), "\n", sep = "")
print(slice_head(df, n = 3))

# 4. WRITE TO SQLITE ###################################
# Keep database logic intentionally minimal and easy to read.

# Connect to/initialize the database
db = dbConnect(SQLite(), DB_PATH)

# Create the table if it doesn't exist
invisible(dbExecute(db, "
  CREATE TABLE IF NOT EXISTS traffic (
    metro_id    INTEGER,
    monitor_id  TEXT,
    observed_at TEXT,
    vehicles    INTEGER,
    speed       REAL,
    occupancy   REAL,
    PRIMARY KEY (metro_id, monitor_id, observed_at)
  )
"))

# Create a unique index on the table (will prevent duplicates)
invisible(dbExecute(
  db,
  "
  CREATE UNIQUE INDEX IF NOT EXISTS idx_traffic_metro_monitor_observed
  ON traffic (metro_id, monitor_id, observed_at)
"
))

before_count = dbGetQuery(
  db,
  "
  SELECT COUNT(*) AS n
  FROM traffic
  WHERE metro_id = :metro_id
",
  params = list(metro_id = BRUSSELS_METRO_ID)
)$n[[1]]

# Insert the data into the table
invisible(dbExecute(
  db,
  "
  INSERT INTO traffic (metro_id, monitor_id, observed_at, vehicles, speed, occupancy)
  VALUES (:metro_id, :monitor_id, :observed_at, :vehicles, :speed, :occupancy)
  ON CONFLICT(metro_id, monitor_id, observed_at) DO NOTHING
",
  params = df
))

# Check total rows
total_rows = dbGetQuery(
  db,
  "
  SELECT COUNT(*) AS n
  FROM traffic
  WHERE metro_id = :metro_id
",
  params = list(metro_id = BRUSSELS_METRO_ID)
)$n[[1]]
inserted_rows = max(total_rows - before_count, 0)

# Disconnect from the database
dbDisconnect(db)

# 5. VERIFY ###################################
cat("   ✅ candidate rows this run: ", nrow(df), "\n", sep = "")
cat("   ✅ new rows appended: ", inserted_rows, "\n", sep = "")
cat("   ✅ total rows (metro): ", total_rows, "\n", sep = "")


# That's it! You've made a script that you can run manually or via CRON 
# to ingest the latest Brussels traffic counts into a SQLite database.




