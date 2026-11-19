param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'dist')
Write-Host "Open http://localhost:$Port in your browser. Press Ctrl+C to stop."
python -m http.server $Port --bind 127.0.0.1
