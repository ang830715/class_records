$ErrorActionPreference = "Stop"

function Test-Url($url) {
  try {
    Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 2 | Out-Null
    return $true
  } catch {
    return $false
  }
}

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$logDir = Join-Path $root ".dev-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path -Path $python)) {
  Push-Location $backend
  try {
    python -m venv .venv
    & $python -m pip install -r requirements.txt
  } finally {
    Pop-Location
  }
}

if (-not (Test-Path -Path (Join-Path $frontend "node_modules"))) {
  Push-Location $frontend
  try {
    npm.cmd install
  } finally {
    Pop-Location
  }
}

if (Test-Url "http://localhost:8000/health") {
  Write-Host "Backend already running: http://localhost:8000"
} else {
  $backendDb = (Join-Path $backend "dev.db").Replace("\", "/")
  $backendCommand = "`$env:DATABASE_URL='sqlite:///$backendDb'; & '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
  $backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "backend.out.log") -RedirectStandardError (Join-Path $logDir "backend.err.log") -PassThru
  $backendProcess.Id | Set-Content -Path (Join-Path $logDir "backend.pid")
  Write-Host "Started backend: http://localhost:8000"
}

if (Test-Url "http://localhost:5173") {
  Write-Host "Frontend already running: http://localhost:5173"
} else {
  $frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") -WorkingDirectory $frontend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "frontend.out.log") -RedirectStandardError (Join-Path $logDir "frontend.err.log") -PassThru
  $frontendProcess.Id | Set-Content -Path (Join-Path $logDir "frontend.pid")
  Write-Host "Started frontend: http://localhost:5173"
}

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Backend:  http://localhost:8000"
Write-Host "API docs: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:5173"
Write-Host "Database: backend/dev.db"
Write-Host "Logs:     $logDir"
