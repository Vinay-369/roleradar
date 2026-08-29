Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting RoleRadar AI Backend (Python 3.12) on port 8000..." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

py -3.12 -m uvicorn app.main:app --reload --port 8000
