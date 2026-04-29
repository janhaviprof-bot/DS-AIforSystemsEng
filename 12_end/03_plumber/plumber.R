# plumber.R
# Plumber REST Endpoint (Brussels Realtime)
# Pairs with fastapi/main.py
# Tim Fraser

library(plumber)
library(xgboost)
library(jsonlite)

# Build a short list of candidate model locations so the API works
# whether it is launched from repo root or from inside 12_end.
model_candidates = c(
  "data/modelr.json",
  "12_end/data/modelr.json",
  "../data/modelr.json"
)

validation_candidates = c(
  "data/validationr.json",
  "12_end/data/validationr.json",
  "../data/validationr.json"
)

resolve_first_path = function(candidates, label) {
  resolved = candidates[file.exists(candidates)][1]
  if (is.na(resolved)) stop("Could not find ", label, ". Checked: ", paste(candidates, collapse = ", "))
  resolved
}

model_path = resolve_first_path(model_candidates, "modelr.json")
validation_path = resolve_first_path(validation_candidates, "validationr.json")

model = xgboost::xgb.load(model_path)
validation = jsonlite::fromJSON(validation_path, simplifyVector = TRUE)

default_standard_error = if (!is.null(validation$residual_standard_error_default)) {
  as.numeric(validation$residual_standard_error_default)
} else {
  as.numeric(validation$test_rmse)
}

se_lookup = list()
if (!is.null(validation$standard_error_by_hour_day)) {
  se_rows = validation$standard_error_by_hour_day
  for (i in seq_len(nrow(se_rows))) {
    key = paste0(as.integer(se_rows$day_of_week[[i]]), "-", as.integer(se_rows$hour_of_day[[i]]))
    se_lookup[[key]] = as.numeric(se_rows$standard_error[[i]])
  }
}

#* Predict Brussels traffic volume from day and hour
#* @param day_of_week int Day of week (1=Monday, ..., 7=Sunday)
#* @param hour_of_day int Hour of day (0-23)
#* @get /predict
function(day_of_week, hour_of_day) {
  mat = xgboost::xgb.DMatrix(
    matrix(
      as.numeric(c(day_of_week, hour_of_day)),
      nrow = 1,
      dimnames = list(NULL, c("day_of_week", "hour_of_day"))
    )
  )
  key = paste0(as.integer(day_of_week), "-", as.integer(hour_of_day))
  se = if (!is.null(se_lookup[[key]])) se_lookup[[key]] else default_standard_error
  list(
    predicted_vehicle_count = round(predict(model, mat), 1),
    standard_error = round(as.numeric(se), 3),
    standard_error_method = validation$standard_error_method
  )
}

#* Return saved model validation metrics
#* @get /validation
function() {
  list(
    metro_id = validation$metro_id,
    test_rmse = validation$test_rmse,
    test_r_squared = validation$test_r_squared,
    train_rmse = validation$train_rmse,
    train_r_squared = validation$train_r_squared
  )
}
