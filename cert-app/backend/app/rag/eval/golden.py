"""
골든셋 로드: JSONL 파일을 읽어 평가용 리스트 반환.
reco 형식(query_text, expected_certs 등)은 common.normalize_gold_labels에서 정규화.
"""
import json
from pathlib import Path
from typing import Any, Dict, List


def load_golden(golden_path: str) -> List[Dict[str, Any]]:
    """
    JSONL 골든 파일을 읽어 행 단위 dict 리스트 반환.
    """
    path = Path(golden_path)
    if not path.exists():
        return []

    # 기존엔 utf-8만 가정했는데, 실제 생성/전송 과정에서 인코딩이 섞이면서
    # query_text/major 등이 모지베이크로 들어오는 문제가 확인됨.
    # 여기서는 파일 앞부분을 기반으로 인코딩을 후보군에서 선택한다.
    def _detect_encoding_from_prefix(raw_lines: list[bytes]) -> str:
        candidates = [
            "utf-8-sig",
            "utf-8",
            "utf-16-le",
            "utf-16-be",
            "cp949",
            "euc-kr",
        ]

        best = ("utf-8", -1)
        for enc in candidates:
            ok = 0
            total = 0
            for b in raw_lines[:40]:
                if not b or b.strip() == b"":
                    continue
                total += 1
                try:
                    s = b.decode(enc, errors="strict").strip()
                    if not s:
                        continue
                    json.loads(s)
                    ok += 1
                except Exception:
                    continue
            if total > 0 and ok > best[1]:
                best = (enc, ok)
        return best[0]

    # prefix line 샘플링 (바이트 단위)
    prefix_lines: list[bytes] = []
    with open(path, "rb") as bf:
        for _ in range(60):
            ln = bf.readline()
            if not ln:
                break
            prefix_lines.append(ln)

    chosen_encoding = _detect_encoding_from_prefix(prefix_lines)
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding=chosen_encoding, errors="strict") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
