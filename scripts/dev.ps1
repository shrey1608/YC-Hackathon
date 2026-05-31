<#
  FairBench dev launcher (Windows / PowerShell).
  Starts the FastAPI control-plane on :8000 (separate window) and the Next.js
  dashboard on :3000 (this window). Ctrl-C stops the dashboard; close the other
  window to stop the API.

  Usage:  ./scripts/dev.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "FairBench dev -> API http://localhost:8000  |  dashboard http://localhost:3000" -ForegroundColor Cyan

# --- backend (:8000) in its own window ---
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Start-Process -FilePath $py -ArgumentList "-m", "fairbench.server.app" -WorkingDirectory $root
Write-Host "backend starting (separate window)..." -ForegroundColor DarkGray

# --- frontend (:3000) in this window ---
$dash = Join-Path $root "dashboard"
if (-not (Test-Path (Join-Path $dash "node_modules"))) {
    Write-Host "installing dashboard deps..." -ForegroundColor Yellow
    Push-Location $dash; npm install; Pop-Location
}
Push-Location $dash
try {
    npm run dev
}
finally {
    Pop-Location
}
