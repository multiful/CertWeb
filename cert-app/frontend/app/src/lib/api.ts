/** API client for backend communication with Mock fallback */

import type {
  QualificationListResponse,
  QualificationDetail,
  QualificationStatsListResponse,
  RecommendationListResponse,
  FilterOptions,
  HealthCheck,
  CertFilterParams,
  UserFavorite,
  Job,
  SemanticSearchResponse,
  HybridRecommendationResponse,
  TrendingQualificationListResponse,
} from '@/types';
import { mockApi } from './mockApi';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta as any).env?.VITE_API_BASE_URL ||
  (import.meta as any).env?.NEXT_PUBLIC_API_URL ||
  'https://certweb-xzpx.onrender.com/api/v1';

/** 요청 타임아웃 (ms). 실무에서는 15~30초 권장 */
const DEFAULT_REQUEST_TIMEOUT_MS = 15000;
/** 재시도 횟수 (네트워크/5xx만). 4xx는 재시도 안 함 */
const MAX_RETRIES = 2;
/** 재시도 대기: 지수 백오프 (1초, 2초) */
const RETRY_DELAY_MS = 1000;

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** 4xx/5xx 응답 본문에서 detail 추출 (서버 메시지 노출) */
async function getErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body && typeof body.detail === 'string') return body.detail;
    if (body && Array.isArray(body.detail)) return body.detail.map((d: any) => d.msg || d).join('; ');
    if (body && typeof body.message === 'string') return body.message;
  } catch {
    /* ignore */
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function apiRequest<T>(
  path: string,
  options?: RequestInit,
  retries = MAX_RETRIES
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_REQUEST_TIMEOUT_MS);
  const init: RequestInit = {
    ...options,
    signal: options?.signal ?? controller.signal,
    headers: { ...options?.headers },
  };

  try {
    const response = await fetch(`${BASE_URL}${path}`, init);
    clearTimeout(timeoutId);

    if (!response.ok) {
      const detail = await getErrorDetail(response);
      const err = new Error(detail || `API Error: ${response.status}`);
      (err as any).status = response.status;
      throw err;
    }
    return await response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    const isNetworkOr5xx =
      error.name === 'TypeError' ||
      error.name === 'AbortError' ||
      (error.status >= 500 && retries > 0);
    if (isNetworkOr5xx && retries > 0) {
      const delay = RETRY_DELAY_MS * (MAX_RETRIES - retries + 1);
      console.warn(`[API Retry] ${path} in ${delay}ms (${retries} left)`);
      await sleep(delay);
      return apiRequest<T>(path, options, retries - 1);
    }
    if (error.status === 401) {
      console.warn(`API Request 401 for ${path}`);
    } else {
      console.error(`API Request failed for ${path}:`, error);
    }
    throw error;
  }
}

// ============== Certification APIs ==============

export async function getCertifications(
  params: CertFilterParams = {}
): Promise<QualificationListResponse> {
  try {
    const query = new URLSearchParams();
    if (params.q) query.append('q', params.q);
    if (params.main_field) query.append('main_field', params.main_field);
    if (params.ncs_large) query.append('ncs_large', params.ncs_large);
    if (params.qual_type) query.append('qual_type', params.qual_type);
    if (params.managing_body) query.append('managing_body', params.managing_body);
    if (params.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params.sort) query.append('sort', params.sort);
    if (params.sort_desc !== undefined) query.append('sort_desc', String(params.sort_desc));
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return await apiRequest<QualificationListResponse>(`/certs?${query.toString()}`);
  } catch {
    // When using mock, we need to adapt CertFilterParams if property names differ,
    // but here we just pass it as is because we fixed the call site
    // However, mockApi.getCertifications might expect camelCase if defined so.
    // Let's check mockApi definition in Step 538.
    // It expects { q?: string; main_field?: string; ... } which is snake_case.
    // So this is fine.
    return mockApi.getCertifications(params);
  }
}

export async function getCertificationDetail(
  qualId: number,
  token?: string | null
): Promise<QualificationDetail | null> {
  try {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return await apiRequest<QualificationDetail>(`/certs/${qualId}`, { headers });
  } catch {
    return mockApi.getCertificationDetail(qualId);
  }
}

export async function getCertificationStats(
  qualId: number,
  year?: number
): Promise<QualificationStatsListResponse> {
  try {
    const query = year ? `?year=${year}` : '';
    return await apiRequest<QualificationStatsListResponse>(`/certs/${qualId}/stats${query}`);
  } catch {
    return mockApi.getCertificationStats(qualId);
  }
}

export async function getFilterOptions(): Promise<FilterOptions> {
  try {
    return await apiRequest<FilterOptions>('/certs/filter-options');
  } catch {
    return mockApi.getFilterOptions();
  }
}

// ============== Recommendation APIs ==============

export async function getRecommendations(
  major: string,
  limit: number = 10
): Promise<RecommendationListResponse> {
  try {
    return await apiRequest<RecommendationListResponse>(`/recommendations?major=${encodeURIComponent(major)}&limit=${limit}`);
  } catch {
    return mockApi.getRecommendations(major);
  }
}

const trendingCache: { data: TrendingQualificationListResponse | null; ts: number } = { data: null, ts: 0 };
const TRENDING_CACHE_TTL_MS = 2 * 60 * 1000;

export async function getTrendingCerts(
  limit: number = 10
): Promise<TrendingQualificationListResponse> {
  if (trendingCache.data && Date.now() - trendingCache.ts < TRENDING_CACHE_TTL_MS) {
    return { ...trendingCache.data, items: trendingCache.data.items.slice(0, limit), total: Math.min(trendingCache.data.total, limit) };
  }
  try {
    const res = await apiRequest<TrendingQualificationListResponse>(`/certs/trending/now?limit=${limit}`);
    trendingCache.data = res;
    trendingCache.ts = Date.now();
    return res;
  } catch {
    return { items: [], total: 0 };
  }
}

export async function getHybridRecommendations(
  major: string,
  interest?: string,
  limit: number = 10,
  token?: string | null
): Promise<HybridRecommendationResponse> {
  const query = new URLSearchParams();
  query.append('major', major);
  if (interest) query.append('interest', interest);
  query.append('limit', limit.toString());

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return await apiRequest<HybridRecommendationResponse>(
    `/recommendations/ai/hybrid-recommendation?${query.toString()}`,
    { headers }
  );
}

export async function semanticSearch(
  query: string,
  limit: number = 10
): Promise<SemanticSearchResponse> {
  return await apiRequest<SemanticSearchResponse>(`/recommendations/ai/semantic-search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function getAvailableMajors(): Promise<{ majors: string[] }> {
  try {
    return await apiRequest<{ majors: string[] }>('/recommendations/majors');
  } catch {
    const majors = await mockApi.getAvailableMajors();
    return { majors };
  }
}

// ============== Job APIs ==============

export async function getJobs(
  params: { q?: string; page?: number; page_size?: number } = {}
): Promise<Job[]> {
  try {
    const query = new URLSearchParams();
    if (params.q) query.append('q', params.q);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return await apiRequest<Job[]>(`/jobs?${query.toString()}`);
  } catch {
    return []; // No mock for jobs yet
  }
}

export async function getJobDetail(jobId: number): Promise<Job | null> {
  try {
    return await apiRequest<Job>(`/jobs/${jobId}`);
  } catch {
    return null;
  }
}

// ============== Health Check ==============

export async function getHealth(): Promise<HealthCheck> {
  try {
    return await apiRequest<HealthCheck>('/health');
  } catch {
    return mockApi.getHealth();
  }
}

// ============== Favorites APIs (requires auth) ==============

export async function getFavorites(
  token: string,
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: UserFavorite[]; total: number }> {
  try {
    return await apiRequest<{ items: UserFavorite[]; total: number }>(
      `/me/favorites?page=${page}&page_size=${pageSize}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
  } catch {
    return { items: [], total: 0 };
  }
}

export async function addFavorite(
  qualId: number,
  token: string
): Promise<UserFavorite> {
  return await apiRequest<UserFavorite>(
    `/me/favorites/${qualId}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
}

export async function removeFavorite(
  qualId: number,
  token: string
): Promise<void> {
  await apiRequest<void>(
    `/me/favorites/${qualId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
}

export async function checkFavorite(
  qualId: number,
  token: string
): Promise<{ qual_id: number; is_favorite: boolean }> {
  try {
    return await apiRequest<{ qual_id: number; is_favorite: boolean }>(
      `/me/favorites/${qualId}/check`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
  } catch {
    return { qual_id: qualId, is_favorite: false };
  }
}

export async function getProfile(token: string): Promise<any> {
  return await apiRequest<any>('/auth/profile', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
}
export async function getRecentViewed(token: string): Promise<any[]> {
  try {
    return await apiRequest<any[]>('/certs/recent/viewed', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  } catch {
    return [];
  }
}
export async function updateProfile(
  token: string,
  updates: { name?: string; userid?: string; nickname?: string; detail_major?: string; grade_year?: number | null }
): Promise<any> {
  return await apiRequest<any>('/auth/profile', {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updates)
  });
}

// ============== Acquired Certs (취득 자격증) ==============
export interface AcquiredCertItem {
  acq_id: number;
  user_id: string;
  qual_id: number;
  acquired_at: string | null;
  created_at: string;
  xp: number;
  qualification?: { qual_id: number; qual_name: string; qual_type?: string; main_field?: string; avg_difficulty?: number; [key: string]: unknown };
}

export interface AcquiredCertSummary {
  total_xp: number;
  level: number;
  tier: string;
  tier_color: string;
  current_level_xp: number;
  next_level_xp: number | null;
  cert_count: number;
}

export async function getAcquiredCerts(
  token: string,
  page = 1,
  pageSize = 100
): Promise<{ items: AcquiredCertItem[]; total: number }> {
  const res = await apiRequest<{ items: AcquiredCertItem[]; total: number }>(
    `/me/acquired-certs?page=${page}&page_size=${pageSize}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res;
}

export async function getAcquiredCertsCount(token: string): Promise<{ count: number }> {
  return await apiRequest<{ count: number }>('/me/acquired-certs/count', {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export async function addAcquiredCert(qualId: number, token: string): Promise<AcquiredCertItem> {
  return await apiRequest<AcquiredCertItem>(`/me/acquired-certs/${qualId}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  });
}

export async function removeAcquiredCert(qualId: number, token: string): Promise<void> {
  await apiRequest(`/me/acquired-certs/${qualId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` }
  });
}

export async function getAcquiredCertsSummary(token: string): Promise<AcquiredCertSummary> {
  return await apiRequest<AcquiredCertSummary>('/me/acquired-certs/summary', {
    headers: { Authorization: `Bearer ${token}` }
  });
}

export async function checkUserId(userid: string): Promise<{ available: boolean, message: string }> {
  return await apiRequest<{ available: boolean, message: string }>('/auth/check-userid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userid })
  });
}

// ============== Contact / Feedback ==============
export async function sendContactEmail(data: { name: string; email: string; subject: string; message: string }): Promise<void> {
  await apiRequest('/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

// ============== Stream / SSE (향후 AI 스트리밍 응답용) ==============
/** SSE 이벤트 스트림 구독. 백엔드에서 EventSource/SSE 엔드포인트 추가 시 사용 */
export function createSSEClient(
  path: string,
  options: { token?: string | null; onMessage: (data: unknown) => void; onError?: (err: Event) => void }
): () => void {
  const url = `${BASE_URL}${path}`;
  const eventSource = new EventSource(url);
  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      options.onMessage(data);
    } catch {
      options.onMessage(e.data);
    }
  };
  eventSource.onerror = (e) => {
    options.onError?.(e);
    eventSource.close();
  };
  return () => eventSource.close();
}
