# RAG Indexing Baseline 운영 상태

> 생성일시: 2026-03-28 01:44:01  
> **본 인덱싱 파이프라인은 Baseline 기반으로 작동한다.**

## 1) 현재 적용 범위 (Indexing 단계)

- Parse/Chunking/Embedding/Store 중 **Indexing 단계만 고도화** 적용
- 기존 파일 구조를 유지하며 in-place 업데이트
- `try/except` 및 로깅을 통해 배치 처리 중 단건 실패가 전체 중단으로 전파되지 않도록 구성

## 2) 반영된 핵심 변경

- `cert_summary`, `cert_description`를 canonical content에 주입하여 임베딩 텍스트 문맥 확장
- metadata 필수 필드 보강:
  - `doc_id` (문서 식별/동기화용)
  - `chunk_type` (`text`)
  - `section_path` (`main_field > ncs_large`)
- `exam_type` 판정 로직 보강:
  - 1순위: `qualification.written_cnt`, `qualification.practical_cnt`
  - 2순위: `qual_type` 문자열 fallback
- 재색인 쿼리에서 `qualification` + `certificates_vectors(chunk_index=0)` 조인으로
  `cert_summary/cert_description/related_majors/written_cnt/practical_cnt` 동시 조회

## 3) 현재 DB 상태 (재색인 후)

- 대상: `certificates_vectors` (`chunk_index = 0`)
- 총 건수: `1101`
- `doc_id` 존재: `1101/1101`
- `chunk_type` 존재: `1101/1101`
- `section_path` 존재: `1101/1101`
- `exam_type != unknown`: `5/1101`
- content 길이: 평균 `493`, 최소 `246`, 최대 `1462`

## 4) exam_type 값이 5건만 채워지는 이유

- 코드 오류가 아니라 **원천 데이터 상태** 영향
- `qualification` 기준으로 `written_cnt > 0 OR practical_cnt > 0`인 자격증이 현재 5건
- 따라서 `exam_type`을 실측값 우선으로 계산하면 non-unknown도 5건이 정상

## 5) 다음 액션 (우선순위)

1. `qualification`의 `written_cnt/practical_cnt` 소스 확장 또는 보정 배치 실행
2. `exam_type` 보정 후 재색인 (증분 가능)
3. 골든셋(`reco_golden_recommendation_19_clean.jsonl`) 기준 오프라인 평가를 주기적으로 비교
4. `current` 파이프라인 성능 저하 구간(Recall/MRR) 원인 분석:
   - query rewrite/slot/intent 가중치
   - domain filtering 강도
   - reranker fallback 정책

## 6) NCS CSV 파이프라인 (DB 우선)

| 파일 | 역할 |
|------|------|
| `dataset/ncs_mapping1.csv` | NCS 원천(동일 자격증명 다행). Git/수급 기준. |
| `dataset/ncs_mapping_resolved.csv` | 자격증명당 1행. `scripts/export_resolved_ncs_csv.py`가 DB `ncs_large`·`main_field`(읽기) + 원천으로 생성. |
| `apply_ncs_mapping_to_qualification.py` | 기본 입력: **resolved가 있으면 resolved**, 없으면 원천(행 선택 로직 동일). 갱신 컬럼만 `ncs_large_mapped`·`ncs_mid`. |
| `run_ncs_canonical_ab_eval.py` | `--csv` 기본값 동일. |

권장 순서(원천 변경 시): `export_resolved_ncs_csv.py` → apply → `reindex_cert_vectors` → `build_bm25_from_db`.

## 7) 인덱싱 병목 점검 (현 구조)

- **임베딩 API**: 재색인 시간·비용의 대부분. 배치 크기 `reindex_cert_vectors --batch-size`(기본 128) 조절.
- **DB**: 자격 한 줄당 청크 소수; `certificates_vectors` 배치 upsert. UPDATE 다발은 apply 단계(자격 수만큼)이며 현재 규모(~1k)에서는 허용 범위.
- **BM25**: `certificates_vectors` 풀 스캔 1회 후 `bm25.pkl` 기록. 메모리·디스크 I/O 위주.
- **Redis**: 검색 결과 캐시가 켜져 있으면 인덱스 교체 직후 오래된 히트 가능 → 평가 스크립트는 캐시 off 권장.
