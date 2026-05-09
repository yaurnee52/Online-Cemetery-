# Остановка процесса на порту 8000 (Django runserver)
$ErrorActionPreference = "Stop"
$port = 8000

$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Write-Host "Порт $port свободен — сервер уже остановлен." -ForegroundColor Yellow
    exit 0
}

$pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $pids) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $label = if ($proc) { "$($proc.ProcessName) (PID $procId)" } else { "PID $procId" }
    Write-Host "Останавливаю $label ..."
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1
$still = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host "Не удалось освободить порт $port. Запустите PowerShell от администратора." -ForegroundColor Red
    exit 1
}

Write-Host "Сервер остановлен. Порт $port свободен." -ForegroundColor Green
