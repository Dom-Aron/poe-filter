$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "======================================="
Write-Host " PoE Market Filter Toolkit"
Write-Host "======================================="
Write-Host ""

python (Join-Path $ScriptRoot "scripts/run_all.py")

Write-Host ""
Write-Host "Concluido. Veja os relatorios em market/reports/"
