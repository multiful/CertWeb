"""
Contrastive embedding 학습 데이터 및 스키마.
Hard negative 기반 triplet/pairwise 포맷으로 추천형 retrieval fine-tuning 준비.
"""
from app.rag.contrastive.schema import (
    ContrastiveSample,
    ContrastiveTriplet,
    contrastive_sample_to_triplets,
)

__all__ = [
    "ContrastiveSample",
    "ContrastiveTriplet",
    "contrastive_sample_to_triplets",
]
