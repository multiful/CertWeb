"""
Contrastive 학습용 데이터 스키마.
query / positive / hard_negative qual_id 목록 및 triplet 변환.
sentence-transformers 등 contrastive fine-tuning에서 사용 가능.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContrastiveSample:
    """한 질의에 대한 positive / hard negative 자격증 ID 집합."""
    query: str
    positive_qual_ids: List[int]
    hard_negative_qual_ids: List[int]
    sample_id: Optional[str] = None
    # 추후 LLM 추출 시 슬롯 보존
    query_slots: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "positive_qual_ids": self.positive_qual_ids,
            "hard_negative_qual_ids": self.hard_negative_qual_ids,
            "sample_id": self.sample_id,
            "query_slots": self.query_slots,
        }


@dataclass
class ContrastiveTriplet:
    """(query, positive_doc_id, negative_doc_id) 단위. pairwise loss용."""
    query: str
    positive_qual_id: int
    negative_qual_id: int
    sample_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "positive_qual_id": self.positive_qual_id,
            "negative_qual_id": self.negative_qual_id,
            "sample_id": self.sample_id,
        }


def contrastive_sample_to_triplets(sample: ContrastiveSample) -> List[ContrastiveTriplet]:
    """한 샘플을 (query, pos_id, neg_id) triplet 리스트로 펼침."""
    out: List[ContrastiveTriplet] = []
    for pos_id in sample.positive_qual_ids:
        for neg_id in sample.hard_negative_qual_ids:
            if pos_id == neg_id:
                continue
            out.append(
                ContrastiveTriplet(
                    query=sample.query,
                    positive_qual_id=pos_id,
                    negative_qual_id=neg_id,
                    sample_id=sample.sample_id,
                )
            )
    return out
