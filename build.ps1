$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'web')
try { npm run build; if ($LASTEXITCODE -ne 0) { throw 'Build failed' } } finally { Pop-Location }
$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
& $config.python (Join-Path $PSScriptRoot 'scripts/compress.py')
