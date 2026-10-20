@echo off 
cd /d "C:\closedloop_sissa_artifacts\DataManagement\" 
echo Initializing Agent University Data Management System... 
python main_orchestrator.py init 
echo. 
echo System initialization complete! 
pause 
