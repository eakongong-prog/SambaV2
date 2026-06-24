@echo off
title SambaV2 Guan Li Hou Tai
color 0A

echo ==========================================================
echo          SambaV2 Guan Li Hou Tai - Qi Dong Zhong...
echo ==========================================================
echo.
echo  Hou Duan API : http://127.0.0.1:8800
echo  API Wen Dang : http://127.0.0.1:8800/api/docs
echo  Qian Duan Ye Mian : http://127.0.0.1:5173
echo.
echo  Zhang Hao : sys_admin
echo  Mi Ma : admin123
echo.
echo ==========================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting backend...
start "SambaV2-API" cmd /c "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8800"

echo [2/2] Starting frontend...
start "SambaV2-Frontend" cmd /c "cd frontend && npx vite --host 127.0.0.1 --port 5173"

echo.
echo ==========================================================
echo  Both services started. Opening browser...
echo ==========================================================

netsh interface portproxy delete v4tov4 listenport=8800 2>/dev/null
netsh interface portproxy delete v4tov4 listenport=5173 2>/dev/null

timeout /t 3 >/dev/null
start "" http://127.0.0.1:5173

pause
