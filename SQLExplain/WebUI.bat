@echo off
title SQL Explain UI Launcher

echo Launching SQL Explain UI...
echo Please wait a few seconds.

REM Activate your venv if you have one
REM call venv\Scripts\activate

start "" streamlit run app_streamlit.py

timeout /t 3 >nul

echo Opening browser...
start "" http://localhost:8501

exit
