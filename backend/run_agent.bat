@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe src\agent.py dev
pause
