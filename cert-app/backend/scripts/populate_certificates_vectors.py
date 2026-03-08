"""
RAG용 certificates_vectors 테이블을 DB의 qualification 데이터로 채웁니다.
- Recursive Chunking (chunk 1000, overlap 150) + [자격증명: {name}] 태깅
- content_hash(SHA-256)로 변경분만 임베딩 호출 (중복 제거)

실행: cert-app/backend 에서 (openai 패키지 필요)
  uv run python scripts/populate_certificates_vectors.py
  또는: 가상환경 활성화 후 python scripts/populate_certificates_vectors.py

옵션:
  --truncate   기존 certificates_vectors 전체 삭제 후 채우기 (기본: 기존 qual_id 행만 갱신)
  --batch N    임베딩 API 배치 크기 (기본 50)
  --dry-run    DB 쓰기 없이 content/청크 건수만 출력

사전: migrations/rag_hybrid_content_hash_hnsw.sql 적용 필요 (content_hash, chunk_index, content_tsv).
      migrations/add_dense_content_column.sql 적용 시 dense 추천형 문서 저장 (dense_content 컬럼).
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

# Chunk 설정 (문맥 보존)
# Hybrid 구조에서는 자격 전체 맥락을 조금 더 길게 가져가되 overlap은 약간 줄여서 중복을 완화한다.
CHUNK_SIZE = 1300
CHUNK_OVERLAP = 120
CONTEXT_TAG_PREFIX = "[자격증명: "


# 추천형 BM25: BM25F 스타일 반복 횟수 (job > major > skill > purpose > name > description)
BM25_RECO_JOB_REPEAT = 4
BM25_RECO_MAJOR_REPEAT = 3
BM25_RECO_SKILL_REPEAT = 3
BM25_RECO_PURPOSE_REPEAT = 2
BM25_RECO_NAME_REPEAT = 2
BM25_RECO_DESC_REPEAT = 1
BM25_RECO_PURPOSE_DEFAULT = "취업 실무 입문 자격증 커리어"

# main_field / ncs_large → 관련 직무·스킬 키워드 (추천형 문서 설계)
# failure 기반 보강: 정보처리·전산·데이터베이스 축 추가, 오타 수정(정볳보안→정보보안)
FIELD_TO_JOB_SKILL = {
    "정보통신": "정보처리 정보처리기사 IT 개발 시스템 데이터베이스 소프트웨어 프로그래밍 네트워크 전산",
    "정보기술개발": "개발자 소프트웨어엔지니어 시스템엔지니어 IT운영 프로그래밍 데이터베이스 정보처리 전산",
    "정보처리": "정보처리기사 정보처리산업기사 SQLD 개발 시스템 데이터베이스 전산",
    "데이터분석": "데이터분석가 데이터엔지니어 데이터베이스 SQL 분석 빅데이터 ADsP",
    "데이터베이스": "SQL SQLD 데이터베이스 정보처리 개발",
    "시스템관리": "시스템관리자 리눅스 서버운영 네트워크 인프라 정보처리",
    "네트워크관리": "네트워크관리자 시스템운영 인프라",
    "정보보안": "보안기사 보안 엔지니어 정보보안",
    "전기·전자": "전기기사 전자기사 전기설계 전자개발",
    "전기설계": "전기기사 전기설계 설비",
    "전자개발": "전자기사 전자개발 반도체",
    "기계": "기계기사 기계설계",
    "건설": "건축기사 토목기사 건축 토목",
    "경제·금융": "회계 금융 재무",
    "보건·의료": "간호 의료 의사 약사",
    # 18골든 failure-driven: 전공/직무 축 보강 (문서 payload)
    "산업데이터공학": "데이터 공학 정보시스템 전산 정보처리 SQLD ADsP",
    "시스템운영": "시스템 운영 개발 서버 정보처리 전산",
    "IT서비스": "IT 서비스 운영 시스템 정보처리",
}

# 2-3: bm25_text purpose 세분화. 자격증/분야별 차등 목적 문구 → 문서 간 구분력 강화.
QUAL_NAME_TO_PURPOSE: dict[str, str] = {
    "정보처리기사": "IT 개발 직무 준비 정보처리 취업",
    "정보처리산업기사": "IT 개발 입문 정보처리 취업",
    "SQL개발자": "데이터베이스 실무 SQL 개발",
    "데이터분석준전문가": "데이터 분석 실무 빅데이터 ADsP",
    "빅데이터분석기사": "데이터 분석 실무 빅데이터 전문기술 심화",
    "컴퓨터활용능력": "OA 문서 실무 공기업 사무직 가산점",
    "네트워크관리사": "전산 시스템 운영 네트워크",
    "리눅스마스터": "전산 시스템 운영 서버",
}
# main_field / ncs_large 기반 purpose fallback
FIELD_TO_PURPOSE: dict[str, str] = {
    "정보통신": "IT 개발 직무 준비 정보처리",
    "정보기술개발": "IT 개발 직무 준비",
    "정보처리": "IT 개발 직무 준비 정보처리",
    "데이터분석": "데이터 분석 실무 빅데이터",
    "데이터베이스": "데이터베이스 실무 SQL",
    "시스템관리": "전산 시스템 운영",
    "네트워크관리": "전산 시스템 운영 네트워크",
    "정보보안": "전산 전문기술 심화 보안",
    "경제·금융": "공기업 사무직 가산점 회계 금융",
    "전기·전자": "전문기술 심화 전기 전자",
    "기계": "전문기술 심화 기계",
    "건설": "전문기술 심화 건축 토목",
    "보건·의료": "전문기술 심화 의료",
}


def _purpose_by_field(main_field: str, ncs_large: str) -> str:
    """main_field/ncs_large 기반 purpose 문구. 2-3 purpose 세분화 fallback."""
    for key, phrase in FIELD_TO_PURPOSE.items():
        if key in (main_field or "") or key in (ncs_large or ""):
            return phrase
    return BM25_RECO_PURPOSE_DEFAULT


def _get_purpose_for_bm25(qual_name: str, main_field: str, ncs_large: str) -> str:
    """자격증별 → 분야별 → 기본 순으로 purpose 문구 선택. 2-3."""
    qn = (qual_name or "").strip()
    for qname, phrase in QUAL_NAME_TO_PURPOSE.items():
        if qname in qn or qn in qname:
            return phrase
    return _purpose_by_field(main_field, ncs_large)


def _job_skill_keywords(main_field: str, ncs_large: str) -> str:
    """main_field, ncs_large에서 직무·스킬 키워드 추출 (추천형 매칭용)."""
    parts = []
    for key, keywords in FIELD_TO_JOB_SKILL.items():
        if key in (main_field or "") or key in (ncs_large or ""):
            parts.append(keywords)
    return " ".join(parts) if parts else ((main_field or "") + " " + (ncs_large or ""))


def _dedupe_tokens(s: str) -> str:
    """공백 기준 토큰 dedupe (순서 유지). 필드 내부 중복 제거용. repetition 블록은 유지."""
    if not s or not s.strip():
        return s.strip()
    tokens = s.split()
    return " ".join(dict.fromkeys(tokens))


def build_bm25_text(row: dict, related_majors: list[str] = None) -> str:
    """
    추천형 BM25 문서 (BM25F 스타일 필드 가중치).
    job > major > skill > purpose > name > description 순 부스팅으로 Recall@20·Hit@20 강화.
    필드 라벨(직무/전공/스킬/목적/이름/설명)을 접두사로 넣어 구조를 명시하고 질의와의 매칭을 보강.
    반복 블록 횟수는 유지하되, 각 필드 내부는 토큰 dedupe로 정보량 정리.
    """
    qual_name = str(row.get("qual_name") or "").strip()
    main_field = str(row.get("main_field") or "").strip()
    ncs_large = str(row.get("ncs_large") or "").strip()
    qual_type = str(row.get("qual_type") or "").strip()
    grade_code = str(row.get("grade_code") or "").strip()
    job_skill_raw = _job_skill_keywords(main_field, ncs_large).strip() or (main_field + " " + ncs_large).strip()
    qn = (qual_name or "").strip()
    for qname, boost in QUAL_NAME_TO_JOB_SKILL_BOOST.items():
        if qname in qn or qn in qname:
            job_skill_raw = (job_skill_raw + " " + boost).strip()
            break
    job_skill = _dedupe_tokens(job_skill_raw)
    major_str = _dedupe_tokens(" ".join(related_majors) if related_majors else "")
    purpose_str = _dedupe_tokens(_get_purpose_for_bm25(qual_name, main_field, ncs_large))
    # 이름 필드에 별칭 포함 → cert_name_included/짧은 질의 sparse recall 개선
    name_parts = [qual_name] if qual_name else []
    if qual_name:
        qn_norm = (qual_name or "").replace(" ", "")
        for k, alias in QUAL_NAME_ALIASES.items():
            if k.replace(" ", "") in qn_norm or qn_norm in k.replace(" ", ""):
                name_parts.append(alias)
    name_and_alias = _dedupe_tokens(" ".join(name_parts))
    desc_str = " ".join([x for x in [main_field, qual_type, grade_code] if x]).strip() or "자격증"
    desc_str = _dedupe_tokens(desc_str)

    def repeat(prefix: str, s: str, n: int) -> str:
        block = (prefix + " " + (s or "").strip()).strip()
        return (" " + block + " ") * n if block else ""

    parts = []
    parts.append(repeat("직무", job_skill, BM25_RECO_JOB_REPEAT))
    parts.append(repeat("전공", major_str, BM25_RECO_MAJOR_REPEAT))
    parts.append(repeat("스킬", job_skill, BM25_RECO_SKILL_REPEAT))
    parts.append(repeat("목적", purpose_str, BM25_RECO_PURPOSE_REPEAT))
    parts.append(repeat("이름", name_and_alias, BM25_RECO_NAME_REPEAT))
    parts.append(repeat("설명", desc_str, BM25_RECO_DESC_REPEAT))

    text = " ".join(parts).replace("\n", " ").strip()
    return text or (qual_name or "자격증")


def build_embed_content(row: dict, related_majors: list[str] = None) -> str:
    """
    임베딩용 콘텐츠: 구조화/태그 포함 유지.
    벡터 검색에 최적화된 형태. (FTS/content 유지용; dense는 build_dense_recommendation_document 사용)
    **메타데이터 규칙**: "자격증명"은 한 번만 사용. 별칭은 반드시 "별칭:" 레이블만 사용 (절대 "자격증명"으로 별칭 표기 금지).
    """
    qual_name = str(row.get("qual_name") or "").strip()
    qual_type = str(row.get("qual_type") or "").strip()
    main_field = str(row.get("main_field") or "").strip()
    ncs_large = str(row.get("ncs_large") or "").strip()
    managing_body = str(row.get("managing_body") or "").strip()
    grade_code = str(row.get("grade_code") or "").strip()

    parts = []
    if qual_name:
        parts.append(f"자격증명: {qual_name}")
    # 별칭은 "별칭:" 레이블만 사용 (자격증명 중복 금지)
    alias = (QUAL_NAME_ALIASES.get(qual_name) or "") if qual_name else ""
    if alias:
        parts.append(f"별칭: {alias}")
    if qual_type:
        parts.append(f"유형: {qual_type}")
    if main_field:
        parts.append(f"분야: {main_field}")
    if ncs_large:
        parts.append(f"NCS분류: {ncs_large}")
    if managing_body:
        parts.append(f"시행기관: {managing_body}")
    if grade_code:
        parts.append(f"등급: {grade_code}")
    if related_majors:
        parts.append(f"관련전공: {', '.join(related_majors)}")

    return " | ".join(parts).replace("\n", " ").strip() or "자격증"


# 자격증 별칭 (추천형 dense 문서용)
QUAL_NAME_ALIASES: dict[str, str] = {
    "정보처리기사": "정처기",
    "정보처리산업기사": "정처산",
    "빅데이터분석기사": "빅분기",
    "데이터분석준전문가": "ADsP",
    "SQL개발자": "SQLD",
    "네트워크관리사": "네관사",
}

# Round2: qual_name 기반 sparse payload 보강 — "정보처리 직무", "데이터/IT" 질의 recall
# 정보처리기사/SQLD/ADsP가 main_field만으로는 질의와 약하게 매칭될 때 보강
QUAL_NAME_TO_JOB_SKILL_BOOST: dict[str, str] = {
    "정보처리기사": "정보처리 직무 정보처리기사",
    "SQL개발자(SQLD)": "SQL 데이터베이스 직무 정보처리",
    "데이터분석준전문가(ADsP)": "데이터분석 데이터 빅데이터 직무",
}


def _grade_to_difficulty(grade_code: str, qual_type: str) -> str:
    """등급/유형으로 난이도 라벨 추정. 없으면 '중'."""
    if not grade_code and not qual_type:
        return "중"
    g = (grade_code or "").strip()
    t = (qual_type or "").strip()
    if "기사" in t or "1급" in g or "기사" in g:
        return "중상"
    if "산업기사" in t or "2급" in g:
        return "중"
    if "기능사" in t or "3급" in g:
        return "중하"
    if "전문가" in t or "준전문가" in t:
        return "중상"
    return "중"


def build_dense_recommendation_document(row: dict, related_majors: list[str] = None) -> str:
    """
    Dense retrieval 전용 추천형 구조화 문서.
    직무/전공/기술/추천대상/활용도/난이도 등을 명시해 추천 의미를 드러내고,
    contrastive 학습 데이터로도 재사용 가능한 형식.
    자격증명은 한 번만, 별칭은 "별칭:" 레이블만 사용 (content 중복 방지).
    """
    qual_name = str(row.get("qual_name") or "").strip()
    qual_type = str(row.get("qual_type") or "").strip()
    main_field = str(row.get("main_field") or "").strip()
    ncs_large = str(row.get("ncs_large") or "").strip()
    managing_body = str(row.get("managing_body") or "").strip()
    grade_code = str(row.get("grade_code") or "").strip()

    job_skill = _job_skill_keywords(main_field, ncs_large).strip() or (main_field + " " + ncs_large).strip()
    major_str = ", ".join(related_majors) if related_majors else (main_field or "")
    alias = QUAL_NAME_ALIASES.get(qual_name) or ""
    difficulty = _grade_to_difficulty(grade_code, qual_type)
    # 추천 대상: 분야·유형 기반
    target = "취업 준비생, 실무 입문, 커리어 증명"
    if "정보" in (main_field or "") or "데이터" in (main_field or ncs_large or ""):
        target = "정보처리 직무 취업 준비생, IT 취업 희망자"
    if "간호" in (qual_name or main_field or ""):
        target = "간호·의료 분야 취업 준비생"
    if "회계" in (qual_name or main_field or "") or "전산회계" in (qual_name or ""):
        target = "회계·사무 직무 취업 준비생"
    utilization = f"{main_field or '해당 분야'} 직무 기초 역량 증명"
    if job_skill:
        utilization = f"{job_skill.strip().split()[0]} 등 실무 역량 증명"

    # 추천 판정문: "이 자격증은 어떤 사람에게 왜 추천되는가"를 문장으로 먼저 배치 (dense = 추천 판정문 중심)
    major_reco = f"이 자격증은 {major_str} 등 관련 전공 학생에게 적합합니다." if major_str else "관련 전공 학생에게 추천됩니다."
    job_reco = f"{job_skill or main_field or ncs_large or '해당 분야'} 직무 준비에 직접 연결됩니다."
    level_reco = "입문용·기초용으로 적합합니다." if difficulty == "중하" else ("심화·실무용으로 적합합니다." if difficulty == "중상" else "입문부터 실무까지 단계별 준비에 적합합니다.")
    purpose_reco = "취업용·실무용·공기업 채용 준비에 적합합니다." if "취업" in target or "실무" in target else "취업·실무·커리어 증명에 활용 가능합니다."
    companion_reco = "같은 분야 기초 자격증과 함께 준비하면 좋습니다." if job_skill else "관련 분야 자격증과 함께 준비할 수 있습니다."

    # 1) 추천 판정문 블록 먼저 (의미 검색에 반응하도록)
    judgment_lines = [major_reco, job_reco, level_reco, purpose_reco, companion_reco]
    # 2) 식별·속성 (최소한으로)
    attr_lines = [
        f"자격증명: {qual_name}",
        f"별칭: {alias}" if alias else None,
        f"관련 직무: {job_skill}" if job_skill else f"관련 직무: {main_field or ncs_large or '해당 분야'}",
        f"관련 전공: {major_str}" if major_str else None,
        f"추천 대상: {target}",
        f"난이도: {difficulty}",
        f"설명: {qual_type or ''} {main_field or ''} {ncs_large or ''} 자격증. {managing_body or '국가/공인 시행'}.".strip(),
    ]
    lines = judgment_lines + [x for x in attr_lines if x]
    text = " ".join(l for l in lines if l).strip()
    return text or qual_name or "자격증"


def load_major_qualification_map(db) -> dict[int, list[str]]:
    """major_qualification_map 테이블에서 qual_id별 관련 전공 목록을 조회."""
    try:
        rows = db.execute(text("""
            SELECT qual_id, major
            FROM major_qualification_map
            ORDER BY qual_id, score DESC
        """)).fetchall()
        result: dict[int, list[str]] = {}
        for r in rows:
            qid = r.qual_id
            major = str(r.major or "").strip()
            if major:
                if qid not in result:
                    result[qid] = []
                if len(result[qid]) < 5:  # 상위 5개 전공만 포함
                    result[qid].append(major)
        return result
    except Exception as e:
        logger.warning("Could not load major_qualification_map: %s", e)
        return {}


def content_hash(text_content: str) -> str:
    """SHA-256 해시. 변경 시에만 임베딩 호출용."""
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()


def chunk_with_tag(full_content: str, qual_name: str) -> list[str]:
    """
    Recursive chunking (문단 → 문장 → 마침표 순) + 각 청크 앞에 [자격증명: {name}] 태그.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    tag = f"{CONTEXT_TAG_PREFIX}{qual_name}] "
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        length_function=len,
    )
    raw_chunks = splitter.split_text(full_content.strip() or "자격증")
    return [tag + c.strip() if not c.strip().startswith(CONTEXT_TAG_PREFIX) else c.strip() for c in raw_chunks]


def get_embeddings_batch(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """OpenAI Embedding API 배치 호출 (한 번에 여러 텍스트)."""
    if not texts:
        return []
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    texts = [t.replace("\n", " ").strip() or " " for t in texts]
    resp = client.embeddings.create(input=texts, model=model)
    return [d.embedding for d in resp.data]


def main():
    parser = argparse.ArgumentParser(description="Populate certificates_vectors from qualification table (chunked + hash)")
    parser.add_argument("--truncate", action="store_true", help="TRUNCATE certificates_vectors before insert")
    parser.add_argument("--batch", type=int, default=50, help="Embedding batch size (default 50)")
    parser.add_argument("--dry-run", action="store_true", help="No DB write, only print counts and sample content")
    args = parser.parse_args()

    try:
        from openai import OpenAI  # noqa: F401
    except ImportError:
        logger.error(
            "패키지 'openai'가 없습니다. cert-app/backend에서 다음 중 하나로 실행하세요:\n"
            "  uv run python scripts/populate_certificates_vectors.py\n"
            "  또는: pip install openai 후 동일 명령"
        )
        sys.exit(1)

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Set it in .env")
        sys.exit(1)

    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT qual_id, qual_name, qual_type, main_field, ncs_large, managing_body, grade_code
                FROM qualification
                WHERE is_active = TRUE
                ORDER BY qual_id
            """)
        ).fetchall()
        rows = [r._mapping for r in rows] if hasattr(rows[0], "_mapping") else [dict(r) for r in rows]
        
        # 관련 전공 정보 로드 (벡터 검색 품질 개선용)
        major_map = load_major_qualification_map(db)
        logger.info("Loaded %s qualifications with major mappings for %s quals", len(rows), len(major_map))
    finally:
        db.close()

    if not rows:
        logger.warning("No active qualifications found.")
        return

    # 기존 (qual_id, chunk_index) -> content_hash (변경 여부 판단용)
    existing_hashes: dict[tuple[int, int], str] = {}
    try:
        db = SessionLocal()
        r = db.execute(text("""
            SELECT qual_id, chunk_index, content_hash FROM certificates_vectors
        """)).fetchall()
        for row in r:
            key = (row.qual_id, getattr(row, "chunk_index", 0) or 0)
            existing_hashes[key] = (row.content_hash or "")
        db.close()
    except Exception as e:
        logger.warning("Could not load existing content_hash (migration may not be applied): %s", e)

    # Dense: 1 qual당 1 row (chunk_index=0). 임베딩은 dense_content 기준, FTS는 content 유지.
    logger.info("Building dense recommendation documents for %s qualifications (1 row per qual)...", len(rows))
    all_chunks: list[dict] = []
    for r in rows:
        qual_id = r["qual_id"]
        related_majors = major_map.get(qual_id, [])
        qual_name = (r.get("qual_name") or "").strip() or "자격"

        content = build_embed_content(r, related_majors)
        bm25_full_text = build_bm25_text(r, related_majors)
        dense_content = build_dense_recommendation_document(r, related_majors)
        h = content_hash(dense_content)
        existing = existing_hashes.get((qual_id, 0))
        metadata = {
            "source": "populate_certificates_vectors",
            "qual_id": qual_id,
            "chunk_index": 0,
            "related_majors": related_majors,
        }
        all_chunks.append({
            "qual_id": qual_id,
            "name": qual_name,
            "content": content,
            "bm25_text": bm25_full_text,
            "dense_content": dense_content,
            "content_hash": h,
            "chunk_index": 0,
            "metadata": json.dumps(metadata),
            "need_embed": existing != h,
        })

    to_embed = [x for x in all_chunks if x["need_embed"]]
    logger.info("Total rows: %s, need new embedding: %s (unchanged: %s)",
                len(all_chunks), len(to_embed), len(all_chunks) - len(to_embed))

    if args.dry_run:
        logger.info("DRY RUN: would upsert %s rows. Sample:", len(all_chunks))
        for i, it in enumerate(all_chunks[:5]):
            dense = it.get("dense_content") or it["content"]
            logger.info("  [%s] qual_id=%s chunk_index=%s need_embed=%s\n      dense_content=%s...\n      bm25=%s...",
                       i, it["qual_id"], it["chunk_index"], it["need_embed"],
                       (dense[:80] + "…"),
                       (it["bm25_text"][:60] + "…"))
        return

    # --truncate 모드에서는 content hash와 무관하게 전체 재삽입
    if args.truncate:
        qual_ids_to_refresh = {it["qual_id"] for it in all_chunks}
        chunks_to_upsert = all_chunks
        to_embed_items = [c for c in all_chunks if c["need_embed"]]
        logger.info("TRUNCATE mode: forcing refresh of all %s qual_ids", len(qual_ids_to_refresh))
    else:
        # qual_id별로 하나라도 need_embed면 해당 qual 전체 재처리 (DELETE 후 INSERT)
        qual_ids_to_refresh = {it["qual_id"] for it in all_chunks if it["need_embed"]}
        chunks_to_upsert = [c for c in all_chunks if c["qual_id"] in qual_ids_to_refresh]
        to_embed_items = [c for c in chunks_to_upsert if c["need_embed"]]

    # 변경된 row만 배치 임베딩 (dense_content 기준)
    need_embed_texts = [x["dense_content"] for x in to_embed_items]
    embedding_by_content: dict[str, list[float]] = {}
    for i in range(0, len(need_embed_texts), args.batch):
        batch_texts = need_embed_texts[i : i + args.batch]
        try:
            embs = get_embeddings_batch(batch_texts)
            for t, e in zip(batch_texts, embs):
                embedding_by_content[t] = e
        except Exception as ex:
            logger.exception("Embedding batch failed at offset %s: %s", i, ex)
            raise
        logger.info("Embedded %s/%s (changed chunks)", min(i + args.batch, len(need_embed_texts)), len(need_embed_texts))
        if i + args.batch < len(need_embed_texts):
            time.sleep(0.2)

    for it in to_embed_items:
        it["embedding"] = embedding_by_content.get(it["dense_content"])

    # refresh 대상 qual 중 need_embed=False 청크는 기존 DB에서 embedding 로드하여 재사용
    existing_embeddings: dict[tuple[int, int], list[float]] = {}
    if chunks_to_upsert:
        db = SessionLocal()
        try:
            qids = list(qual_ids_to_refresh)
            rows = db.execute(text("""
                SELECT qual_id, chunk_index, embedding FROM certificates_vectors
                WHERE qual_id = ANY(:ids)
            """), {"ids": qids}).fetchall()
            for row in rows:
                key = (row.qual_id, getattr(row, "chunk_index", 0) or 0)
                emb = getattr(row, "embedding", None)
                if emb is not None:
                    if isinstance(emb, list):
                        existing_embeddings[key] = emb
                    elif isinstance(emb, str):
                        import ast
                        try:
                            existing_embeddings[key] = ast.literal_eval(emb)
                        except Exception:
                            pass
                    else:
                        existing_embeddings[key] = list(emb)
        except Exception as e:
            logger.warning("Could not load existing embeddings: %s", e)
        finally:
            db.close()

    for it in chunks_to_upsert:
        if it.get("embedding"):
            continue
        key = (it["qual_id"], it["chunk_index"])
        if key in existing_embeddings:
            it["embedding"] = existing_embeddings[key]
        else:
            # 새 row인데 아직 embedding 없음 (방어)
            it["embedding"] = get_embeddings_batch([it["dense_content"]])[0]

    if not qual_ids_to_refresh:
        logger.info("No qual_ids need refresh; skipping DB write.")
        return

    db = SessionLocal()
    try:
        if args.truncate:
            db.execute(text("TRUNCATE certificates_vectors"))
            db.commit()
            logger.info("TRUNCATE certificates_vectors done.")
        else:
            qids = list(qual_ids_to_refresh)
            for j in range(0, len(qids), 500):
                chunk = qids[j : j + 500]
                db.execute(text("DELETE FROM certificates_vectors WHERE qual_id = ANY(:ids)"), {"ids": chunk})
            db.commit()
            logger.info("Deleted certificates_vectors for %s qual_ids (refresh set).", len(qids))

        # INSERT: content(FTS), bm25_text, dense_content(임베딩 소스), content_hash from dense_content
        insert_sql = text("""
            INSERT INTO certificates_vectors (qual_id, name, content, bm25_text, dense_content, embedding, metadata, content_hash, chunk_index)
            VALUES (:qual_id, :name, :content, :bm25_text, :dense_content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), :content_hash, :chunk_index)
        """)
        for it in chunks_to_upsert:
            db.execute(insert_sql, {
                "qual_id": it["qual_id"],
                "name": it["name"],
                "content": it["content"],
                "bm25_text": it["bm25_text"],
                "dense_content": it.get("dense_content") or it["content"],
                "embedding": str(it["embedding"]),
                "metadata": it["metadata"],
                "content_hash": it["content_hash"],
                "chunk_index": it["chunk_index"],
            })
        db.commit()
        logger.info("Inserted %s rows into certificates_vectors (qual_ids refreshed: %s).",
                    len(chunks_to_upsert), len(qual_ids_to_refresh))
    except Exception as e:
        db.rollback()
        logger.exception("DB error: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
