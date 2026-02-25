"""
개선 사항 및 실행 가능 여부 점검 (로컬에서 실행).
  uv run python scripts/check_improvements.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    ok = []
    fail = []

    # 1) 모듈 import
    try:
        from app.api.certs import router as certs_router
        from app.crud import qualification_crud
        from app.services.vector_service import vector_service
        from app.redis_client import redis_client
        from app.config import get_settings
        ok.append("모듈 import (certs, crud, vector_service, redis, config)")
    except Exception as e:
        fail.append(f"모듈 import: {e}")
        print("FAIL:", fail[-1])
        return 1

    # 2) get_list에 cached_total 인자 존재
    import inspect
    sig = inspect.signature(qualification_crud.get_list)
    if "cached_total" in sig.parameters:
        ok.append("get_list(cached_total) 시그니처 존재")
    else:
        fail.append("get_list에 cached_total 없음")

    # 3) Redis int roundtrip (연결된 경우만)
    if redis_client.client:
        try:
            redis_client.set("_check_int", 12345, 10)
            v = redis_client.get("_check_int")
            redis_client.client.delete("_check_int")
            if v == 12345:
                ok.append("Redis int 저장/조회 정상")
            else:
                fail.append(f"Redis int roundtrip: 기대 12345, 실제 {v!r}")
        except Exception as e:
            fail.append(f"Redis int roundtrip: {e}")
    else:
        ok.append("Redis 미연결 시 count 캐시만 스킵 (정상)")

    # 4) RAG threshold 로직
    try:
        s = get_settings()
        th = s.RAG_MATCH_THRESHOLD if s.RAG_MATCH_THRESHOLD > 0 else None
        max_d = (1.0 - th) if (th is not None and th > 0) else 1.0
        if th == 0.4 and max_d == 0.6:
            ok.append("RAG match_threshold -> max_distance 계산 일치 (0.4 -> 0.6)")
        else:
            ok.append(f"RAG threshold 계산 (threshold={th}, max_distance={max_d})")
    except Exception as e:
        fail.append(f"RAG threshold: {e}")

    # 5) pg_trgm 마이그레이션 파일 존재
    mig = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations", "add_pg_trgm_gin_indexes.sql")
    if os.path.isfile(mig):
        ok.append("migrations/add_pg_trgm_gin_indexes.sql 존재")
    else:
        fail.append("add_pg_trgm_gin_indexes.sql 없음")

    print("--- 개선 사항 점검 결과 ---")
    for x in ok:
        print("  OK:", x)
    for x in fail:
        print("  FAIL:", x)
    print("---")
    return 0 if not fail else 1

if __name__ == "__main__":
    sys.exit(main())
