/** Hooks for certification data fetching (React Query) */

import { useQuery } from '@tanstack/react-query';
import type {
  QualificationListResponse,
  QualificationDetail,
  QualificationStatsListResponse,
  FilterOptions,
  CertFilterParams,
} from '@/types';
import {
  getCertifications,
  getCertificationDetail,
  getCertificationStats,
  getFilterOptions,
} from '@/lib/api';
import { certKeys } from '@/lib/queryKeys';

interface UseCertsReturn {
  data: QualificationListResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useCerts(params: CertFilterParams = {}): UseCertsReturn {
  const {
    data,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey: certKeys.list(params),
    queryFn: () => getCertifications(params),
    staleTime: 10 * 60 * 1000, // 10분: 자격증 목록은 자주 안 바뀌므로 재방문 시 캐시 우선
  });

  return {
    data: data ?? null,
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
    refetch,
  };
}

interface UseCertDetailReturn {
  data: QualificationDetail | null;
  loading: boolean;
  error: Error | null;
}

export function useCertDetail(qualId: number | null, token?: string | null): UseCertDetailReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: certKeys.detail(qualId, token),
    queryFn: () => getCertificationDetail(qualId!, token ?? undefined),
    enabled: qualId != null,
    staleTime: 60 * 60 * 1000, // 1시간: 상세/직무·전공 등 거의 변경 없음
  });

  return {
    data: data ?? null,
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}

interface UseCertStatsReturn {
  data: QualificationStatsListResponse | null;
  loading: boolean;
  error: Error | null;
}

export function useCertStats(
  qualId: number | null,
  year?: number
): UseCertStatsReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: certKeys.stats(qualId, year),
    queryFn: () => getCertificationStats(qualId!, year),
    enabled: qualId != null,
    staleTime: 60 * 60 * 1000, // 1시간: 통계는 갱신 주기가 김
  });

  return {
    data: data ?? null,
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}

interface UseFilterOptionsReturn {
  data: FilterOptions | null;
  loading: boolean;
  error: Error | null;
}

export function useFilterOptions(): UseFilterOptionsReturn {
  const {
    data,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: certKeys.filterOptions(),
    queryFn: getFilterOptions,
    staleTime: 10 * 60 * 1000, // 10분: 필터 옵션(직무/전공 등) 변경 적음
  });

  return {
    data: data ?? null,
    loading,
    error: error instanceof Error ? error : error ? new Error(String(error)) : null,
  };
}
