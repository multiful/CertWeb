"""
개인화 soft scoring: 전공/학년/즐겨찾기/취득 자격증/난이도 적합도를 반영한 점수 보정.
profile 없으면 0 반환 (fallback). 기존 metadata_soft_score와 병행 사용 가능.
전공 비교 시 profile/자격증 모두 major_category로 정규화해 매칭률을 높임.
"""
import logging
from typing import Any, Dict, List, Optional, Set

from app.rag.utils.dense_query_rewrite import UserProfile
from app.rag.utils.major_normalize import normalize_major

logger = logging.getLogger(__name__)


# 기본 가중치 (config로 오버라이드)
DEFAULT_MAJOR_BONUS = 0.15
DEFAULT_FAVORITE_FIELD_BONUS = 0.10
DEFAULT_ACQUIRED_PENALTY = -1.0
DEFAULT_NEXT_STEP_BONUS = 0.10  # 취득 자격과 같은 분야 + 더 높은 난이도 → 다음 단계 보너스
DEFAULT_GRADE_DIFFICULTY_BONUS = 0.10
DEFAULT_FAR_TOO_DIFFICULT_PENALTY = -0.15
DEFAULT_FAR_TOO_EASY_PENALTY = -0.05  # 고학년(3~4) + 매우 쉬운 cert 약한 감점 (보조)


def _normalize_tokens(s: str) -> Set[str]:
    if not s or not isinstance(s, str):
        return set()
    return set(t.strip() for t in s.replace(",", " ").split() if t.strip())


def _overlap_ratio(a: Set[str], b: Set[str]) -> float:
    if not b:
        return 0.0
    return len(a & b) / len(b)


def compute_personalized_soft_score(
    query_slots: Dict[str, Any],
    qual_metadata: Dict[str, Any],
    profile: Optional[UserProfile] = None,
    config: Optional[Dict[str, float]] = None,
    acquired_meta: Optional[Dict[int, Dict[str, Any]]] = None,
) -> float:
    """
    사용자 프로필 기반 개인화 가산/감점.
    - 전공 일치: +major_bonus
    - 즐겨찾기 자격증과 동일 분야: +favorite_field_bonus
    - 이미 취득한 자격증과 동일: acquired_penalty (강한 감점, exact exclude)
    - 취득 자격과 같은 분야 + 더 높은 난이도: +next_step_bonus (다음 단계)
    - 학년-난이도 적합: +grade_difficulty_bonus
    - 너무 어려운 자격증: far_too_difficult_penalty
    - 고학년 + 너무 쉬운 자격증: far_too_easy_penalty (보조)
    profile 없으면 0 반환.
    """
    if not profile:
        return 0.0

    cfg = config or {}
    major_bonus = float(cfg.get("major_bonus", DEFAULT_MAJOR_BONUS))
    favorite_field_bonus = float(cfg.get("favorite_field_bonus", DEFAULT_FAVORITE_FIELD_BONUS))
    acquired_penalty = float(cfg.get("acquired_penalty", DEFAULT_ACQUIRED_PENALTY))
    next_step_bonus = float(cfg.get("next_step_bonus", DEFAULT_NEXT_STEP_BONUS))
    grade_difficulty_bonus = float(cfg.get("grade_difficulty_bonus", DEFAULT_GRADE_DIFFICULTY_BONUS))
    far_too_difficult_penalty = float(cfg.get("far_too_difficult_penalty", DEFAULT_FAR_TOO_DIFFICULT_PENALTY))
    far_too_easy_penalty = float(cfg.get("far_too_easy_penalty", DEFAULT_FAR_TOO_EASY_PENALTY))

    score = 0.0
    applied_major = 0.0
    applied_fav = 0.0
    applied_acq = 0.0
    applied_next = 0.0
    applied_grade = 0.0
    applied_far = 0.0
    applied_easy = 0.0

    qual_id = qual_metadata.get("qual_id")
    if qual_id is None:
        return 0.0

    # 이미 취득한 자격증과 동일 → 강한 감점 (exact exclude)
    acquired_ids: List[int] = list(profile.get("acquired_qual_ids") or [])
    if acquired_ids and qual_id in acquired_ids:
        score += acquired_penalty
        applied_acq = acquired_penalty
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "personalized_soft qual_id=%s acquired_penalty=%s", qual_id, applied_acq,
            )
        return score

    # 전공 일치 (profile.major vs qual related_majors). 둘 다 major_category로 정규화 후 비교.
    profile_major = (profile.get("major") or "").strip()
    if profile_major:
        q_major_norm = normalize_major(profile_major)
        qual_majors = qual_metadata.get("related_majors") or []
        if isinstance(qual_majors, list):
            qual_major_set = set()
            for m in qual_majors:
                n = normalize_major(str(m).strip())
                if n:
                    qual_major_set.add(n)
        else:
            qual_major_set = {normalize_major(str(qual_majors).strip())} if str(qual_majors).strip() else set()
        if q_major_norm and qual_major_set and q_major_norm in qual_major_set:
            score += major_bonus
            applied_major = major_bonus

    # 즐겨찾기 자격증과 같은 분야 (qual main_field/ncs_large가 favorite_field_tokens와 겹침)
    favorite_field_tokens: Set[str] = set()
    for t in profile.get("favorite_field_tokens") or []:
        favorite_field_tokens |= _normalize_tokens(str(t))
    if favorite_field_tokens:
        qual_job = _normalize_tokens(
            str(qual_metadata.get("main_field") or "") + " " + str(qual_metadata.get("ncs_large") or "")
        )
        if qual_job and _overlap_ratio(qual_job, favorite_field_tokens) > 0:
            score += favorite_field_bonus
            applied_fav = favorite_field_bonus

    # 다음 단계 보너스: 취득 자격과 같은 분야(main_field/ncs_large) + 후보 난이도가 취득보다 높음
    cand_diff = qual_metadata.get("avg_difficulty")
    if acquired_meta and cand_diff is not None:
        try:
            cand_diff_f = float(cand_diff)
            qual_mf = _normalize_tokens(str(qual_metadata.get("main_field") or ""))
            qual_ncs = _normalize_tokens(str(qual_metadata.get("ncs_large") or ""))
            for aid in acquired_ids:
                am = acquired_meta.get(aid)
                if not am:
                    continue
                acq_diff = am.get("avg_difficulty")
                if acq_diff is None:
                    continue
                acq_diff_f = float(acq_diff)
                if cand_diff_f <= acq_diff_f + 0.5:
                    continue
                am_mf = _normalize_tokens(str(am.get("main_field") or ""))
                am_ncs = _normalize_tokens(str(am.get("ncs_large") or ""))
                if (qual_mf & am_mf) or (qual_ncs & am_ncs):
                    score += next_step_bonus
                    applied_next = next_step_bonus
                    break
        except (TypeError, ValueError):
            pass

    # 학년-난이도 적합도 (1~2학년: 입문/기초형 가산, 3~4학년: 실무/중급형 가산)
    grade_level = profile.get("grade_level")
    avg_difficulty = qual_metadata.get("avg_difficulty")
    if grade_level is not None and avg_difficulty is not None:
        try:
            g = int(grade_level)
            diff = float(avg_difficulty)
            if g <= 2:
                if diff <= 5.5:
                    score += grade_difficulty_bonus
                    applied_grade = grade_difficulty_bonus
                elif diff >= 8.0:
                    score += far_too_difficult_penalty
                    applied_far = far_too_difficult_penalty
            else:
                if 5.0 <= diff <= 7.5:
                    score += grade_difficulty_bonus
                    applied_grade = grade_difficulty_bonus
                elif diff >= 9.0:
                    score += far_too_difficult_penalty * 0.5
                    applied_far = far_too_difficult_penalty * 0.5
                elif g >= 3 and diff <= 4.0:
                    score += far_too_easy_penalty
                    applied_easy = far_too_easy_penalty
        except (TypeError, ValueError):
            pass

    if score != 0 and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "personalized_soft qual_id=%s major=%s fav=%s acq=%s next=%s grade=%s far=%s easy=%s",
            qual_id, applied_major, applied_fav, applied_acq, applied_next, applied_grade, applied_far, applied_easy,
        )
    return score


def merge_difficulty_into_metadata(
    metadata_by_qual: Dict[int, Dict[str, Any]],
    difficulty_by_qual: Dict[int, float],
) -> None:
    """metadata_by_qual 각 항목에 avg_difficulty를 넣어 준다 (in-place)."""
    for qid, meta in metadata_by_qual.items():
        if qid in difficulty_by_qual:
            meta["avg_difficulty"] = difficulty_by_qual[qid]
        meta["qual_id"] = qid
