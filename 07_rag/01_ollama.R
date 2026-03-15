# 01_ollama.R - Launch Ollama from R
# Pairs with 01_ollama.sh. Starts ollama serve in the background with system2.
# Tim Fraser

# Configuration (match 01_ollama.sh)
PORT = 11434L
OLLAMA_HOST = paste0("0.0.0.0:", PORT)
OLLAMA_CONTEXT_LENGTH = 32000L

# Set env for this R process and any child processes (e.g. system2).
Sys.setenv(OLLAMA_HOST = OLLAMA_HOST, OLLAMA_CONTEXT_LENGTH = as.character(OLLAMA_CONTEXT_LENGTH))

# Start ollama serve in the background. wait = FALSE so R does not block.
# stdout/stderr go to null so the console is not flooded.
system2("ollama", "serve", stdout = FALSE, stderr = FALSE, wait = FALSE)

# Optional: give the server a moment to bind before using it.
Sys.sleep(1)

# To stop the server later (run in R or in a separate script):
#   system2("pkill", c("-f", "ollama serve"), stdout = FALSE, stderr = FALSE)
# Or on Windows: system("taskkill /F /IM ollama.exe", ignore.stderr = TRUE)
