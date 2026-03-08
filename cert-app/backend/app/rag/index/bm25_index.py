"""
BM25 인덱스: rank_bm25 사용, 디스크 저장(pickle)으로 메모리 폭발 방지.
한글: 문자 2-gram 토크나이저 옵션 (용량 적고 별도 패키지 없음).
로컬 CPU만 사용.
"""
import pickle
import re
from pathlib import Path
from typing import List, Optional, Tuple

from rank_bm25 import BM25Okapi

try:
    from app.rag.utils.query_processor import process_query_for_bm25
except Exception:
    process_query_for_bm25 = None

# 한글 음절 범위 (가~힣)
_HANGUL_RE = re.compile(r"[\uAC00-\uD7A3]+")
# 한글 한 글자 이상 연속
_HANGUL_SPAN_RE = re.compile(r"[\uAC00-\uD7A3]+")


def _segment_by_script(part: str) -> List[str]:
    """한글 연속 구간 / 비한글 연속 구간으로 분리. 공백은 이미 split으로 제거된 토큰 단위."""
    if not part:
        return []
    segments: List[str] = []
    i = 0
    while i < len(part):
        m = _HANGUL_SPAN_RE.match(part[i:])
        if m:
            segments.append(m.group(0))
            i += len(m.group(0))
        else:
            # 비한글: 영문/숫자/기호 연속까지 한 덩어리
            j = i
            while j < len(part) and not _HANGUL_RE.match(part[j]):
                j += 1
            if j > i:
                segments.append(part[i:j])
            i = j
    return segments


def tokenize_korean_ngram(text: str, n: int = 2) -> List[str]:
    """
    한국어 패치: 한글 연속 구간만 문자 n-gram, 그 외(영문/숫자/기호)는 덩어리 그대로 토큰.
    공백 기준 1차 분리 후, 각 토큰을 스크립트별로 재분리하여 한글만 2-gram 적용.
    """
    if not text or not text.strip():
        return []
    tokens: List[str] = []
    for part in text.strip().split():
        if not part:
            continue
        for seg in _segment_by_script(part):
            if not seg:
                continue
            if _HANGUL_RE.fullmatch(seg) and len(seg) >= n:
                for i in range(len(seg) - n + 1):
                    tokens.append(seg[i : i + n])
            elif _HANGUL_RE.fullmatch(seg):
                tokens.append(seg)  # 한글 1글자만 있으면 그대로
            else:
                tokens.append(seg.lower())  # 영문/숫자/기호 덩어리
    return tokens


class BM25Index:
    """BM25 인덱스: 빌드 후 디스크에 저장, 로드하여 검색."""

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = index_path
        self._bm25: Optional[BM25Okapi] = None
        self._doc_ids: List[str] = []  # chunk_id 또는 (qual_id, chunk_index) 문자열
        self._corpus: List[str] = []

    def build(
        self,
        documents: List[dict],
        use_korean_ngram: bool = False,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        """
        documents: [{"chunk_id": str, "text": str}, ...]
        use_korean_ngram: False(기본)=공백 기준 토큰만(plain BM25), True=한글 2-gram.
        k1, b: BM25 파라미터 (k1=1.5, b=0.75 기본).
        """
        self._doc_ids = [d.get("chunk_id", str(i)) for i, d in enumerate(documents)]
        self._corpus = [d.get("text", "").replace("\n", " ") for d in documents]
        if use_korean_ngram:
            tokenized = [tokenize_korean_ngram(doc, n=2) for doc in self._corpus]
        else:
            tokenized = [doc.split() for doc in self._corpus]
        tokenized = [t if t else ["_"] for t in tokenized]
        if not tokenized:
            self._bm25 = None
            return
        self._bm25 = BM25Okapi(tokenized, k1=k1, b=b)
        self._use_korean_ngram = use_korean_ngram
        self._k1, self._b = k1, b

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """(chunk_id, score) 리스트 반환."""
        if not self._bm25 or not self._doc_ids:
            return []
        use_ngram = getattr(self, "_use_korean_ngram", False)
        q_tokens = tokenize_korean_ngram(query, n=2) if use_ngram else query.strip().split()
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(self._doc_ids[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    def search_with_expansion(
        self,
        query: str,
        k: int = 10,
        expansion_top_n: int = 30,
        rrf_k: int = 60,
    ) -> List[Tuple[str, float]]:
        """
        동의어/약어 확장 쿼리로 여러 번 검색 후 RRF로 병합.
        process_query_for_bm25 미사용 시 단순 search와 동일.
        """
        if not process_query_for_bm25:
            return self.search(query, k=k)
        _, expansions = process_query_for_bm25(query, expand=True, max_expansions=5)
        if len(expansions) <= 1:
            return self.search(query, k=k)
        rrf_scores: dict = {}
        for exp_q in expansions:
            raw = self.search(exp_q, k=expansion_top_n)
            for rank, (doc_id, _) in enumerate(raw, start=1):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (rrf_k + rank)
        sorted_ids = sorted(rrf_scores.keys(), key=lambda d: -rrf_scores[d])[:k]
        return [(doc_id, float(rrf_scores[doc_id])) for doc_id in sorted_ids]

    def save(self, path: Optional[Path] = None) -> None:
        path = path or self.index_path
        if not path:
            raise ValueError("index_path required for save")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "bm25": self._bm25,
                    "doc_ids": self._doc_ids,
                    "corpus": self._corpus,
                    "use_korean_ngram": getattr(self, "_use_korean_ngram", False),
                    "k1": getattr(self, "_k1", 1.5),
                    "b": getattr(self, "_b", 0.75),
                },
                f,
            )

    def load(self, path: Optional[Path] = None) -> None:
        path = path or self.index_path
        if not path or not Path(path).exists():
            self._bm25 = None
            self._doc_ids = []
            self._corpus = []
            self._use_korean_ngram = False
            return
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._bm25 = data.get("bm25")
        self._doc_ids = data.get("doc_ids", [])
        self._corpus = data.get("corpus", [])
        self._use_korean_ngram = data.get("use_korean_ngram", False)
        self._k1 = data.get("k1", 1.5)
        self._b = data.get("b", 0.75)
