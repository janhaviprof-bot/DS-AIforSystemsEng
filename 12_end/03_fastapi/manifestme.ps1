$ErrorActionPreference = "Stop"
# manifestme.ps1 — same as manifestme.sh, for PowerShell (no Bash/WSL).
# Run from repo root: powershell -NoProfile -ExecutionPolicy Bypass -File 12_end/03_fastapi/manifestme.ps1
# Or from this folder: .\manifestme.ps1

Set-Location $PSScriptRoot
python -m pip install -q rsconnect-python
rsconnect write-manifest fastapi --entrypoint main:app --overwrite .
