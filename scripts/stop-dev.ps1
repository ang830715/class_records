$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root ".dev-logs"

foreach ($name in @("backend", "frontend")) {
  $pidFile = Join-Path $logDir "$name.pid"
  if (Test-Path -Path $pidFile) {
    $processId = Get-Content -Path $pidFile -ErrorAction SilentlyContinue
    if ($processId) {
      taskkill.exe /PID $processId /T /F | Out-Null
      Write-Host "Stopped $name process tree $processId"
    }
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "No saved PID for $name"
  }
}
