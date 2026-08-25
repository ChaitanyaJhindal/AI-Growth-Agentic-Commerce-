@echo off
echo ======================================================================
echo   AURA - Starting Dedicated Embedding Microservice on Port 8001
echo ======================================================================

set PYTHONPATH=%CD%
python src\embedding_service.py
pause
