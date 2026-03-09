# Contrastive 모델 로컬 사용 (CPU 전용)

## GitHub에 올리지 않아도 되는 파일

| 구분 | 파일/폴더 | 이유 |
|------|-----------|------|
| **제외 권장** | `model.safetensors` | 대용량 바이너리 (수십~수백 MB) |
| **제외 권장** | `example/cert_embeddings.npy` | 임베딩 캐시, 코퍼스·스크립트로 재생성 가능 |
| **제외 권장** | `example/cert_index.faiss` | FAISS 인덱스, 재생성 가능 |
| **제외 권장** | `example/cert_metadata.json`, `example/manifest.json` | example용 메타, 재생성 가능 |
| **올려도 됨** | `README.md`, `config*.json`, `tokenizer*.json`, `modules.json`, `1_Pooling/` | 설정·문서, 용량 작음 |

루트 `.gitignore`에 위 제외 항목이 이미 추가되어 있음.

---

## Contrastive를 서비스에 연결하는 방법

**현재 상태:** 프로덕션 RAG는 **OpenAI embedding**(`get_embedding`)만 사용 중이며, 이 contrastive 폴더는 **어디에서도 로드되지 않음**.  
연결하려면 아래 중 하나를 구현하면 됨.

### 1) 로컬 SentenceTransformer로 임베딩만 쓰기 (예: vector_service 대체)

- **모델 경로:** `app/rag/contrastive` (또는 환경변수로 지정).
- **코드 예 (CPU 전용):**

```python
from sentence_transformers import SentenceTransformer

# 로컬 경로만 사용 → Hugging Face Hub 접속 불필요
model = SentenceTransformer("cert-app/backend/app/rag/contrastive", device="cpu")

def get_embedding_local(text: str):
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()
```

- **차원:** 768 (OpenAI text-embedding-3-small은 1536).  
  기존 pgvector가 1536이면 **인덱스/컬럼을 768로 새로 만들거나**, 별도 벡터 테이블로 두고 검색만 이 모델로 수행해야 함.  
  **1536으로 다시 학습/맞추고 싶다면** 아래 "768 → 1536 호환" 섹션 참고.

### 2) example처럼 FAISS 로컬 검색만 쓰기

- `example/cert_index.faiss` + `cert_metadata.json`을 재생성한 뒤,  
  질의 → `model.encode(query)` → FAISS 검색 → 메타데이터 매핑.
- 서비스 API와 연결하려면: 해당 FAISS 검색 결과를 qual_id 등으로 변환해 기존 RAG 파이프라인(예: hybrid)에 넣는 래퍼만 추가하면 됨.

### 3) OpenAI와 병행 (멀티뷰 등)

- 설정 플래그로 “로컬 contrastive 사용”을 켜고,  
  `get_embedding` 호출부에서 `OPENAI_EMBEDDING=False` 같은 경우에만 위 `get_embedding_local`을 호출하도록 분기.

---

## CPU만 쓸 때 Hugging Face 연결이 필요한가?

**필요 없음.**

- 모델이 **로컬 폴더에 전부 있을 때** (`model.safetensors`, `config.json`, `tokenizer.json` 등)  
  `SentenceTransformer("로컬/경로")` 는 **해당 디렉터리만 읽음**. 인터넷/Hugging Face Hub 접속은 하지 않음.
- Hugging Face 연결은 **모델 ID**(예: `jhgan/ko-sroberta-multitask`)를 넘길 때만 필요.  
  이 contrastive 모델은 이미 그 베이스를 fine-tune한 결과가 로컬에 저장돼 있으므로, **CPU만 쓰고 이 경로만 쓰면 HF 연결 불필요**.

요약: **로컬 contrastive 폴더 경로만 지정하고 `device="cpu"`로 로드하면, CPU 전용 + 오프라인 동작 가능.**

---

## 768 → 1536 호환 (기존 pgvector와 차원 맞추기)

코랩에서 가져온 이 모델을 **1536차원으로 다시 학습/맞춰서** 기존 pgvector(OpenAI 1536)와 같이 쓰고 싶다면 선택지는 세 가지다.

### 1) 프로젝션 레이어 추가 (추천)

- **구조:** 지금 768-dim 출력 위에 **Linear(768 → 1536)** 를 하나 붙이고, 그 1536 출력을 최종 임베딩으로 사용.
- **학습:** 기존 contrastive(트리플렛) 데이터로 **프로젝션 레이어만** 학습하거나, 전체를 소량만 fine-tune.  
  의미 공간은 여전히 768에서 나오고, 1536은 그걸 선형으로 펼친 것이라 “진짜 1536차원 표현”은 아니지만, **같은 모델끼리는 코사인 유사도가 유지**되므로 검색 품질은 유지된다.
- **장점:** 베이스 모델·토크나이저 그대로 써서 코랩에서 재학습만 하면 됨. 구현도 비교적 단순(sentence-transformers에 커스텀 모듈 추가 후 저장).

### 2) 1536-dim 베이스 모델로 처음부터 재학습

- **방식:** 1536 차원을 내는 베이스(예: OpenAI 호환 오픈 모델, 또는 1024+ 프로젝션 등)를 쓰고, 지금 쓰는 contrastive 데이터로 **처음부터** fine-tune.
- **장점:** “원래부터” 1536이라 pgvector와 차원 일치.  
- **단점:** 베이스 교체·학습 파이프라인 다시 짜야 하고, 데이터/에폭 다시 돌려야 함.

### 3) 768 그대로 두고 별도 컬럼/인덱스

- **방식:** pgvector에 **768차원 컬럼 하나 더** 추가하거나, 이 모델 전용 테이블을 두고, 검색 시에만 이 모델(768)을 쓴다.  
  기존 1536 인덱스는 그대로 두고, “로컬 contrastive 검색”만 768로 수행 후 후처리에서 합치는 식.
- **장점:** 재학습 없음. 코랩 작업 불필요.  
- **단점:** 스키마/인덱스 하나 더 관리해야 함.

---

**정리:** “다시 학습시켜서 1536으로 쓸 수 있냐”는 **된다**.  
가장 현실적인 건 **1) 프로젝션 768→1536**을 코랩(또는 로컬)에서 한 번 더 학습해서 저장하고, 그 저장된 모델을 1536-dim 임베딩용으로 쓰는 방식이다. 코랩에서 가져온 걸 그대로 베이스로 두고, 위 프로젝션만 붙여서 학습하면 된다.
