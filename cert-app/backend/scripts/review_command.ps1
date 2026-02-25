# 검토 커맨드: 서버가 떠 있는 상태에서 실행. 목록/트렌딩/최근본 API를 호출해
# 서버 로그에 남는 SQL을 확인할 수 있음. (qual_id IN (...) 대신 = ANY(:ids) 사용 여부 확인)
$base = "http://127.0.0.1:8000"
$v1 = "$base/api/v1"

Write-Host "[검토] Health..." -ForegroundColor Cyan
try { Invoke-RestMethod -Uri "$base/health" -Method Get -TimeoutSec 5 | Out-Null } catch { Write-Host "  (서버 미실행 시 실패)" -ForegroundColor Yellow }

Write-Host "[검토] certs list (count/bulk 경로)..." -ForegroundColor Cyan
try { Invoke-RestMethod -Uri "$v1/certs?page=1&page_size=5" -Method Get -TimeoutSec 10 | Out-Null } catch { Write-Host "  오류: $_" -ForegroundColor Red }

Write-Host "[검토] trending (ANY(:ids) 경로)..." -ForegroundColor Cyan
try { Invoke-RestMethod -Uri "$v1/certs/trending/now?limit=5" -Method Get -TimeoutSec 5 | Out-Null } catch { Write-Host "  오류: $_" -ForegroundColor Red }

Write-Host "[검토] 완료. 서버 터미널 로그에서 qual_id_1_1 등 파라미터가 없으면 OK." -ForegroundColor Green
