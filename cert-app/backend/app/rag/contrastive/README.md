# Contrastive (768-dim) Retriever

**Contrastive = 768-dim 한국어 bi-encoder 전용.** 자격증 도메인 contrastive 학습 모델만 해당함.

- **공식 모델:** Hub `multifuly/cert-constrative-embedding` (로컬 모델 파일 제거됨.)
- **아님:** jhgan/ko-sroberta-multitask 등 일반 768-dim 한국어 모델은 contrastive가 아님. FAISS는 공식 모델로 구축됨.

- **설정:** `.env` 에 `RAG_CONTRASTIVE_MODEL=multifuly/cert-constrative-embedding`, `RAG_CONTRASTIVE_INDEX_DIR=data/contrastive_index`
- **문서:** [`docs/RAG_FEATURES.md`](../../../docs/RAG_FEATURES.md) (Contrastive 행) · 백엔드 `README.md` · `data/contrastive_index/README.md`

---

## 인덱스 (`data/contrastive_index/`)

- **삭제하면 안 됨.** Contrastive 검색은 이 인덱스에 의존함.
- `cert_index.faiss`, `cert_metadata.json` 이 없으면 `contrastive_search()` 가 빈 리스트를 반환하고, 3-way RRF에서 contrastive arm 이 동작하지 않음.
- 용량이 부족하면 `RAG_CONTRASTIVE_ENABLE=false` 로 끈 뒤 인덱스 폴더를 지울 수 있음. (나중에 다시 쓰려면 인덱스 재생성 필요.)
