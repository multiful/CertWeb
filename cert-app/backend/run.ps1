# FastAPI 서버 실행 (가상환경 Python 사용)
# Cursor 터미널 등에서 venv가 활성화되지 않아도 동작합니다.
$venvPython = "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe"
$backendDir = $PSScriptRoot
Set-Location $backendDir
& $venvPython -m uvicorn main:app --reload
