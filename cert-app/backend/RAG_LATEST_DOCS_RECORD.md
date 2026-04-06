# RAG(최신) 문서 기록 / 정리 기준

> 생성일시: 2026-03-30
> 목적: 이 저장소의 “현재 운영 중인 최신 RAG 파이프라인”을 설명/재현하는 문서만 남기기 위한 기준 기록

## 1) “최신 RAG”로 간주한 문서 세트(남길 문서)

아래 문서들은 현재 `POST /api/v1/rag/ask` 기준 E2E 흐름(Rewrite/Hybrid Retrieve/Fusion/Metadata·개인화 Soft/Rerank/Gating/Evidence-first 생성)과 인덱싱/운영 튜닝 상태를 직접 다루거나, 최신 Contrastive(768-dim) 구성에 필수인 참조 문서를 포함합니다.

- `cert-app/backend/docs/RAG_FEATURES.md` — **구현된 RAG 기능 전체 카탈로그**(스위치·모듈·CLI)
- `cert-app/backend/RAG_Indexing.md`
- `cert-app/backend/data/rag_e2e_pipeline.md`
- `cert-app/backend/RAG_IMPROVEMENT.md`
- `cert-app/backend/app/rag/contrastive/README.md`
- `cert-app/backend/data/contrastive_index/README.md`
- `cert-app/backend/README.md`

## 2) 정리(삭제) 대상 후보: RAG(최신)과 무관한 문서

아래 문서들은 RAG 최신 파이프라인 설명 문서라기보다는, 프론트 성능/템플릿/복구 안내/일반 프로젝트 개요 등에 해당합니다. (삭제/보관 여부는 사용자 확인 후 진행)

- `cert-app/frontend/app/docs/FRONTEND_TROUBLESHOOTING_AND_RESULTS.md`
- `cert-app/frontend/app/docs/REACT_QUERY_DELAY_REDUCTION.md`
- `cert-app/backend/data/RESTORE_contrastive_cleaned_audit_v3.md`

> 사용자 요청 반영:
> - `README.md`(루트), `cert-app/README.md`, `cert-app/frontend/app/README.md`는 **README.md 이름 규칙**으로 정리 대상에서 제외(남김).

## 3) 다음 단계(사용자 확인 후 실행 예정)

1. (현재 턴) 프론트 docs 2개, `RESTORE_contrastive_cleaned_audit_v3.md` 삭제 완료.
2. (현재 턴) untracked 실험/보조 `.py` 스크립트 7개 삭제 완료.
3. 다음으로, RAG 실행/CLI(`app.rag ...`)에서 import 경로가 깨지지 않았는지(특히 인덱싱/재색인 스크립트) 확인합니다.

