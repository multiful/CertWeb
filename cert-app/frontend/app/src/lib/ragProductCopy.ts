/**
 * 제품 UI 문구 단일 기준.
 * 백엔드 `docs/Final_RAG_TECHNIQUES_SUMMARY.md`(갱신 2026-04-06)와 용어를 맞춤.
 */
export const RAG_VERSION_MARK = '2026.04 종결본';

/** 배지·헤더용 (항상 "RAG" 접두 포함) */
export const RAG_RELEASE_LABEL = `RAG ${RAG_VERSION_MARK}`;

/** 푸터·배지 등 짧은 태그 */
export const PRODUCT_FOOTER_LINE =
  `2026 CertFinder · 국가자격 데이터 & 하이브리드 RAG(${RAG_VERSION_MARK})`;

/** AI 추천 로딩·설명용 한 줄 */
export const RAG_RETRIEVAL_LOADING_LINE =
  'BM25·시맨틱(pgvector)·Contrastive 3채널 하이브리드 검색, 합격률·난이도·프로필 보정을 합치는 중입니다.';

/** 스펙 패널·툴팁용 (조금 더 구체) */
export const RAG_RETRIEVAL_DETAIL_LINE =
  '로컬 BM25 + pgvector + Contrastive(768)를 Linear 융합하고, 설정·질의에 따라 계층 BM25·메타 보정·Cross-Encoder 리랭킹 경로가 붙습니다.';
