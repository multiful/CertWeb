# Contrastive 인덱스 디렉터리

3-way RRF(BM25 + Dense1536 + **Contrastive768**) 사용 시 이 디렉터리에 다음 파일이 필요합니다.

- **cert_index.faiss** – FAISS 인덱스 (768-dim, inner product)
- **cert_metadata.json** – row_id → qual_id, qual_name, text 매핑

**Contrastive(공식):** 768-dim 한국어 bi-encoder. **Hub 모델 `multifuly/cert-constrative-embedding`만 contrastive임.**  
일반 768-dim 한국어 모델(예: jhgan/ko-sroberta-multitask)은 contrastive가 아니며, 인덱스는 공식 모델로 구축됨.

`.env` 설정 예:

- `RAG_CONTRASTIVE_ENABLE=true`
- `RAG_CONTRASTIVE_INDEX_DIR=data/contrastive_index` (backend 루트 기준)
- `RAG_CONTRASTIVE_MODEL=multifuly/cert-constrative-embedding`

검증: `uv run python scripts/check_contrastive_connection.py` 또는 `uv run python scripts/test_contrastive_latency.py`
