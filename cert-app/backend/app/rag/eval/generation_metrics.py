"""Generation 지표 (간단 규칙): citation_coverage, hallucination_proxy."""
import re
from typing import List


def citation_coverage(answer: str, citation_chunk_ids: List[str]) -> float:
    """답변 문장 중 citation [chunk_id] 포함 비율. 문장은 . ! ? 로 split."""
    if not answer or not citation_chunk_ids:
        return 0.0
    sentences = re.split(r"[.!?]\s+", answer)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    pattern = re.compile(r"\[\d+:\d+\]")  # [qual_id:chunk_index]
    cited = sum(1 for s in sentences if pattern.search(s))
    return cited / len(sentences)


def hallucination_proxy(answer: str, citation_chunk_ids: List[str]) -> float:
    """citation 없는 주장 문장 비율 (간단 규칙: 문장에 [x:y] 없으면 주장)."""
    if not answer:
        return 0.0
    sentences = re.split(r"[.!?]\s+", answer)
    sentences = [s.strip() for s in sentences if s.strip() and len(s) > 10]
    if not sentences:
        return 0.0
    pattern = re.compile(r"\[\d+:\d+\]")
    uncited = sum(1 for s in sentences if not pattern.search(s))
    return uncited / len(sentences)
