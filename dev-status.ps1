# Проверка: запущен ли dev-сервер Django на порту 8000
$ErrorActionPreference = "Continue"
$port = 8000

Write-Host "Проверка порта $port (Django runserver)..." -ForegroundColor Cyan

$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Write-Host "Сервер НЕ запущен: порт $port свободен." -ForegroundColor Yellow
    Write-Host "Запуск: .\run-dev.ps1"
    exit 1
}

foreach ($conn in $listeners) {
    $procId = $conn.OwningProcess
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $name = if ($proc) { $proc.ProcessName } else { "?" }
    Write-Host "Сервер ЗАПУЩЕН: PID $procId ($name), http://127.0.0.1:$port/" -ForegroundColor Green
}

try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 3
    Write-Host "HTTP ответ: $($resp.StatusCode) — это наш Django, а не кэш браузера." -ForegroundColor Green
} catch {
    Write-Host "Порт занят, но HTTP не отвечает: $($_.Exception.Message)" -ForegroundColor Red
}

exit 0
