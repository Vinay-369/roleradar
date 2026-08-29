@echo off
title RoleRadar AI Backend (Python 3.12)
cd /d "%~dp0"
echo ========================================================
echo Starting RoleRadar AI FastAPI Backend on port 8000...
echo Python version: 3.12
echo ========================================================
py -3.12 -m uvicorn app.main:app --reload --port 8000
pause
