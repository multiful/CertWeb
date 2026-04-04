"""
오프라인 RAG A/B용 env 프리셋 (scripts/eval_retrieval_ab_compare.py).

- CONTROL: 비우면 코드·.env 기본값(프리셋 키만 제거 후 캐시 클리어).
- CHALLENGERS: 이름 → {RAG_*: 값} 딕셔너리. eval 스크립트가 순서대로 control 대비 실행.

운영 A/B: main.py → rag_ab_middleware → 요청 스코프에서 set_rag_field_overrides 로
RAG_CHALLENGER_PRESET 필드만 덮어씀 (get_rag_settings()가 model_copy 반영).
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Callable, Dict, List, Tuple

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# 레거시 단일 challenger 호환 (eval 스크립트·온라인 A/B 공통)
RAG_CONTROL_PRESET: Dict[str, Any] = {}
# 온라인 A/B challenger: 기본값(코드) 대비 검증할 축. 승자 반영 후에는 다음 가설만 남김.
RAG_CHALLENGER_PRESET: Dict[str, Any] = {
    "RAG_DENSE_USE_QUERY_REWRITE": "false",
}

# eval / random_search 가 os.environ에서 제거 후 캐시 클리어할 때 쓰는 키(교차 검증: RAGSettings 필드명).
RAG_EVAL_PRESET_ENV_KEYS: Tuple[str, ...] = (
    "RAG_TOP_N_CANDIDATES",
    "RAG_VECTOR_THRESHOLD",
    "RAG_RRF_K",
    "RAG_RRF_EXPONENT",
    "RAG_RRF_W_BM25",
    "RAG_RRF_W_DENSE1536",
    "RAG_RRF_W_CONTRASTIVE768",
    "RAG_BM25_TOP_N",
    "RAG_CONTRASTIVE_TOP_N",
    "RAG_LINEAR_BM25_RANK_PRIOR",
    "RAG_POST_METADATA_BM25_RANK_PRIOR",
    "RAG_HIERARCHICAL_BLEND_WEIGHT",
    "RAG_METADATA_SOFT_MAIN_FIELD_IN_JOB_MATCH",
    "RAG_METADATA_DOMAIN_MISMATCH_ENABLE",
    "RAG_METADATA_DOMAIN_MISMATCH_PENALTY",
    "RAG_FUSION_METHOD",
    "RAG_DENSE_USE_QUERY_REWRITE",
)

# 다중 오프라인 A/B (이름, env 조각). Wave A=메타, B=풀·RRF, C=질의 재작성
RAG_AB_CHALLENGERS: List[Tuple[str, Dict[str, Any]]] = [
    (
        "wave_a_meta_no_mainfield_job",
        {"RAG_METADATA_SOFT_MAIN_FIELD_IN_JOB_MATCH": "false"},
    ),
    (
        "wave_a_meta_no_domain_mismatch",
        {"RAG_METADATA_DOMAIN_MISMATCH_ENABLE": "false"},
    ),
    (
        "wave_a_meta_domain_penalty_mild",
        {"RAG_METADATA_DOMAIN_MISMATCH_PENALTY": "-0.15"},
    ),
    (
        "wave_b_pool_top_n_plus_20",
        {"RAG_TOP_N_CANDIDATES": "156"},
    ),
    (
        "wave_b_pool_top_n_minus_20",
        {"RAG_TOP_N_CANDIDATES": "116"},
    ),
    (
        "wave_b_rrf_contrastive_up",
        {"RAG_RRF_W_CONTRASTIVE768": "1.05"},
    ),
    (
        "wave_c_dense_rewrite_off",
        {"RAG_DENSE_USE_QUERY_REWRITE": "false"},
    ),
]


def challenger_preset_to_overrides(preset: Dict[str, Any]) -> Dict[str, Any]:
    """
    문자열 기반 프리셋을 get_rag_settings().model_copy(update=...)에 넣을 수 있는
    네이티브 값 dict로 변환. 알 수 없는 키·검증 실패 시 해당 키는 스킵.
    """
    from app.rag.config import RAGSettings, get_rag_settings

    if not preset:
        return {}
    base = get_rag_settings()
    data = base.model_dump()
    keys_in = [k for k in preset if k in RAGSettings.model_fields]
    if not keys_in:
        return {}
    for k in keys_in:
        data[k] = preset[k]
    try:
        validated = RAGSettings.model_validate(data)
    except Exception as e:
        logger.warning("RAG challenger preset validation failed: %s", e)
        return {}
    return {k: getattr(validated, k) for k in keys_in}


def _resolve_variant(request: Request, ab_enable: bool, challenger_pct: int, allow_header: bool) -> tuple[str, bool]:
    """
    (variant_label, apply_challenger_overrides)
    """
    hdr = (request.headers.get("X-RAG-Variant") or "").strip().lower()
    if allow_header and hdr in ("control", "challenger"):
        return hdr, hdr == "challenger"
    if not ab_enable:
        return "control", False
    pct = max(0, min(100, challenger_pct))
    if pct <= 0 or not RAG_CHALLENGER_PRESET:
        return "control", False
    if secrets.randbelow(100) < pct:
        return "challenger", True
    return "control", False


async def rag_ab_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """
    RAG A/B: challenger 트래픽에만 ContextVar 오버라이드 적용.
    - app.config: RAG_AB_ENABLE, RAG_AB_CHALLENGER_PCT, RAG_AB_ALLOW_HEADER_OVERRIDE
    - X-RAG-Variant: control | challenger (allow_header 시 분할보다 우선)
    """
    from app.config import get_settings
    from app.rag.config import reset_rag_field_overrides, set_rag_field_overrides

    app_settings = get_settings()
    variant, use_challenger = _resolve_variant(
        request,
        app_settings.RAG_AB_ENABLE,
        app_settings.RAG_AB_CHALLENGER_PCT,
        app_settings.RAG_AB_ALLOW_HEADER_OVERRIDE,
    )

    token = None
    try:
        if use_challenger:
            ovr = challenger_preset_to_overrides(RAG_CHALLENGER_PRESET)
            if ovr:
                token = set_rag_field_overrides(ovr)
            else:
                variant = "control"
        response: Response = await call_next(request)
        response.headers["X-RAG-Variant"] = variant
        return response
    finally:
        if token is not None:
            reset_rag_field_overrides(token)
