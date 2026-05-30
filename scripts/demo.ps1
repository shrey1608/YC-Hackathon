# FairBench end-to-end demo (Windows PowerShell).
# Runs the offline self-validating loop, then points you at the dashboard.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "== FairBench demo ==" -ForegroundColor Cyan
& $py -m fairbench.cli demo

Write-Host "`nOpen the dashboard:" -ForegroundColor Cyan
Write-Host "  cd dashboard; npm install; npm run dev   # http://localhost:3000"
