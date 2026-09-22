# Windows equivalent of `make demo` (see Makefile / spec section 58).
# Run from the repo root: powershell -ExecutionPolicy Bypass -File scripts/demo.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot "backend\.venv"
$Py = Join-Path $Venv "Scripts\python.exe"

Write-Host "==> Installing backend dependencies" -ForegroundColor Cyan
if (-not (Test-Path $Venv)) {
    python -m venv $Venv
}
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $RepoRoot "backend\requirements.txt")

Write-Host "==> Installing frontend dependencies" -ForegroundColor Cyan
Push-Location (Join-Path $RepoRoot "frontend")
npm install
Pop-Location

Write-Host "==> Seeding synthetic demo corpus" -ForegroundColor Cyan
& $Py (Join-Path $RepoRoot "scripts\seed_demo_data.py")

Write-Host "==> Running demo ingestion (detect -> extract -> classify -> ontology -> chunk -> embed -> index)" -ForegroundColor Cyan
& $Py (Join-Path $RepoRoot "scripts\run_demo_ingestion.py")

Write-Host "==> Evaluating against the golden set" -ForegroundColor Cyan
& $Py (Join-Path $RepoRoot "scripts\evaluate.py")

Write-Host ""
Write-Host "Demo data ready." -ForegroundColor Green
Write-Host "Next: start the backend and frontend in two separate terminals:"
Write-Host "  cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Write-Host "  cd frontend; npm run dev"
Write-Host "Then open http://localhost:5173"
