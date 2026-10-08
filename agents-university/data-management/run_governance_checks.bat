@echo off 
cd /d "C:\closedloop_sissa_artifacts\DataManagement\" 
echo Running governance and compliance checks... 
python main_orchestrator.py governance 
echo. 
echo Governance checks complete! 
pause 
