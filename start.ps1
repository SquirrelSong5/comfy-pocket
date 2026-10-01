param([switch]$Restart, [switch]$Open)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$settings = Get-Content -LiteralPath (Join-Path $projectRoot 'config.json') -Raw | ConvertFrom-Json
$pidFile = Join-Path $projectRoot 'state/server.pid'
if (Test-Path -LiteralPath $pidFile) {
    $serverProcessId = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$serverProcessId" -ErrorAction SilentlyContinue
    if ($existing -and $existing.CommandLine -match '-m backend\.server' -and $existing.ExecutablePath -eq $settings.python.Replace('/','\')) {
        if (!$Restart) { if ($Open) { Start-Process ('http://127.0.0.1:' + $settings.port) }; Write-Output 'Comfy Pocket is already running'; exit }
        Stop-Process -Id $serverProcessId
        Wait-Process -Id $serverProcessId -ErrorAction SilentlyContinue
    }
}
$service = Start-Process -FilePath $settings.python -ArgumentList '-m','backend.server' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'state/server.out.log') -RedirectStandardError (Join-Path $projectRoot 'state/server.err.log') -PassThru
$service.Id | Set-Content -LiteralPath $pidFile
if ($Open) { Start-Process ('http://127.0.0.1:' + $settings.port) }
Write-Output ('Comfy Pocket: http://127.0.0.1:' + $settings.port)
