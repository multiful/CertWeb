from typing import Dict


def build_canonical_intent_key(slots: Dict[str, str], raw_query: str, rewrite: str) -> str:
    """
    Reranker 학습/평가용 canonical intent key 생성용 함수.

    이 단계에서는 시그니처와 역할만 정의하고, 실제 구현은 후속 단계에서 채운다.
    - 동일 의도(도메인/희망직무/목적/후속추천 여부/자격명 포함 여부 등)는 같은 key로 묶인다.
    - 텍스트 표면형(템플릿 문장 변형, 조사 등)은 key에 직접 사용하지 않는다.
    """
    raise NotImplementedError

