@echo off
chcp 65001 >nul
title TEMU Auto Publish Workbench

echo ========================================
echo   TEMU full auto publish workbench
echo ========================================
echo.

cd /d "C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"

echo Starting local service...
echo Workbench will open in browser automatically
echo.
echo DO NOT CLOSE this window while using workbench
echo ========================================
echo.

python workbench_server.py

pause
