$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvPip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"

# Проверяем готовое venv по python.exe, а не по папке (иначе пустой .venv ломает запуск)
if (-not (Test-Path $venvPython)) {
  Write-Host "Creating virtual environment..."
  if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
  }
  python -m venv .venv
}

Write-Host "Installing dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPip install -r requirements.txt

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Update DB credentials if needed."
  } else {
    Write-Host "WARNING: .env not found. Create it manually."
  }
}

Write-Host "Applying migrations..."
& $venvPython manage.py migrate

Write-Host "Starting server at http://127.0.0.1:8000/"
Write-Host "Stop: Ctrl+C in this window, or .\stop-dev.ps1 | Status: .\dev-status.ps1"
& $venvPython manage.py runserver
