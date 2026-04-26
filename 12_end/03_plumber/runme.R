# runme.R
# Run the Brussels Plumber API locally.
# Tim Fraser
# Execute from repository root:
# Rscript 12_end/03_plumber/runme.R

plumber::plumb("12_end/03_plumber/plumber.R")$run(host = "0.0.0.0", port = 8000L)
