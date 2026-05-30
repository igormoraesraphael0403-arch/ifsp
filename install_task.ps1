$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$powershellExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
$runnerPath = Join-Path $projectRoot "run_ticket.ps1"

if (-not (Test-Path $runnerPath)) {
    throw "Runner não encontrado em $runnerPath"
}

$action = New-ScheduledTaskAction -Execute $powershellExe -Argument "-ExecutionPolicy Bypass -File `"$runnerPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 9:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "SICA Ticket IFSP" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Gera o ticket do SICA em dias úteis às 09:00 e envia por email." `
    -Force

Write-Host "Tarefa agendada criada com sucesso."
