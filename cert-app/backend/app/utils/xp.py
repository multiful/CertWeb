"""
자격증 XP / 레벨 / 티어 계산 유틸리티.

난이도(difficulty) 기반 XP 계산 → 누적 total_xp → 레벨(1~9) → 티어(Bronze/Silver/Gold/Platinum/Diamond).
"""
from __future__ import annotations
from typing import Optional


# ─── XP 계산 ──────────────────────────────────────────────────────────────────

def calculate_cert_xp(difficulty: Optional[float]) -> float:
    """
    자격증 1개의 XP 점수를 반환 (최솟값 0.5 보장).

    난이도 구간별 가중치:
      9.0~9.9 → +12    (최종 21.0~21.9)
      8.0~8.9 → +8     (최종 16.0~16.9)
      7.0~7.9 → +5     (최종 12.0~12.9)
      6.0~6.9 → +2     (최종 8.0~8.9)
      5.0~5.9 →  0     (최종 5.0~5.9)
      4.0~4.9 → -0.5   (최종 3.5~4.4)
      3.0~3.9 → -1.0   (최종 2.0~2.9)
      1.0~2.9 → -0.5   (최종 0.5~2.4)
    """
    if difficulty is None:
        return 3.0  # 난이도 미상: 기본 3 XP

    d = float(difficulty)

    if d >= 9.0:
        bonus = 12.0
    elif d >= 8.0:
        bonus = 8.0
    elif d >= 7.0:
        bonus = 5.0
    elif d >= 6.0:
        bonus = 2.0
    elif d >= 5.0:
        bonus = 0.0
    elif d >= 4.0:
        bonus = -0.5
    elif d >= 3.0:
        bonus = -1.0
    else:  # 1.0 ~ 2.9
        bonus = -0.5

    return max(0.5, round(d + bonus, 2))


# ─── 레벨 임계값 ──────────────────────────────────────────────────────────────
# 레벨 N이 되려면 누적 XP가 LEVEL_XP_THRESHOLDS[N-1] 이상이어야 함.
# 설계 기준: 평균 난이도(5.0) 자격증 1개 ≈ 5 XP → Lv2 도달.
#
# Lv1:  0+ (초기)
# Lv2:  5+ (~1개 기본)
# Lv3: 15+ (~3개 기본 or 1개 어려운)
# Lv4: 35+ (~7개 기본 or 2~3개 어려운)
# Lv5: 70+ (~14개 기본 or 5개 어려운)
# Lv6: 120+
# Lv7: 190+
# Lv8: 290+
# Lv9: 430+
#
LEVEL_XP_THRESHOLDS: list[int] = [0, 5, 15, 35, 70, 120, 190, 290, 430]
MAX_LEVEL = 9


def get_level_from_xp(total_xp: float) -> int:
    """누적 XP → 레벨(1~9)."""
    level = 1
    for i, threshold in enumerate(LEVEL_XP_THRESHOLDS):
        if total_xp >= threshold:
            level = i + 1
    return min(level, MAX_LEVEL)


def get_xp_for_next_level(current_level: int) -> Optional[int]:
    """다음 레벨에 필요한 XP 임계값. 최고 레벨이면 None."""
    if current_level >= MAX_LEVEL:
        return None
    return LEVEL_XP_THRESHOLDS[current_level]  # index = 다음레벨 - 1


def get_xp_for_current_level(current_level: int) -> int:
    """현재 레벨 시작점 XP."""
    return LEVEL_XP_THRESHOLDS[current_level - 1]


# ─── 티어 ─────────────────────────────────────────────────────────────────────

TIER_INFO: dict[str, dict] = {
    "Bronze":   {"levels": [1, 2], "color": "#a97241", "bg": "#2c1d0e", "border": "#7a4f25"},
    "Silver":   {"levels": [3, 4], "color": "#9da8b3", "bg": "#1a1f24", "border": "#6b7a87"},
    "Gold":     {"levels": [5, 6], "color": "#f5c518", "bg": "#2a220a", "border": "#c9a200"},
    "Platinum": {"levels": [7, 8], "color": "#54e0c7", "bg": "#0a2525", "border": "#2ab8a0"},
    "Diamond":  {"levels": [9],    "color": "#b9f2ff", "bg": "#071e2e", "border": "#4dd9ff"},
}


def get_tier_from_level(level: int) -> str:
    """레벨 → 티어 이름."""
    for tier_name, info in TIER_INFO.items():
        if level in info["levels"]:
            return tier_name
    return "Diamond"


def get_xp_summary(acquired_items: list) -> dict:
    """
    취득 자격증 리스트(각 항목에 avg_difficulty 또는 xp 포함)에서
    total_xp / level / tier / next_level_xp / current_level_xp 를 반환.
    """
    total_xp = 0.0
    for item in acquired_items:
        # item은 dict 또는 객체, avg_difficulty or pre-computed xp 사용
        if isinstance(item, dict):
            diff = item.get("avg_difficulty") or item.get("xp")
        else:
            diff = getattr(item, "avg_difficulty", None)
        xp = diff if diff is not None else calculate_cert_xp(None)
        if not isinstance(xp, float) and not isinstance(xp, int):
            xp = calculate_cert_xp(xp if xp else None)
        total_xp += xp

    level = get_level_from_xp(total_xp)
    tier = get_tier_from_level(level)
    next_threshold = get_xp_for_next_level(level)
    current_threshold = get_xp_for_current_level(level)
    tier_meta = TIER_INFO.get(tier, {})

    return {
        "total_xp": round(total_xp, 2),
        "level": level,
        "tier": tier,
        "tier_color": tier_meta.get("color", "#fff"),
        "current_level_xp": current_threshold,
        "next_level_xp": next_threshold,
    }
