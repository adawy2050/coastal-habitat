$ErrorActionPreference = 'Stop'
$atlasRoot = $PSScriptRoot
$pythonPath = (Get-Command python).Source
$cachePath = Join-Path $atlasRoot '_cache'
New-Item -ItemType Directory -Path $cachePath -Force | Out-Null
foreach ($task in @(@{ Name='atlas-publish-2026'; Script='scripts/finish_observed2026_update.py' })) {
    $pidFile = Join-Path $cachePath ($task.Name + '.pid')
    if (Test-Path -LiteralPath $pidFile) {
        $existingId = [int](Get-Content -LiteralPath $pidFile)
        $existingProcess = Get-Process -Id $existingId -ErrorAction SilentlyContinue
        if ($existingProcess) { Write-Host ($task.Name + ' is running as ' + $existingId); continue }
    }
    $started = Start-Process -FilePath $pythonPath -ArgumentList @('-u', $task.Script) -WorkingDirectory $atlasRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $cachePath ($task.Name + '.log')) -RedirectStandardError (Join-Path $cachePath ($task.Name + '.error.log')) -PassThru
    Set-Content -LiteralPath $pidFile -Value $started.Id
    Write-Host ($task.Name + ' started as ' + $started.Id)
}
Write-Host 'Progress: https://adawy2050.github.io/coastal-habitat/status/'
