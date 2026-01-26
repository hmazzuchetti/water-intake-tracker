@echo off
echo ================================
echo Building Water Intake Tracker
echo ================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Check if Pillow is installed (for icon conversion)
pip show Pillow >nul 2>&1
if errorlevel 1 (
    echo Installing Pillow...
    pip install Pillow
)

REM Convert icon if webp exists
if exist "icon.webp" (
    echo Converting icon.webp to icon.ico...
    python convert_icon.py
) else if exist "dist\icon.webp" (
    echo Converting dist\icon.webp to icon.ico...
    python convert_icon.py
)

echo.
echo Building executable...
echo.

REM Build using spec file if it exists
if exist "WaterIntakeTracker.spec" (
    pyinstaller WaterIntakeTracker.spec --noconfirm
) else (
    REM Fallback to command line build
    set ICON_ARG=
    if exist "icon.ico" set ICON_ARG=--icon=icon.ico

    pyinstaller ^
        --name=WaterIntakeTracker ^
        --onefile ^
        --windowed ^
        --add-data "sounds;sounds" ^
        --add-data "data;data" ^
        --add-data "models;models" ^
        --hidden-import=winsound ^
        --hidden-import=cv2 ^
        --hidden-import=mediapipe ^
        --hidden-import=PyQt5.sip ^
        --collect-all mediapipe ^
        %ICON_ARG% ^
        main.py
)

echo.
if exist "dist\WaterIntakeTracker.exe" (
    echo ================================
    echo BUILD SUCCESSFUL!
    echo ================================
    echo.
    echo Executable: dist\WaterIntakeTracker.exe
    echo.
    echo The exe is self-contained. Just share the WaterIntakeTracker.exe file.
    echo Models will be downloaded automatically on first run if not bundled.
) else (
    echo Build may have failed. Check the output above.
)

pause
