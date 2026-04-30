$ErrorActionPreference = "Stop"
# deployme.ps1 — same as deployme.sh, for PowerShell (no Bash/WSL).
# Requires .env in this folder with CONNECT_SERVER and CONNECT_API_KEY.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File 12_end/03_fastapi/deployme.ps1

Set-Location $PSScriptRoot

if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -notmatch "=") {
      return
    }
    $parts = $_ -split "=", 2
    $name = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    if ($name) {
      Set-Item -Path "Env:$name" -Value $value
    }
  }
}

if (-not $env:CONNECT_SERVER -or -not $env:CONNECT_API_KEY) {
  throw "Set CONNECT_SERVER and CONNECT_API_KEY in .env (see .env.example) or in the environment before deploying."
}

python -m pip install -q rsconnect-python
$title = if ($env:CONNECT_TITLE) {
  $env:CONNECT_TITLE
} else {
  "brussels-traffic-fastapi"
}
rsconnect deploy fastapi --title $title --server $env:CONNECT_SERVER --api-key $env:CONNECT_API_KEY --entrypoint main:app .
