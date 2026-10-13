$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $repoRoot '.runtime'
foreach ($name in @('backend', 'frontend')) {
    $pidFile = Join-Path $runtimeDir "$name.pid"
    if (Test-Path -LiteralPath $pidFile) {
        $processId = [int](Get-Content -LiteralPath $pidFile)
        Stop-Process -Id $processId -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $pidFile -Force
    }
}
Write-Host 'NumeroFlix development services stopped.'

