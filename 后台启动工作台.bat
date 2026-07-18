@echo off
cd /d "C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2"
start "" pythonw workbench_server.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765
exit