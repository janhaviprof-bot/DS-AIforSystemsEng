#!/bin/bash

# Local .bashrc for this repository
# This file contains project-specific bash configurations

# Add LM Studio to PATH for this project (auto-detect)
WIN_USER="${WIN_USER:-$USERNAME}"
WIN_HOME="/c/Users/${WIN_USER}"
clean_path() {
  local IFS=':'
  local parts=($PATH)
  local new=()
  local p
  for p in "${parts[@]}"; do
    case "$p" in
      /c/Python312|/c/Users/tmf77/*|/c/Program\ Files/R/R-4.4.1/bin) continue ;;
      *) new+=("$p") ;;
    esac
  done
  PATH=$(IFS=:; echo "${new[*]}")
}
path_prepend() {
  case ":$PATH:" in
    *":$1:"*) ;;
    *) PATH="$1:$PATH" ;;
  esac
}
path_append() {
  case ":$PATH:" in
    *":$1:"*) ;;
    *) PATH="$PATH:$1" ;;
  esac
}

clean_path

LM_STUDIO_HOME="$WIN_HOME/.lmstudio/bin"
if [ -d "$LM_STUDIO_HOME" ]; then
  path_append "$LM_STUDIO_HOME"
  alias lms="$LM_STUDIO_HOME/lms.exe"
fi

OLLAMA_HOME="$WIN_HOME/AppData/Local/Programs/Ollama"
if [ -d "$OLLAMA_HOME" ]; then
  path_append "$OLLAMA_HOME"
  alias ollama="$OLLAMA_HOME/ollama.exe"
fi

# Add R to your Path for this project (auto-detect latest)
unalias R 2>/dev/null
unalias Rscript 2>/dev/null
R_HOME="$(ls -d "/c/Program Files/R/R-"* 2>/dev/null | sort -V | tail -n 1)"
if [ -n "$R_HOME" ] && [ -d "$R_HOME/bin" ]; then
  path_prepend "$R_HOME/bin"
  R() { "$R_HOME/bin/R.exe" "$@"; }
  Rscript() { "$R_HOME/bin/Rscript.exe" "$@"; }
fi
# Add R libraries to your path for this project (auto-detect latest)
R_VERSION=""
if [ -n "$R_HOME" ]; then
  R_VERSION="$(basename "$R_HOME" | sed 's/^R-//')"
fi
R_MAJOR_MINOR=""
if [ -n "$R_VERSION" ]; then
  R_MAJOR_MINOR="$(echo "$R_VERSION" | cut -d. -f1-2)"
fi
R_LIBS_USER_CANDIDATE="$(ls -d "$WIN_HOME/AppData/Local/R/win-library/"* 2>/dev/null | sort -V | tail -n 1)"
if [[ -z "${R_LIBS_USER:-}" || "${R_LIBS_USER}" == *"/Users/tmf77/"* ]]; then
  if [ -n "$R_MAJOR_MINOR" ]; then
    export R_LIBS_USER="$WIN_HOME/AppData/Local/R/win-library/$R_MAJOR_MINOR"
  elif [ -n "$R_LIBS_USER_CANDIDATE" ]; then
    export R_LIBS_USER="$R_LIBS_USER_CANDIDATE"
  fi
fi

# Add Python to your Path for this project (auto-detect latest)
unalias python 2>/dev/null
PYTHON_HOME="$(ls -d "$WIN_HOME/AppData/Local/Programs/Python/Python3"* 2>/dev/null | sort -V | tail -n 1)"
if [ -n "$PYTHON_HOME" ] && [ -d "$PYTHON_HOME" ]; then
  path_prepend "$PYTHON_HOME"
  alias python="$PYTHON_HOME/python.exe"
fi

# Add Python Scripts to PATH (auto-detect latest)
PYTHON_SCRIPTS_LOCAL="$(ls -d "$WIN_HOME/AppData/Local/Programs/Python/Python3"*/Scripts 2>/dev/null | sort -V | tail -n 1)"
if [ -n "$PYTHON_SCRIPTS_LOCAL" ] && [ -d "$PYTHON_SCRIPTS_LOCAL" ]; then
  path_prepend "$PYTHON_SCRIPTS_LOCAL"
fi
PYTHON_SCRIPTS="$(ls -d "$WIN_HOME/AppData/Roaming/Python/Python"*/Scripts 2>/dev/null | sort -V | tail -n 1)"
if [ -n "$PYTHON_SCRIPTS" ] && [ -d "$PYTHON_SCRIPTS" ]; then
  path_prepend "$PYTHON_SCRIPTS"
fi

echo "✅ Local .bashrc loaded."