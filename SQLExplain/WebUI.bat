@echo off
title SQL Explain - Setup and Run

echo ==========================================
echo  Automatic SQL Explain UI Launcher
echo  - Creates virtual env (if needed)
echo  - Installs dependencies
echo  - Starts Streamlit UI
echo ==========================================
echo.

REM ---- 1. Check Python ----
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM ---- 2. Set venv directory ----
set VENV_DIR=venv

REM ---- 3. Create venv if not exists ----
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creating virtual environment in "%VENV_DIR%" ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [INFO] Upgrading pip ...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip

    echo [INFO] Installing dependencies from requirements.txt ...
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment already exists. Skipping setup.
)

REM ---- 4. Start Streamlit UI ----
echo.
echo [INFO] Starting Streamlit app...
start "" "%VENV_DIR%\Scripts\python.exe" -m streamlit run app_streamlit.py

REM ---- 5. Wait a bit and open browser ----
echo [INFO] Waiting for server to start...
timeout /t 4 >nul

echo [INFO] Opening browser at http://localhost:8501 ...
start "" http://localhost:8501

echo.
echo [DONE] SQL Explain UI should now be running in your browser.
echo Close this window if you don't need logs.
pause
