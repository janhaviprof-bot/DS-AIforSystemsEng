# Same path convention as 08_function_calling/mcp_plumber/runme.R (repository root = getwd()).
# Tim Fraser
# Execute this script from bash using: Rscript 10_data_management/agentr/runme.R
plumber::plumb("10_data_management/agentr/plumber.R")$run(host = "0.0.0.0", port = 8001L)
