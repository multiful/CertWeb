# 운영 가이드 — Redis 캐시 / 로그인 만료

## 1. Redis 캐시 청소 및 재적용

### 캐시가 쓰이는 곳

- **fastcert:*** — `/certs/{id}/fast` 응답(자격증 기본 정보 + 합격률·난이도 등). 서버 기동 시 DB → Redis 일괄 동기화.

### 방법 1: 서버 재시작 (권장)

백엔드가 뜰 때 **lifespan**에서 자동으로:

1. Redis `FLUSHALL`
2. 5초 후 `FastSyncService.sync_all_to_redis(db)` 로 DB → Redis 재동기화

그래서 **배포/재시작만 해도** 캐시는 비워진 뒤 최신 DB 기준으로 다시 채워집니다.

### 방법 2: 재시작 없이 API로 처리

1. **전체 캐시만 비우기**  
   - `POST /api/v1/admin/cache/flush`  
   - 헤더: `X-Job-Secret: <JOB_SECRET>`  
   - 이후 `/certs/{id}/fast`는 캐시 미스 시 DB 폴백으로 동작(캐시는 비어 있는 상태).

2. **비우고 바로 DB 기준으로 다시 채우기**  
   - `POST /api/v1/admin/cache/flush-and-sync`  
   - 헤더: `X-Job-Secret: <JOB_SECRET>`  
   - Redis 전체 flush 후, **백그라운드**에서 `sync_all_to_redis` 실행.  
   - 재시작 없이 캐시 청소 + 재적용을 한 번에 하고 싶을 때 사용.

예시 (로컬):

```bash
curl -X POST "http://localhost:8000/api/v1/admin/cache/flush-and-sync" \
  -H "X-Job-Secret: YOUR_JOB_SECRET"
```

---

## 2. 로그인이 2일 후에도 유지되는 이유 (만료가 안 되는 것처럼 보이는 이유)

- **Supabase Auth**는 **refresh token**으로 access token을 자동 갱신합니다.
- 브라우저에 세션(토큰)이 남아 있으면, 며칠 뒤에 다시 들어와도 refresh로 로그인 상태가 유지되는 것이 **기본 동작**입니다.

### 프론트엔드에서의 “만료” 동작

- **비활성 타임아웃:** `useAuth`에서 **1시간(3600초)** 동안 마우스/키보드/스크롤 등 이벤트가 없으면 **자동 로그아웃**합니다.
- 이 타이머는 **탭이 열려 있을 때만** 동작합니다. 탭을 닫았다가 2일 뒤에 다시 열면, 저장된 세션으로 `getSession()`이 그대로 세션을 반환하고, refresh token이 유효하면 로그인 상태가 유지됩니다.

### 만료를 짧게 하고 싶을 때

- **Supabase 대시보드** → **Authentication** → **Settings**  
  - **JWT expiry** (access token 유효 시간)  
  - **Refresh token 유효기간** (또는 “Refresh token rotation” 관련 설정)  
  을 줄이면, refresh token이 만료된 뒤에는 자동 갱신이 안 되어 로그인이 풀립니다.  
- 앱 코드 변경 없이 **설정만으로** 조정 가능합니다.

정리하면, “2일 만에 들어갔는데 로그인되어 있다”는 것은 refresh token이 아직 유효해서 그런 것이고, 더 짧게 만료시키려면 Supabase Auth 설정에서 refresh/JWT 만료를 줄이면 됩니다.
