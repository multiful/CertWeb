# 실시간 동작 확인 스크립트 (백엔드가 이미 실행 중일 때)
# 사용: .\scripts\verify_runtime.ps1   또는  powershell -File scripts\verify_runtime.ps1
# 전제: cert-app\backend 에서 uvicorn main:app --reload 로 서버 실행 후, 다른 터미널에서 실행

# 한글 출력 깨짐 방지
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$base = "http://127.0.0.1:8000"
$v1 = "$base/api/v1"

# 서버 미실행 시 안내
try {
    $null = Invoke-WebRequest -Uri $base -Method Get -TimeoutSec 2 -UseBasicParsing
} catch {
    Write-Host ">>> 백엔드 서버가 실행 중이 아닙니다. 먼저 다른 터미널에서:" -ForegroundColor Yellow
    Write-Host "    cd cert-app\backend" -ForegroundColor Gray
    Write-Host "    uv run python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000" -ForegroundColor Gray
    Write-Host ">>> 서버를 띄운 뒤 이 스크립트를 다시 실행하세요.`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== 1. Health ===" -ForegroundColor Cyan
try {
    $h = Invoke-RestMethod -Uri "$base/health" -Method Get
    Write-Host ($h | ConvertTo-Json -Compress)
    if ($h.status -eq "healthy" -or $h.status -eq "degraded") { Write-Host "OK" -ForegroundColor Green } else { Write-Host "CHECK" -ForegroundColor Yellow }
} catch { Write-Host "FAIL: $_" -ForegroundColor Red }

Write-Host "`n=== 2. RAG 검색 (certificates_vectors) ===" -ForegroundColor Cyan
try {
    $rag = Invoke-RestMethod -Uri "$v1/certs/search/rag?q=정보처리&limit=3" -Method Get
    Write-Host "query: $($rag.query), items: $($rag.items.Count)"
    $rag.items | ForEach-Object { Write-Host "  - $($_.name) (qual_id=$($_.qual_id), similarity=$($_.similarity))" }
    if ($rag.items.Count -gt 0) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "NO RESULTS (certificates_vectors 비었거나 RAG 미연동)" -ForegroundColor Yellow }
} catch { Write-Host "FAIL: $_" -ForegroundColor Red }

Write-Host "`n=== 3. 인기 전공 (정규화 없음) ===" -ForegroundColor Cyan
try {
    $pop = Invoke-RestMethod -Uri "$v1/recommendations/popular-majors?limit=5" -Method Get
    Write-Host "majors: $($pop.majors -join ', ')"
    if ($pop.majors.Count -gt 0) { Write-Host "OK" -ForegroundColor Green } else { Write-Host "EMPTY" -ForegroundColor Yellow }
} catch { Write-Host "FAIL: $_" -ForegroundColor Red }

Write-Host "`n=== 4. 자격 목록 일부 ===" -ForegroundColor Cyan
try {
    $certs = Invoke-RestMethod -Uri "$v1/certs?page=1&page_size=2" -Method Get
    Write-Host "total: $($certs.total), items: $($certs.items.Count)"
    Write-Host "OK" -ForegroundColor Green
} catch { Write-Host "FAIL: $_" -ForegroundColor Red }

Write-Host "`nDone." -ForegroundColor Gray
