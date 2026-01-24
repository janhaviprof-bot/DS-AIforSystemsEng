#!/bin/bash

# dependencies.sh

# Installs all R and Python dependencies for this repository
# Run this script from the project root: bash 00_quickstart/dependencies.sh

# --- SYSTEM DEPENDENCIES ---
# Python and R must be installed manually on Windows.
# Download Python: https://www.python.org/downloads/
# Download R: https://cran.r-project.org/bin/windows/base/
# (Recommended: Python 3.12, R 4.4.1)

# --- PYTHON DEPENDENCIES ---
# Resolve Python command
PYTHON_CMD=""
if command -v python &> /dev/null; then
  PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
  PYTHON_CMD="python3"
else
  PYTHON_CANDIDATE="$(ls -d "/c/Users/${USERNAME}/AppData/Local/Programs/Python/Python3"* 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$PYTHON_CANDIDATE" ] && [ -x "$PYTHON_CANDIDATE/python.exe" ]; then
    PYTHON_CMD="$PYTHON_CANDIDATE/python.exe"
  fi
fi

# Ensure python is available
if [ -n "$PYTHON_CMD" ]; then
  "$PYTHON_CMD" --version
else
  echo "⚠️ Python not found. Please install Python manually."
fi


# --- PIP INSTALLATION (if missing) ---
# Try to install pip if not found
if [ -n "$PYTHON_CMD" ] && ! "$PYTHON_CMD" -m pip --version &> /dev/null; then
  echo "⚠️ pip not found. Attempting to install pip..."
  # Download get-pip.py
  curl -O https://bootstrap.pypa.io/get-pip.py
  # Try to use python to install pip
  "$PYTHON_CMD" get-pip.py
  # Clean up
  rm get-pip.py
  # Re-check pip
  "$PYTHON_CMD" -m pip --version || echo "❌ pip installation failed. Please install pip manually: https://pip.pypa.io/en/stable/installation/"
else
  echo "✅ pip is already installed."
fi

# Ensure pip is available
if [ -n "$PYTHON_CMD" ]; then
  "$PYTHON_CMD" -m pip --version || echo "⚠️ pip not found. Please ensure pip is installed."
fi

# Install Python packages
if [ -n "$PYTHON_CMD" ]; then
  "$PYTHON_CMD" -m pip install --upgrade pip
  "$PYTHON_CMD" -m pip install fastapi uvicorn pydantic pandas requests matplotlib shiny
fi

# --- R DEPENDENCIES ---
# Resolve R command
R_CMD=""
if command -v R &> /dev/null; then
  R_CMD="R"
else
  R_HOME="$(ls -d "/c/Program Files/R/R-"* 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$R_HOME" ] && [ -x "$R_HOME/bin/R.exe" ]; then
    R_CMD="$R_HOME/bin/R.exe"
  fi
fi

# Ensure R is available
if [ -n "$R_CMD" ]; then
  "$R_CMD" --version
else
  echo "⚠️ R not found. Please install R manually."
fi

# Install R packages (run in R)
if [ -n "$R_CMD" ]; then
  if [[ -z "${R_LIBS_USER:-}" || "${R_LIBS_USER}" == *"/Users/tmf77/"* ]]; then
    R_VERSION="$(basename "$R_HOME" | sed 's/^R-//')"
    R_MAJOR_MINOR="$(echo "$R_VERSION" | cut -d. -f1-2)"
    export R_LIBS_USER="/c/Users/${USERNAME}/AppData/Local/R/win-library/${R_MAJOR_MINOR}"
  fi
  "$R_CMD" -q -e "if (nzchar(Sys.getenv('R_LIBS_USER')) && !dir.exists(Sys.getenv('R_LIBS_USER'))) dir.create(Sys.getenv('R_LIBS_USER'), recursive=TRUE); install.packages(c('shiny','plumber','jsonlite','httr','httr2','dplyr','readr','googlesheets4','ollamar','future','parallel','stringr','ggplot2'), repos=c(CRAN='https://packagemanager.posit.co/cran/latest'), lib=Sys.getenv('R_LIBS_USER'))"
fi

# --- DONE ---
echo "✅ All dependencies installation commands have been run. If you see errors above, please install Python and R manually first."

