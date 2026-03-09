"""
Contrastive retriever: 768-dim 한국어 bi-encoder + FAISS 인덱스.

- **Contrastive(공식):** RAG_CONTRASTIVE_MODEL에 지정한 모델. Hub 기준 `multifuly/cert-constrative-embedding`.
  자격증 도메인 contrastive 학습으로 만든 768-dim SentenceTransformer. 이 모델만 contrastive임.
- **일반 768-dim 한국어 모델**(예: jhgan/ko-sroberta-multitask)은 contrastive가 아님. FAISS 차원만 맞출 뿐,
  인덱스는 contrastive 모델로 구축되었으므로 공식 모델 사용 권장.
- BM25·dense1536과 별도 arm으로 검색 후 RRF로만 결합. 768→1536 변환 금지.
- RAG_CONTRASTIVE_EMBEDDING_URL 설정 시 해당 URL로 질의 임베딩만 요청(로컬 모델 미로드).

지연 완화: (1) 로드 실패 시 한 번만 시도. (2) 정상 시 CPU 인코딩 ~100–500ms, pre-warm 권장.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.rag.config import get_rag_settings

logger = logging.getLogger(__name__)

# Lazy-loaded singleton
_model = None
_faiss_index = None
_metadata_by_row_id: Dict[int, dict] = {}  # row_id -> {qual_id, qual_name, text, ...}
_embedding_dim: int = 768
# 한 번 로드 실패하면 같은 프로세스에서 재시도하지 않음 → 질의마다 40초+ 지연 방지
_load_failed: bool = False
# 원격 임베딩 URL 설정 시 로컬 모델 미로드
_embedding_url: Optional[str] = None


def diagnose_contrastive_status() -> Dict[str, str]:
    """
    contrastive가 빈 리스트를 반환하는 이유를 단계별로 진단.
    반환: {"ok": "true"|"false", "reason": "설명", "step": "실패한 단계 또는 ok"}
    """
    out: Dict[str, str] = {"ok": "false", "reason": "", "step": ""}
    if _model is not None and _faiss_index is not None:
        out["ok"] = "true"
        out["reason"] = "로드 완료"
        out["step"] = "ok"
        return out
    if _load_failed:
        out["reason"] = "이전 로드 실패로 재시도 생략(프로세스당 1회만 시도)"
        out["step"] = "cached_failure"
        return out

    settings = get_rag_settings()
    embedding_url = (getattr(settings, "RAG_CONTRASTIVE_EMBEDDING_URL", None) or "").strip()
    model_name = (getattr(settings, "RAG_CONTRASTIVE_MODEL", None) or "").strip()
    index_dir = (getattr(settings, "RAG_CONTRASTIVE_INDEX_DIR", None) or "").strip()
    if not index_dir:
        out["reason"] = "RAG_CONTRASTIVE_INDEX_DIR 미설정"
        out["step"] = "config"
        return out
    if not embedding_url and not model_name:
        out["reason"] = "RAG_CONTRASTIVE_EMBEDDING_URL 또는 RAG_CONTRASTIVE_MODEL 미설정"
        out["step"] = "config"
        return out

    index_path = Path(index_dir)
    if not index_path.is_dir():
        out["reason"] = f"인덱스 디렉터리 없음: {index_dir}"
        out["step"] = "index_dir"
        return out
    if not (index_path / "cert_metadata.json").is_file():
        out["reason"] = f"cert_metadata.json 없음: {index_dir}"
        out["step"] = "metadata"
        return out
    if not (index_path / "cert_index.faiss").is_file():
        out["reason"] = f"cert_index.faiss 없음: {index_dir}"
        out["step"] = "faiss_file"
        return out
    try:
        import faiss  # noqa: F401
    except ImportError:
        out["reason"] = "faiss 미설치. pip install faiss-cpu"
        out["step"] = "faiss_import"
        return out
    if embedding_url and embedding_url.startswith(("http://", "https://")):
        out["reason"] = "설정·파일 정상. RAG_CONTRASTIVE_EMBEDDING_URL 사용 시 로컬 모델 불필요."
        out["step"] = "remote_embedding"
        return out
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError as e:
        out["reason"] = f"sentence_transformers 미설치 또는 torch 로드 실패: {e}. pip install sentence-transformers"
        out["step"] = "st_import"
        return out
    except Exception as e:
        out["reason"] = f"sentence_transformers 로드 중 오류 (numpy/pandas 호환 등): {e!r}"
        out["step"] = "st_import"
        return out
    out["reason"] = "설정·파일·import는 정상. 모델 로드 단계에서 실패했을 수 있음(이전 로그 확인)"
    out["step"] = "model_load"
    return out


def _embed_via_api(query: str):
    """RAG_CONTRASTIVE_EMBEDDING_URL로 POST하여 768-dim 벡터 반환. L2 정규화 적용. 실패 시 None."""
    url = (_embedding_url or "").strip().rstrip("/")
    if not url:
        return None
    try:
        import httpx
        import numpy as np
        settings = get_rag_settings()
        token = (getattr(settings, "RAG_CONTRASTIVE_EMBEDDING_TOKEN", None) or "").strip()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = {"inputs": query.strip()}
        # HF Space 등: 루트 먼저 시도, 404면 /embed 시도 (콜드스타트/경로 차이 대응)
        to_try = [url, f"{url}/", f"{url}/embed"]
        last_error = None
        with httpx.Client(timeout=30.0) as client:
            for base in to_try:
                try:
                    r = client.post(base, json=body, headers=headers)
                    if r.status_code != 200:
                        last_error = f"HTTP {r.status_code}"
                        continue
                    data = r.json()
                    if isinstance(data, list):
                        vec = data[0] if data and isinstance(data[0], list) else data
                    elif isinstance(data, dict) and "embedding" in data:
                        vec = data["embedding"]
                    else:
                        vec = data
                    if not vec or not isinstance(vec, (list, tuple)):
                        continue
                    arr = np.array(vec, dtype=np.float32).flatten()
                    if arr.size != _embedding_dim:
                        continue
                    norm = np.linalg.norm(arr)
                    if norm > 1e-9:
                        arr = arr / norm
                    return arr.reshape(1, -1)
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
                    last_error = e
                    continue
        if last_error:
            logger.warning("contrastive retriever: remote embedding failed: %s", last_error)
        return None
    except Exception as e:
        logger.warning("contrastive retriever: remote embedding failed: %s", e)
        return None


def prewarm_contrastive() -> bool:
    """
    앱 기동 시 한 번 호출하면 첫 질의에서의 cold-start 지연을 줄임.
    contrastive가 비활성이거나 로드 실패 시 False, 성공 시 True.
    """
    return _ensure_loaded()


def _ensure_loaded() -> bool:
    """모델·FAISS·메타데이터 로드. 실패 시 False. RAG_CONTRASTIVE_EMBEDDING_URL 있으면 로컬 모델 생략."""
    global _model, _faiss_index, _metadata_by_row_id, _embedding_dim, _load_failed, _embedding_url
    if _faiss_index is not None and (_model is not None or _embedding_url is not None):
        return True
    if _load_failed:
        return False

    settings = get_rag_settings()
    embedding_url = (getattr(settings, "RAG_CONTRASTIVE_EMBEDDING_URL", None) or "").strip()
    model_name = (getattr(settings, "RAG_CONTRASTIVE_MODEL", None) or "").strip()
    index_dir = (getattr(settings, "RAG_CONTRASTIVE_INDEX_DIR", None) or "").strip()
    if not index_dir:
        logger.debug("contrastive retriever: RAG_CONTRASTIVE_INDEX_DIR not set")
        _load_failed = True
        return False
    if not embedding_url and not model_name:
        logger.debug("contrastive retriever: RAG_CONTRASTIVE_EMBEDDING_URL or RAG_CONTRASTIVE_MODEL not set")
        _load_failed = True
        return False

    index_path = Path(index_dir)
    if not index_path.is_dir():
        logger.warning("contrastive retriever: index dir not found: %s", index_dir)
        _load_failed = True
        return False

    # Load metadata (row_id → qual_id)
    cert_meta_path = index_path / "cert_metadata.json"
    if not cert_meta_path.is_file():
        logger.warning("contrastive retriever: cert_metadata.json not found in %s", index_dir)
        _load_failed = True
        return False
    try:
        with open(cert_meta_path, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
        _metadata_by_row_id = {int(m.get("row_id", i)): m for i, m in enumerate(raw_list)}
    except Exception as e:
        logger.exception("contrastive retriever: failed to load cert_metadata.json: %s", e)
        _load_failed = True
        return False

    # Load FAISS index
    faiss_path = index_path / "cert_index.faiss"
    if not faiss_path.is_file():
        logger.warning("contrastive retriever: cert_index.faiss not found in %s", index_dir)
        _load_failed = True
        return False
    try:
        import faiss
        _faiss_index = faiss.read_index(str(faiss_path))
        _embedding_dim = _faiss_index.d
    except ImportError:
        logger.warning("contrastive retriever: faiss not installed. pip install faiss-cpu (or faiss-gpu)")
        _load_failed = True
        return False
    except Exception as e:
        logger.exception("contrastive retriever: failed to load FAISS index: %s", e)
        _load_failed = True
        return False

    # 원격 임베딩 URL이 있으면 로컬 모델 로드 생략 (HF Inference API 등으로 지연 단축)
    if embedding_url and embedding_url.startswith(("http://", "https://")):
        _embedding_url = embedding_url
        logger.info(
            "contrastive retriever loaded (remote embedding): url=%s index_dir=%s ndocs=%s dim=%s",
            embedding_url[:60] + "..." if len(embedding_url) > 60 else embedding_url,
            index_dir,
            len(_metadata_by_row_id),
            _embedding_dim,
        )
        return True

    # Load SentenceTransformer (HF repo or local path) — 여기서 torch 등 로드로 30초+ 걸릴 수 있음
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name, device="cpu")
    except ImportError:
        logger.warning("contrastive retriever: sentence_transformers not installed. pip install sentence-transformers")
        _load_failed = True
        return False
    except Exception as e:
        logger.exception("contrastive retriever: failed to load model %s: %s", model_name, e)
        _load_failed = True
        return False

    logger.info(
        "contrastive retriever loaded: model=%s index_dir=%s ndocs=%s dim=%s",
        model_name, index_dir, len(_metadata_by_row_id), _embedding_dim,
    )
    return True


def contrastive_search(query: str, top_k: int = 95) -> List[Tuple[str, float]]:
    """
    Contrastive 768-dim FAISS 검색.
    반환: [(chunk_id, score), ...]. chunk_id는 qual_id:0 형식(기존 RRF와 호환).
    """
    if not query or not query.strip():
        return []

    if not _ensure_loaded():
        return []

    import numpy as np

    # Query embedding: 원격 URL 또는 로컬 모델
    q = None
    if _embedding_url:
        q = _embed_via_api(query)
    if q is None and _model is not None:
        try:
            from sentence_transformers import SentenceTransformer
            q = _model.encode([query.strip()], normalize_embeddings=True)
        except ImportError:
            return []
    if q is None or (hasattr(q, "size") and q.size == 0):
        return []
    q = np.asarray(q, dtype=np.float32)
    if q.ndim == 1:
        q = q.reshape(1, -1)

    k = min(top_k, _faiss_index.ntotal)
    if k <= 0:
        return []

    scores, indices = _faiss_index.search(q, k)
    if indices is None or indices.size == 0:
        return []

    out: List[Tuple[str, float]] = []
    for i, row_id in enumerate(indices[0]):
        if row_id < 0:
            continue
        meta = _metadata_by_row_id.get(int(row_id))
        if meta is None:
            continue
        qual_id = meta.get("qual_id")
        if qual_id is None:
            continue
        # chunk_id 형식: qual_id:chunk_index (contrastive는 자격증 단위이므로 0)
        chunk_id = f"{qual_id}:0"
        score = float(scores[0][i])
        out.append((chunk_id, score))

    return out
