$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $repoRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

$backend = Start-Process -FilePath 'uv' -ArgumentList @('run', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden -PassThru
$frontend = Start-Process -FilePath 'npm' -ArgumentList @('run', 'dev') -WorkingDirectory (Join-Path $repoRoot 'frontend') -WindowStyle Hidden -PassThru
Set-Content -LiteralPath (Join-Path $runtimeDir 'backend.pid') -Value $backend.Id
Set-Content -LiteralPath (Join-Path $runtimeDir 'frontend.pid') -Value $frontend.Id
Write-Host "NumeroFlix started: API http://127.0.0.1:8000, UI http://localhost:5173"

