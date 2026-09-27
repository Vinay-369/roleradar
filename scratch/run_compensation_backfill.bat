@echo off
REM Compensation Data Backfill Script for Windows
REM Run this to fix missing salary and stipend data in jobs and internships

echo.
echo ========================================
echo COMPENSATION DATA BACKFILL
echo ========================================
echo.

cd /d "%~dp0backend"

echo Step 1: Testing compensation extraction logic...
python "..\scratch\test_compensation_extraction.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compensation extraction test failed
    pause
    exit /b 1
)

echo.
echo Step 2: Checking database connection...
python "..\scratch\check_db_connection.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Cannot connect to MongoDB. Please ensure MongoDB is running.
    pause
    exit /b 1
)

echo.
echo Step 3: Running compensation backfill...
python "..\scratch\backfill_compensation_data.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backfill failed
    pause
    exit /b 1
)

echo.
echo Step 4: Running diagnostic to verify results...
python "..\scratch\diagnose_compensation_missing.py"

echo.
echo ========================================
echo BACKFILL COMPLETE
echo ========================================
echo.
pause
