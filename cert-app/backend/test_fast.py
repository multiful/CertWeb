import requests
import time
import urllib.parse
import json
import os
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

REDIS_URL = "redis://default:FHdjGf7H1CYLvevptL9sVqFJ1P7tNdiF@redis-16019.c340.ap-northeast-2-1.ec2.cloud.redislabs.com:16019"
BASE = "http://localhost:8000/api/v1"

PASS_STR = "[PASS]"
FAIL_STR = "[FAIL]"
INFO_STR = "[INFO]"
SKIP_STR = "[SKIP]"


def chk(cond, msg):
    print(f"{PASS_STR if cond else FAIL_STR} {msg}")
    return cond


results = []

# ============================================================
# [1] Redis Connection
# ============================================================
print("\n========== [1] Redis 연결 ==========")
import redis
redis_ok = False
try:
    r = redis.from_url(REDIS_URL)
    r.ping()
    host = REDIS_URL.split("@")[1]
    print(f"{PASS_STR} Redis 연결 성공: {host}")
    redis_ok = True
except Exception as e:
    print(f"{FAIL_STR} Redis 연결 실패: {e}")


# ============================================================
# [2] API Health
# ============================================================
print("\n========== [2] 헬스체크 ==========")
res_health = requests.get("http://localhost:8000/health")
h = res_health.json()
print(f"  전체: {h.get('status')} | DB: {h.get('database')} | Redis: {h.get('redis')}")
chk(res_health.status_code == 200, "HTTP 200 OK")
chk(h.get("status") == "healthy", f"Server healthy: {h.get('status')}")
chk(h.get("redis") == "healthy", f"Redis healthy: {h.get('redis')}")
chk(h.get("database") == "healthy", f"DB healthy: {h.get('database')}")


# ============================================================
# [3] Recommendations
# ============================================================
print("\n========== [3] 전공 맞춤 추천 ==========")
major_raw = "컴퓨터공학"
major_enc = urllib.parse.quote(major_raw)
res_rec = requests.get(f"{BASE}/recommendations?major={major_enc}&limit=4")
rec_data = res_rec.json().get("items", [])
matched_major = res_rec.json().get("major", "")
chk(res_rec.status_code == 200, f"추천 API 상태코드: {res_rec.status_code}")
chk(len(rec_data) > 0, f"추천 결과 {len(rec_data)}개 반환됨")
if matched_major:
    print(f"{INFO_STR} 매칭된 전공: {matched_major}")
for item in rec_data:
    print(f"  - {item.get('qual_name')}  [score={item.get('score')}]")


# ============================================================
# [4] Fast endpoint vs Normal (latency comparison)
# ============================================================
print("\n========== [4] Fast 엔드포인트 속도 비교 ==========")
res_list = requests.get(f"{BASE}/certs?limit=1")
cert_id_valid = None
if res_list.status_code == 200 and res_list.json().get("items"):
    cert_id_valid = res_list.json()["items"][0]["qual_id"]
    cert_name = res_list.json()["items"][0]["qual_name"]
    print(f"{INFO_STR} 테스트 자격증: {cert_name} (ID={cert_id_valid})")

if cert_id_valid:
    # Normal
    t0 = time.perf_counter()
    r_norm = requests.get(f"{BASE}/certs/{cert_id_valid}")
    t1 = time.perf_counter()
    normal_ms = (t1 - t0) * 1000
    chk(r_norm.status_code == 200, f"일반 API 상태코드: {r_norm.status_code}")
    print(f"{INFO_STR} 일반 API 응답시간: {normal_ms:.2f} ms")

    # Fast (Fallback - no cache)
    t0 = time.perf_counter()
    r_fast1 = requests.get(f"{BASE}/certs/{cert_id_valid}/fast")
    t1 = time.perf_counter()
    fallback_ms = (t1 - t0) * 1000
    chk(r_fast1.status_code == 200, f"Fast API 상태코드 (Fallback): {r_fast1.status_code}")
    print(f"{INFO_STR} Fast API 응답시간 (DB Fallback): {fallback_ms:.2f} ms")

    # Simulate Quix Streams: populate Redis
    if redis_ok:
        import orjson as _orjson
        payload_from_api = r_fast1.json()  # already {"status":..., "data":...} or raw
        if "data" not in payload_from_api:
            payload_from_api = {"status": "success", "data": payload_from_api}
        r.set(f"fastcert:{cert_id_valid}", _orjson.dumps(payload_from_api))
        print(f"{INFO_STR} Redis에 데이터 저장 완료 (Quix Streams 워커 시뮬레이션)")

        # Fast (Cache Hit)
        t0 = time.perf_counter()
        r_fast2 = requests.get(f"{BASE}/certs/{cert_id_valid}/fast")
        t1 = time.perf_counter()
        cache_ms = (t1 - t0) * 1000
        chk(r_fast2.status_code == 200, f"Fast API 상태코드 (Cache Hit): {r_fast2.status_code}")
        print(f"{INFO_STR} Fast API 응답시간 (Redis Cache Hit): {cache_ms:.2f} ms")
        chk(cache_ms < normal_ms, f"캐시 응답이 일반 API보다 빠름: {cache_ms:.1f}ms < {normal_ms:.1f}ms")
        if cache_ms > 0:
            print(f"{INFO_STR} 속도 향상: {normal_ms/cache_ms:.1f}x")

        # Third call to confirm stable cache hit
        t0 = time.perf_counter()
        r_fast3 = requests.get(f"{BASE}/certs/{cert_id_valid}/fast")
        t1 = time.perf_counter()
        cache2_ms = (t1 - t0) * 1000
        print(f"{INFO_STR} Fast API 응답시간 (Cache Hit 2nd): {cache2_ms:.2f} ms")
    else:
        print(f"{SKIP_STR} Redis 불가, Cache Hit 테스트 건너뜀")


# ============================================================
# [5] README.md 내용 검증
# ============================================================
print("\n========== [5] README.md 검증 ==========")
with open("../README.md", "r", encoding="utf-8") as f:
    text = f.read()

checks_readme = [
    ("Quix Streams", "README에 Quix Streams 언급"),
    ("orjson", "README에 orjson 언급"),
    ("Redis 비동기 캐싱", "README에 Redis 비동기 캐싱 언급"),
    ("안티그래비티", "README에 안티그래비티(프로젝트명) 언급"),
    ("FastAPI", "README에 FastAPI 언급"),
    ("Supabase", "README에 Supabase 언급"),
    ("pgvector", "README에 pgvector 언급"),
    ("quix_worker.py", "README에 quix_worker.py 경로 언급"),
    ("fast_certs.py", "README에 fast_certs.py 경로 언급"),
    ("react", "README에 React 언급"),
    ("Shadcn", "README에 Shadcn UI 언급"),
    ("Tailwind", "README에 Tailwind CSS 언급"),
    ("uvicorn main:app --reload", "README에 서버 실행 명령어 언급"),
    ("npm run dev", "README에 프론트엔드 실행 명령어 언급"),
    ("docker-compose up", "README에 Docker 실행 명령어 언급"),
]
for keyword, msg in checks_readme:
    chk(keyword.lower() in text.lower(), msg)

print("\n========== 테스트 완료 ==========")
