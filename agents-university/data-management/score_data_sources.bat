@echo off 
cd /d "C:\closedloop_sissa_artifacts\DataManagement\" 
echo Scoring and prioritizing data sources... 
python main_orchestrator.py score 
echo. 
echo Data source scoring complete! 
pause 
