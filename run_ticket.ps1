$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "generate_ticket.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python do ambiente virtual não encontrado em $pythonExe"
}

Push-Location $projectRoot
try {
    & $pythonExe $scriptPath
} finally {
    Pop-Location
}
