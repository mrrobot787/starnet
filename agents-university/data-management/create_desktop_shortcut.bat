@echo off
REM Agent University Data Management System - Desktop Shortcut Creator
REM This batch file creates a desktop shortcut for easy access

echo Creating Agent University Data Management System desktop shortcut...

REM Get the current directory
set CURRENT_DIR=%~dp0

REM Create the shortcut using PowerShell
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Agent University Data Management.lnk'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '\"%CURRENT_DIR%launch_agent_university.py\"'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.Description = 'Agent University Data Management System - One-click data pipeline automation'; $Shortcut.Save()}"

if %ERRORLEVEL% EQU 0 (
    echo ✅ Desktop shortcut created successfully!
    echo.
    echo The shortcut "Agent University Data Management.lnk" has been created on your desktop.
    echo.
    echo You can now:
    echo   • Double-click the desktop shortcut to launch the GUI
    echo   • Initialize the system with one click
    echo   • Monitor data source scoring and governance
    echo   • Access all system features through the interface
    echo.
) else (
    echo ❌ Failed to create desktop shortcut.
    echo.
    echo Manual creation steps:
    echo 1. Right-click on desktop and select "New" → "Shortcut"
    echo 2. Enter target: python "%CURRENT_DIR%launch_agent_university.py"
    echo 3. Enter name: Agent University Data Management
    echo 4. Click Finish
    echo.
)

REM Also create a quick launch batch file
echo @echo off > "%CURRENT_DIR%quick_launch.bat"
echo cd /d "%CURRENT_DIR%" >> "%CURRENT_DIR%quick_launch.bat"
echo python launch_agent_university.py >> "%CURRENT_DIR%quick_launch.bat"
echo pause >> "%CURRENT_DIR%quick_launch.bat"

echo ✅ Quick launch batch file created: quick_launch.bat
echo.

REM Create system initialization batch file
echo @echo off > "%CURRENT_DIR%initialize_system.bat"
echo cd /d "%CURRENT_DIR%" >> "%CURRENT_DIR%initialize_system.bat"
echo echo Initializing Agent University Data Management System... >> "%CURRENT_DIR%initialize_system.bat"
echo python main_orchestrator.py init >> "%CURRENT_DIR%initialize_system.bat"
echo echo. >> "%CURRENT_DIR%initialize_system.bat"
echo echo System initialization complete! >> "%CURRENT_DIR%initialize_system.bat"
echo pause >> "%CURRENT_DIR%initialize_system.bat"

echo ✅ System initialization batch file created: initialize_system.bat
echo.

REM Create data source scoring batch file
echo @echo off > "%CURRENT_DIR%score_data_sources.bat"
echo cd /d "%CURRENT_DIR%" >> "%CURRENT_DIR%score_data_sources.bat"
echo echo Scoring and prioritizing data sources... >> "%CURRENT_DIR%score_data_sources.bat"
echo python main_orchestrator.py score >> "%CURRENT_DIR%score_data_sources.bat"
echo echo. >> "%CURRENT_DIR%score_data_sources.bat"
echo echo Data source scoring complete! >> "%CURRENT_DIR%score_data_sources.bat"
echo pause >> "%CURRENT_DIR%score_data_sources.bat"

echo ✅ Data source scoring batch file created: score_data_sources.bat
echo.

REM Create governance check batch file
echo @echo off > "%CURRENT_DIR%run_governance_checks.bat"
echo cd /d "%CURRENT_DIR%" >> "%CURRENT_DIR%run_governance_checks.bat"
echo echo Running governance and compliance checks... >> "%CURRENT_DIR%run_governance_checks.bat"
echo python main_orchestrator.py governance >> "%CURRENT_DIR%run_governance_checks.bat"
echo echo. >> "%CURRENT_DIR%run_governance_checks.bat"
echo echo Governance checks complete! >> "%CURRENT_DIR%run_governance_checks.bat"
echo pause >> "%CURRENT_DIR%run_governance_checks.bat"

echo ✅ Governance checks batch file created: run_governance_checks.bat
echo.

echo 🚀 Agent University Data Management System is ready!
echo.
echo Available launch options:
echo   • Desktop shortcut (GUI) - Full interactive interface
echo   • quick_launch.bat - Direct GUI launch
echo   • initialize_system.bat - One-click system setup
echo   • score_data_sources.bat - Data source prioritization
echo   • run_governance_checks.bat - Compliance monitoring
echo.
echo For command-line usage:
echo   python main_orchestrator.py [init^|score^|governance^|status]
echo.

pause
