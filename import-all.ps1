# ==============================================================================
# TechQueue Interview Coach — Windows PowerShell Import Script
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Orch = Join-Path $ScriptDir "..\venv\Scripts\orchestrate.exe"

if (-not (Test-Path $Orch)) {
    $Orch = "orchestrate"
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " TechQueue Interview Coach - Importing to Orchestrate" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Importing Knowledge Base ..." -ForegroundColor Yellow
& $Orch knowledge-bases import -f (Join-Path $ScriptDir "knowledge_base\interview_knowledge_base.yaml")

Write-Host "`n[2/4] Importing Python Tools ..." -ForegroundColor Yellow
& $Orch tools import -k python -f (Join-Path $ScriptDir "tools\profile_tools.py")
& $Orch tools import -k python -f (Join-Path $ScriptDir "tools\evaluation_tools.py")

Write-Host "`n[3/4] Importing Flow Tool ..." -ForegroundColor Yellow
& $Orch tools import -k flow -f (Join-Path $ScriptDir "tools\interview_prep_flow.py")

Write-Host "`n[4/4] Importing Agent ..." -ForegroundColor Yellow
& $Orch agents import -f (Join-Path $ScriptDir "agents\techqueue_interview_coach.yaml")

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host " Import complete! Start chatting with TechQueue:" -ForegroundColor Green
Write-Host "   orchestrate chat start" -ForegroundColor White
Write-Host "   -> Select: techqueue_interview_coach" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Green
