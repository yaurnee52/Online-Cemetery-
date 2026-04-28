$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}

Write-Host "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Update DB credentials if needed."
  } else {
    Write-Host "WARNING: .env not found. Create it manually."
  }
}

Write-Host "Applying migrations..."
python manage.py migrate

Write-Host "Starting server at http://127.0.0.1:8000/"
python manage.py runserver
