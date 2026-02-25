# FastAPI 서버 실행 (가상환경 Python 사용)
# Cursor에서 이 venv 연결: Ctrl+Shift+P → "Python: Select Interpreter" → 위 경로의 python.exe 선택
# 터미널에서 venv 미활성화 상태여도 이 스크립트는 동작합니다.
$venvPython = "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe"
$backendDir = $PSScriptRoot
Set-Location $backendDir
& $venvPython -m uvicorn main:app --reload
