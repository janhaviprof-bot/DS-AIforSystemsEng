# 02_train_model.R
# Train XGBoost Model (Brussels Realtime)
# Tim Fraser

# Git bash: cd 12_end && Rscript 02_train_model.R
# Powershell: Set-Location 12_end; Rscript 02_train_model.R

# Goal: Train an ML XGBoost model to predict Brussels traffic volume
# from day of week and hour of day.
# Features:
# - day_of_week: 1-7 (1=Monday, 7=Sunday)
# - hour_of_day: 0-23 (0=12:00 AM, 23=11:00 PM)
# Label:
# - vehicles: number of vehicles observed at the monitor

# 0. SETUP ###################################

## 0.1 Load Packages #################################

library(DBI, quietly = TRUE, warn.conflicts = FALSE)
library(RSQLite, quietly = TRUE, warn.conflicts = FALSE)
library(dplyr, quietly = TRUE, warn.conflicts = FALSE)
library(lubridate, quietly = TRUE, warn.conflicts = FALSE)
library(xgboost, quietly = TRUE, warn.conflicts = FALSE)
library(jsonlite, quietly = TRUE, warn.conflicts = FALSE)

# 1. CONFIG ###################################

script_arg = commandArgs(trailingOnly = FALSE)
script_path = sub("^--file=", "", script_arg[grepl("^--file=", script_arg)][1])
script_dir = if (!is.na(script_path) && nzchar(script_path)) {
  dirname(normalizePath(script_path, winslash = "/", mustWork = FALSE))
} else {
  normalizePath("12_end", winslash = "/", mustWork = FALSE)
}
DB_PATH = file.path(script_dir, "data", "traffic.db")
DATA_DIR = file.path(script_dir, "data")
MODEL_PATH = file.path(DATA_DIR, "modelr.json")
VALIDATION_PATH = file.path(DATA_DIR, "validationr.json")
METRO_ID = 948

dir.create(DATA_DIR, showWarnings = FALSE, recursive = TRUE)

# 2. LOAD DATA ###################################

# Connect to the database
db = DBI::dbConnect(RSQLite::SQLite(), DB_PATH)

# Fetch the data from the database
df = DBI::dbGetQuery(
  conn = db,
  statement = "
  SELECT observed_at, vehicles
  FROM traffic
  WHERE metro_id = :metro_id
  ORDER BY observed_at
",
  params = list(metro_id = METRO_ID)
)

# Disconnect from the database
DBI::dbDisconnect(db)

# Check if the data is empty
if (nrow(df) == 0) stop("No rows found for configured METRO_ID.")

# 3. FEATURE ENGINEERING ###################################
# Convert the observed_at timestamp to a valid UTC timestamp
# Extract the day of week and hour of day
df = df %>%
  mutate(
    observed_at = lubridate::ymd_hms(observed_at, tz = "UTC", quiet = TRUE),
    day_of_week = lubridate::wday(observed_at, week_start = 1),
    hour_of_day = lubridate::hour(observed_at)
  )

# Define the features
features = c("day_of_week", "hour_of_day")

# 4. TRAIN/TEST SPLIT ###################################

# Split the data into training and test sets

df = df |> mutate(row_id = row_number())

# Randomly sample 80% of the data for training
train_df = df |> slice_sample(prop = 0.8)

# The remaining 20% is for testing
test_df = df |> anti_join(train_df |> select(row_id), by = "row_id")

# Drop row id
train_df = train_df |> select(-row_id)
test_df = test_df |> select(-row_id)

# Convert to matrices for training and testing
X_train = as.matrix(train_df[, features])
y_train = train_df$vehicles
X_test = as.matrix(test_df[, features])
y_test = test_df$vehicles

# 5. TRAIN MODEL ###################################

# Create the training data matrix
dtrain = xgboost::xgb.DMatrix(data = X_train, label = y_train)

# Train the model
model = xgboost::xgb.train(
  params = list(
    objective = "reg:squarederror",
    max_depth = 4,
    eta       = 0.1
  ),
  data    = dtrain,
  nrounds = 50,
  verbose = 0
)


# 6. EVALUATE ###################################

pred_train = predict(model, dtrain)
train_rmse = sqrt(mean((pred_train - y_train)^2))
train_r_squared = 1 - sum((y_train - pred_train)^2) / sum((y_train - mean(y_train))^2)

dtest = xgboost::xgb.DMatrix(data = X_test, label = y_test)
pred_test = predict(model, dtest)
test_rmse = sqrt(mean((pred_test - y_test)^2))
test_r_squared = 1 - sum((y_test - pred_test)^2) / sum((y_test - mean(y_test))^2)

test_residuals = y_test - pred_test
uncertainty_tbl = test_df |>
  transmute(
    day_of_week = as.integer(day_of_week),
    hour_of_day = as.integer(hour_of_day),
    residual = as.numeric(test_residuals)
  ) |>
  summarise(
    standard_error = sd(residual),
    n = n(),
    .by = c(day_of_week, hour_of_day)
  ) |>
  mutate(standard_error = if_else(is.na(standard_error), as.numeric(test_rmse), standard_error))

uncertainty_rows = lapply(seq_len(nrow(uncertainty_tbl)), function(i) {
  list(
    day_of_week = as.integer(uncertainty_tbl$day_of_week[[i]]),
    hour_of_day = as.integer(uncertainty_tbl$hour_of_day[[i]]),
    standard_error = as.numeric(uncertainty_tbl$standard_error[[i]]),
    n = as.integer(uncertainty_tbl$n[[i]])
  )
})

cat("Training RMSE:", round(train_rmse, 2), "\n")
cat("Training R-squared:", round(train_r_squared, 3), "\n")
cat("Testing RMSE:", round(test_rmse, 2), "\n")
cat("Testing R-squared:", round(test_r_squared, 3), "\n")


# 7. SAVE MODEL ###################################

xgboost::xgb.save(model, MODEL_PATH)

validation = list(
  metro_id = METRO_ID,
  test_rmse = as.numeric(test_rmse),
  test_r_squared = as.numeric(test_r_squared),
  train_rmse = as.numeric(train_rmse),
  train_r_squared = as.numeric(train_r_squared),
  residual_standard_error_default = as.numeric(test_rmse),
  standard_error_method = "Residual SD on held-out test split by day_of_week/hour_of_day; fallback to test RMSE.",
  standard_error_by_hour_day = uncertainty_rows
)
jsonlite::write_json(validation, VALIDATION_PATH, auto_unbox = TRUE, pretty = TRUE)

cat("\n====================================================\n")
cat("📋 02_train_model.R | Brussels realtime model\n")
cat("====================================================\n")
cat("   ✅ metro_id: ", METRO_ID, "\n", sep = "")
cat("   ✅ train rows (80%): ", nrow(train_df), "\n", sep = "")
cat("   ✅ test rows (20%): ", nrow(test_df), "\n", sep = "")
cat("   ✅ features: day_of_week, hour_of_day\n")
cat("   ✅ model saved to ", MODEL_PATH, "\n", sep = "")
cat("   ✅ validation saved to ", VALIDATION_PATH, "\n", sep = "")

