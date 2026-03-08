"""
구조화 로깅 및 감사 로그.
- 로그에는 파라미터/토큰 원문을 남기지 않음.
- 감사: 누가 어떤 API를 호출했는지 수준만 (user_id는 해시 또는 마스킹 권장).
"""
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _mask_user_id(user_id: Optional[str]) -> str:
    """감사 로그용: user_id 일부만 노출 (개인정보 최소화)."""
    if not user_id or len(user_id) < 8:
        return "anon"
    return f"{user_id[:4]}***"


def log_structured(
    level: int,
    message: str,
    **kwargs: Any,
) -> None:
    """키-값 형태로 추가 필드를 붙여 로그. kwargs는 str() 처리."""
    extra = " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    log_msg = f"{message} {extra}" if extra else message
    logger.log(level, log_msg)


def log_audit(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> None:
    """감사 로그: API 호출 요약. 개인정보 최소화."""
    log_structured(
        logging.INFO,
        "audit",
        method=method,
        path=path,
        status=status_code,
        duration_ms=round(duration_ms, 2),
        user=_mask_user_id(user_id),
        ip=(client_ip or "")[:32] if client_ip else "",
    )
