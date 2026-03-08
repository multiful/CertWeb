/**
 * React Query queryKey 설계: 서버 데이터 캐시/동기화 표준화
 * - certs, recommendations, filter options, stats 등 일관된 키 구조
 */

import type { CertFilterParams } from '@/types';

/** 인증/세션 관련 키 (예: 로그인 사용자 프로필) */
export const authKeys = {
  all: ['auth'] as const,
  profile: (userId: string | null) => ['auth', 'profile', userId] as const,
};

/** 자격증 목록: 필터/페이지/정렬에 따라 캐시 분리 */
export const certKeys = {
  all: ['certs'] as const,
  lists: () => [...certKeys.all, 'list'] as const,
  list: (params: CertFilterParams) => [...certKeys.lists(), params] as const,
  details: () => [...certKeys.all, 'detail'] as const,
  detail: (qualId: number | null, token?: string | null) =>
    [...certKeys.details(), qualId, token ?? 'anon'] as const,
  stats: (qualId: number | null, year?: number) =>
    [...certKeys.all, 'stats', qualId, year] as const,
  filterOptions: () => [...certKeys.all, 'filterOptions'] as const,
  trending: (limit?: number) => [...certKeys.all, 'trending', limit] as const,
};

/** 추천: 전공/인기 전공별 캐시 */
export const recommendationKeys = {
  all: ['recommendations'] as const,
  byMajor: (major: string, limit?: number) =>
    ['recommendations', 'major', major, limit] as const,
  majors: () => ['recommendations', 'majors'] as const,
  popularMajors: (limit?: number) =>
    ['recommendations', 'popularMajors', limit] as const,
};

/** 사용자별 즐겨찾기/취득 자격 (토큰 있음 시 캐시) */
export const userKeys = {
  favorites: (token: string | null) =>
    ['user', 'favorites', token ?? 'none'] as const,
  acquiredCerts: (token: string | null) =>
    ['user', 'acquiredCerts', token ?? 'none'] as const,
  recentViewed: (token: string | null) =>
    ['user', 'recentViewed', token ?? 'none'] as const,
  profile: (token: string | null) =>
    ['user', 'profile', token ?? 'none'] as const,
};

/** AI 추천 (전공/관심사/티어 조합) */
export const aiRecommendationKeys = {
  hybrid: (major: string, interest?: string, tier?: string) =>
    ['ai', 'hybrid', major, interest, tier] as const,
  semanticSearch: (query: string, token: string | null) =>
    ['ai', 'semantic', query, token ?? 'anon'] as const,
};
