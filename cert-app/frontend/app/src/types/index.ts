/** Certification types */

export interface Qualification {
  qual_id: number;
  qual_name: string;
  qual_type: string | null;
  main_field: string | null;
  ncs_large: string | null;
  managing_body: string | null;
  grade_code: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface QualificationStats {
  stat_id: number;
  qual_id: number;
  year: number;
  exam_round: number;
  candidate_cnt: number | null;
  pass_cnt: number | null;
  pass_rate: number | null;
  exam_structure: string | null;
  difficulty_score: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface QualificationListItem extends Qualification {
  latest_pass_rate: number | null;
  avg_difficulty: number | null;
  total_candidates: number | null;
}

export interface Job {
  job_id: number;
  job_name: string;
  outlook: string | null;
  salary_info: string | null;
  work_conditions: string | null;
  description: string | null;
  outlook_summary: string | null;
  entry_salary: string | null;
  reward: number | null;
  stability: number | null;
  development: number | null;
  condition: number | null;
  professionalism: number | null;
  equality: number | null;
  similar_jobs: string | null;
  aptitude: string | null;
  employment_path: string | null;
  qualifications?: Qualification[];
}

export interface QualificationDetail extends Qualification {
  stats: QualificationStats[];
  jobs: Job[];
  latest_pass_rate: number | null;
  avg_difficulty: number | null;
  total_candidates: number | null;
}

export interface JobQueryParams {
  q?: string;
  page?: number;
  page_size?: number;
}

export interface Recommendation {
  qual_id: number;
  qual_name: string;
  qual_type: string | null;
  main_field: string | null;
  managing_body: string | null;
  score: number;
  reason: string | null;
  latest_pass_rate: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface QualificationListResponse extends PaginatedResponse<QualificationListItem> { }

export interface QualificationStatsListResponse {
  items: QualificationStats[];
  qual_id: number;
}

export interface RecommendationListResponse {
  items: Recommendation[];
  major: string;
  total: number;
}

export interface FilterOptions {
  main_fields: string[];
  ncs_large: string[];
  qual_types: string[];
  managing_bodies: string[];
}

export interface HealthCheck {
  status: string;
  database: string;
  redis: string;
  version: string;
}

export interface UserFavorite {
  fav_id: number;
  user_id: string;
  qual_id: number;
  created_at: string;
  qualification?: Qualification;
}

export type SortOption = 'name' | 'pass_rate' | 'difficulty' | 'recent';

export interface CertFilterParams {
  q?: string;
  main_field?: string;
  ncs_large?: string;
  qual_type?: string;
  managing_body?: string;
  is_active?: boolean;
  sort?: SortOption;
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export * from './recommendations';
