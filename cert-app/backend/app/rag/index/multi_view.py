"""
자격증별 멀티뷰 임베딩: job / major / skill / recommendation 뷰.
한 qual당 여러 semantic view를 만들 수 있는 구조 (설정으로 비활성, 1차는 스켈레톤).
populate에서 RAG_MULTIVIEW_ENABLE=True 시 view별 row 저장, retrieval 시 qual_id 기준 MaxP merge.
"""
from typing import Dict, List, Tuple

# populate에서 사용할 view 타입 상수 (certificates_vectors.metadata 또는 view_type 컬럼)
VIEW_TYPE_JOB = "job_view"
VIEW_TYPE_MAJOR = "major_view"
VIEW_TYPE_SKILL = "skill_view"
VIEW_TYPE_RECOMMENDATION = "recommendation_view"
MULTIVIEW_TYPES = [VIEW_TYPE_JOB, VIEW_TYPE_MAJOR, VIEW_TYPE_SKILL, VIEW_TYPE_RECOMMENDATION]


def build_views_for_qual(
    row: dict,
    related_majors: list[str],
    job_skill_fn,
) -> Dict[str, str]:
    """
    한 자격증에 대해 4개 semantic view 텍스트 생성.
    row: qualification row dict. job_skill_fn(main_field, ncs_large) -> str (기존 _job_skill_keywords 등).
    """
    qual_name = str(row.get("qual_name") or "").strip()
    main_field = str(row.get("main_field") or "").strip()
    ncs_large = str(row.get("ncs_large") or "").strip()
    job_skill = (job_skill_fn(main_field, ncs_large) if job_skill_fn else (main_field + " " + ncs_large)).strip()
    major_str = ", ".join(related_majors) if related_majors else (main_field or "")

    job_view = f"자격증명: {qual_name}. 관련 직무: {job_skill}" if job_skill else f"자격증명: {qual_name}. 분야: {main_field or ncs_large}"
    major_view = f"자격증명: {qual_name}. 관련 전공: {major_str}" if major_str else f"자격증명: {qual_name}. 분야: {main_field}"
    skill_view = f"자격증명: {qual_name}. 관련 기술: {job_skill}" if job_skill else f"자격증명: {qual_name}. {main_field or ncs_large}"
    recommendation_view = f"자격증명: {qual_name}. IT 취업 준비, 실무 역량 증명용 자격증." if "정보" in (main_field or ncs_large or "") or "데이터" in (main_field or ncs_large or "") else f"자격증명: {qual_name}. 취업·실무 입문용 자격증."

    return {
        VIEW_TYPE_JOB: job_view,
        VIEW_TYPE_MAJOR: major_view,
        VIEW_TYPE_SKILL: skill_view,
        VIEW_TYPE_RECOMMENDATION: recommendation_view,
    }


def merge_vector_results_by_qual_maxp(
    chunk_scores: List[Tuple[str, float]],
) -> List[Tuple[str, int, float]]:
    """
    여러 view(chunk)별 (chunk_id, score) 리스트를 qual_id 기준으로 merge.
    동일 qual_id에 대해 최대 점수(MaxP)만 취해 (qual_id, score) 형태로 반환.
    chunk_id 형식: "qual_id:chunk_index".
    반환: [(chunk_id, score), ...] (chunk_id=qual_id:0). hybrid 파이프라인과 호환.
    """
    by_qual: Dict[int, float] = {}
    for cid, score in chunk_scores:
        if ":" in cid:
            try:
                qid = int(cid.split(":")[0])
                by_qual[qid] = max(by_qual.get(qid, 0.0), float(score))
            except ValueError:
                continue
    return [(f"{qid}:0", sc) for qid, sc in sorted(by_qual.items(), key=lambda x: -x[1])]
