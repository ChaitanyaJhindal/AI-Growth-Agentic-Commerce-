@echo off
title AURA - AI-Native Luxury Fashion Concierge
echo =====================================================================
echo   AURA - AI Luxury Fashion Concierge ^& Agentic Commerce System
echo =====================================================================
echo.
echo Starting FastAPI Server ^& Web Application at http://127.0.0.1:8000...
echo.

:: Launch the browser automatically once the server is spinning up
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

:: Start the FastAPI backend which serves both API and Frontend
python server.py

pause
