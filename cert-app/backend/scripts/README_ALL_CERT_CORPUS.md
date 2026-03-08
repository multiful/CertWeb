# 전체 자격증 코퍼스(ALL_CERT_CORPUS) 생성

bi-encoder contrastive 학습 **평가** 시 retrieval 후보 전체를 담는 `ALL_CERT_CORPUS_JSON` 파일 생성 방법.

## 개념 정리

| 구분 | 설명 |
|------|------|
| **contrastive 학습 데이터셋** | row 단위. `raw_query`, `profile`, `rewritten_query`, `positive`/`positives`, `negatives` 등. **모델 학습용** supervision 데이터. |
| **ALL_CERT_CORPUS_JSON** | 자격증 **전체 후보집합**. retrieval 평가 시 후보군 전체로 사용. 자격증 1개당 1문서. **검색/평가용** corpus. |

즉, 학습 데이터셋 전체를 넣는 것이 아니라, **전체 자격증 후보를 dedupe한 문서 코퍼스**를 별도 JSON으로 만든다.

---

## 파일명

- **스크립트:** `scripts/build_all_cert_corpus.py`
- **임시 코퍼스(학습 데이터에서 추출):** `data/all_cert_corpus_from_train.json`
- **최종 코퍼스(마스터/DB):** `data/all_cert_corpus.json`

---

## 실행 예시

```bash
# cert-app/backend 기준

# 작업 A: 학습 데이터셋 → 임시 코퍼스
uv run python scripts/build_all_cert_corpus.py --from-train-json data/contrastive_profile_train_merged.json -o data/all_cert_corpus_from_train.json

# 작업 B: 마스터 JSON → 최종 코퍼스
uv run python scripts/build_all_cert_corpus.py --from-master-json data/qualification_export.json -o data/all_cert_corpus.json

# 작업 B: 마스터 CSV → 최종 코퍼스
uv run python scripts/build_all_cert_corpus.py --from-master-csv data/qualification_export.csv -o data/all_cert_corpus.json

# 작업 B: Supabase(DB) 직접 로드 → 최종 코퍼스 (자격증 1103건, DATABASE_URL 필요)
# cert-app/backend 에서 실행. .env 에 DATABASE_URL=postgresql://...@db.xxx.supabase.co:5432/postgres
uv run python scripts/build_all_cert_corpus.py --from-db -o data/all_cert_corpus.json

# 또는 venv Python + PYTHONPATH 로 실행 (uv run 시 sqlalchemy 미설치 환경이면)
# PowerShell: $env:PYTHONPATH = "Z:\CertWeb\cert-app\backend"; & "C:\Users\rlaeh\envs\fastapi\.venv\Scripts\python.exe" scripts/build_all_cert_corpus.py --from-db -o data/all_cert_corpus.json
```

**선택 옵션**

- `--no-source-roles` : train 모드에서 `source_roles` 메타데이터 제외
- `--dedupe-by qual_name|qual_id|none` : 마스터 모드 dedupe 기준 (기본: qual_name)
- `--master-csv-delimiter ";"` : CSV 구분자 (기본 `,`)
- `--no-vectors-content` : `--from-db` 시 `certificates_vectors` content 미사용, qualification 컬럼만으로 text 생성

---

## 입·출력 형식

### 입력 (학습 데이터셋 예시)

```json
[
  {
    "query_id": "p001",
    "raw_query": "...",
    "profile": { ... },
    "rewritten_query": "...",
    "positive": { "qual_id": 102, "qual_name": "정보처리기사", "text": "자격증명: ..." },
    "negatives": [
      { "qual_id": 202, "qual_name": "정보보안기사", "text": "..." }
    ]
  },
  {
    "positives": [
      { "qual_id": 102, "qual_name": "정보처리기사", "text": "..." }
    ]
  }
]
```

### 입력 (마스터 JSON/CSV 예시)

- **JSON:** 루트가 배열. 각 요소에 `qual_id`, `qual_name` 및 선택적으로 `qual_type`, `main_field`, `ncs_large`, `관련직무`, `추천대상`, `설명` 등.
- **CSV:** 첫 행 헤더. 컬럼명 `qual_name`, `qual_id`, `qual_type`, `main_field` 등 (한글 키도 지원).

### 출력 (공통)

```json
[
  {
    "qual_id": 102,
    "qual_name": "정보처리기사",
    "text": "자격증명: 정보처리기사\n자격종류: 국가기술자격\n관련직무: ...\n추천대상: ...\n설명: ..."
  }
]
```

train 모드에서 `--no-source-roles` 를 쓰지 않으면 optional로 `source_roles: ["positive", "negative"]` 가 붙을 수 있다.

---

## Dedupe 기준

- **임시 코퍼스 (--from-train-json)**  
  - **기준:** `qual_name`  
  - 동일 `qual_name` 이 여러 번 나오면 **1개만** 유지.  
  - **text 선택:** 같은 이름이면 **더 긴 text**를 가진 항목을 유지 (정보가 많은 쪽 우선).  
  - `qual_id` 는 가능하면 유지(첫 번째 또는 더 긴 text 항목의 id).

- **최종 코퍼스 (--from-master-* / --from-db)**  
  - **기본:** `--dedupe-by qual_name` → `qual_name` 기준 1건만.  
  - `--dedupe-by qual_id` → `qual_id` 기준.  
  - `--dedupe-by none` → dedupe 없음.

---

## 임시 코퍼스 vs 최종 코퍼스

| 항목 | 임시 (all_cert_corpus_from_train.json) | 최종 (all_cert_corpus.json) |
|------|----------------------------------------|------------------------------|
| **출처** | contrastive 학습 JSON의 positive/positives/negatives만 수집 | 실제 서비스 DB 또는 전체 자격증 마스터 JSON/CSV |
| **범위** | 학습 데이터에 등장한 자격증만 (일부) | **전체** 자격증 후보 |
| **용도** | 학습 직후 빠른 평가·디버깅, 학습 데이터에 포함된 자격증만 retrieval 테스트 | **실제 평가·배포** 시 retrieval 후보 전체 |
| **text** | 학습 데이터에 적힌 그대로 (여러 row에서 나온 경우 더 긴 text로 병합) | 마스터/DB 필드로 retrieval 포맷 생성 (자격증명/자격종류/관련직무/추천대상/설명) |

**권장:**  
- 개발·실험 단계에서는 임시 코퍼스로 빠르게 Recall@k 등 확인.  
- 최종 지표·배포 전에는 **반드시** DB 또는 마스터 export 기반으로 `all_cert_corpus.json` 을 만들어 사용.

---

## 학습 코드에서 ALL_CERT_CORPUS_JSON 연결

평가 스크립트에서 후보 코퍼스 경로를 한 곳에서 지정해 두면 된다.

```python
# 예: eval 또는 contrastive 학습 스크립트 상단
ALL_CERT_CORPUS_JSON = "all_cert_corpus.json"   # 또는 "data/all_cert_corpus.json"

# 사용 예
with open(ALL_CERT_CORPUS_JSON, "r", encoding="utf-8") as f:
    corpus = json.load(f)
# corpus = [ {"qual_id": ..., "qual_name": "...", "text": "..."}, ... ]
```

- **실행 시 working directory** 가 `cert-app/backend` 이면 `data/all_cert_corpus.json` 에 저장했을 경우  
  `ALL_CERT_CORPUS_JSON = "data/all_cert_corpus.json"` 로 두면 된다.  
- 절대 경로를 쓰려면 `Path(__file__).resolve().parent.parent / "data" / "all_cert_corpus.json"` 처럼 구성해도 된다.

**정리:**  
- `ALL_CERT_CORPUS_JSON = "data/all_cert_corpus.json"` (또는 프로젝트 내 해당 경로) 로 두고,  
- 위 실행 예시대로 `--from-db` 또는 `--from-master-json` / `--from-master-csv` 로 **최종** `all_cert_corpus.json` 을 생성한 뒤,  
- 학습/평가 코드에서 이 경로를 읽어 후보 코퍼스로 사용하면 된다.
