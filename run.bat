@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .env (
  echo [안내] .env 파일이 없어서 코치 채팅은 꺼진 상태로 실행됩니다. 통계/온도/썸 신호는 정상 동작합니다.
  set ANTHROPIC_API_KEY=dummy
)
set PYTHONIOENCODING=utf-8
start "kakao-coach backend" cmd /k ".venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000"
start "kakao-coach frontend" cmd /k "cd frontend && npm run dev"
timeout /t 4 >nul
start http://localhost:5173
