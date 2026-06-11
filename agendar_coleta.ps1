# ============================================================
# REGISTRO DA TAREFA AGENDADA — Amostra Acadêmica
# Agenda o executar_coleta.bat toda segunda-feira às 09:00
#
# Para registrar:   powershell -ExecutionPolicy Bypass -File agendar_coleta.ps1
# Para remover:     Unregister-ScheduledTask -TaskName "ColetaVagasDados" -Confirm:$false
# ============================================================

$NomeTarefa = "ColetaVagasDados"
$Projeto    = "C:\Users\User\Desktop\Amostra Acadêmica"
$Script     = "$Projeto\executar_coleta.bat"

# Remove versão anterior se existir
$existente = Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue
if ($existente) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa anterior removida."
}

# Ação: executar o .bat com cmd
$acao = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$Script`"" `
    -WorkingDirectory $Projeto

# Gatilho: toda segunda-feira às 09:00
$gatilho = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday `
    -At "09:00AM"

# Configurações
$config = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Registra rodando como o usuário atual (Chrome precisa de sessão ativa)
# RunLevel Limited = sem necessidade de admin, suficiente para abrir Chrome
Register-ScheduledTask `
    -TaskName  $NomeTarefa `
    -Action    $acao `
    -Trigger   $gatilho `
    -Settings  $config `
    -RunLevel  Limited `
    -Force

Write-Host ""
Write-Host "Tarefa '$NomeTarefa' registrada com sucesso!"
Write-Host "  Executa: toda segunda-feira as 09:00"
Write-Host "  Script : $Script"
Write-Host "  Logs   : $Projeto\logs\"
Write-Host ""
Write-Host "Para forcar uma execucao agora:"
Write-Host "  Start-ScheduledTask -TaskName '$NomeTarefa'"