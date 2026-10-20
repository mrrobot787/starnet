@echo off
echo ========================================================
echo   Creating AML University Training Hospital Shortcut
echo ========================================================
echo.

REM Get the current directory
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

REM Get desktop path
for /f "tokens=2*" %%i in ('reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop') do set "DESKTOP=%%j"

echo Project Directory: %PROJECT_DIR%
echo Desktop Path: %DESKTOP%
echo.

REM Create shortcut using PowerShell
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\AML University Training Hospital.lnk'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\""%PROJECT_DIR%\aml_university_launcher.py\""'; $Shortcut.WorkingDirectory = '%PROJECT_DIR%'; $Shortcut.Description = 'AML University Training Hospital - Domain Pack Teaching System'; $Shortcut.IconLocation = 'imageres.dll,185'; $Shortcut.Save()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   ✅ Desktop shortcut created successfully!
    echo ========================================================
    echo.
    echo You can now double-click "AML University Training Hospital"
    echo on your desktop to launch the complete system.
    echo.
    echo Features:
    echo   • 🎓 Domain Pack Dashboard
    echo   • 🏥 Agent Health Monitoring
    echo   • 📊 Unified Analytics Hub
    echo   • 🧪 Testing Tools
    echo   • 📝 Live System Logs
    echo.
) else (
    echo.
    echo ❌ Error creating shortcut!
    echo Please run this script as Administrator.
    echo.
)

pause

