/** Mock API for demo purposes */
import type {
  QualificationListResponse,
  QualificationDetail,
  QualificationStatsListResponse,
  RecommendationListResponse,
  FilterOptions,
  HealthCheck,
} from '@/types';

// Sample certification data
const certifications = [
  {
    qual_id: 1,
    qual_name: '정보처리기사',
    qual_type: '국가기술자격',
    main_field: '정보통신',
    ncs_large: '정보기술개발',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 35.0,
    avg_difficulty: 7.5,
    total_candidates: 61500,
  },
  {
    qual_id: 2,
    qual_name: '정보처리산업기사',
    qual_type: '국가기술자격',
    main_field: '정보통신',
    ncs_large: '정보기술개발',
    managing_body: '한국산업인력공단',
    grade_code: '산업기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 42.5,
    avg_difficulty: 6.0,
    total_candidates: 32000,
  },
  {
    qual_id: 3,
    qual_name: 'SQLD',
    qual_type: '국가공인자격',
    main_field: '정보통신',
    ncs_large: '데이터분석',
    managing_body: '한국데이터산업진흥원',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 62.5,
    avg_difficulty: 5.0,
    total_candidates: 48000,
  },
  {
    qual_id: 4,
    qual_name: 'SQLP',
    qual_type: '국가공인자격',
    main_field: '정보통신',
    ncs_large: '데이터분석',
    managing_body: '한국데이터산업진흥원',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 30.0,
    avg_difficulty: 8.0,
    total_candidates: 15000,
  },
  {
    qual_id: 5,
    qual_name: '리눅스마스터 1급',
    qual_type: '민간자격',
    main_field: '정보통신',
    ncs_large: '시스템관리',
    managing_body: '한국정보통신진흥협회',
    grade_code: '1급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 48.7,
    avg_difficulty: 6.0,
    total_candidates: 25000,
  },
  {
    qual_id: 6,
    qual_name: '리눅스마스터 2급',
    qual_type: '민간자격',
    main_field: '정보통신',
    ncs_large: '시스템관리',
    managing_body: '한국정보통신진흥협회',
    grade_code: '2급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 55.0,
    avg_difficulty: 5.5,
    total_candidates: 18000,
  },
  {
    qual_id: 7,
    qual_name: '네트워크관리사 1급',
    qual_type: '민간자격',
    main_field: '정보통신',
    ncs_large: '네트워크관리',
    managing_body: '한국정보통신진흥협회',
    grade_code: '1급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 41.3,
    avg_difficulty: 6.5,
    total_candidates: 22000,
  },
  {
    qual_id: 8,
    qual_name: '네트워크관리사 2급',
    qual_type: '민간자격',
    main_field: '정보통신',
    ncs_large: '네트워크관리',
    managing_body: '한국정보통신진흥협회',
    grade_code: '2급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 50.0,
    avg_difficulty: 5.8,
    total_candidates: 28000,
  },
  {
    qual_id: 9,
    qual_name: '정볳보안기사',
    qual_type: '국가기술자격',
    main_field: '정보통신',
    ncs_large: '정볳보안',
    managing_body: '한국인터넷진흥원',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 25.0,
    avg_difficulty: 8.5,
    total_candidates: 12000,
  },
  {
    qual_id: 10,
    qual_name: '전기기사',
    qual_type: '국가기술자격',
    main_field: '전기·전자',
    ncs_large: '전기설계',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 40.0,
    avg_difficulty: 7.0,
    total_candidates: 35000,
  },
  {
    qual_id: 11,
    qual_name: '전기산업기사',
    qual_type: '국가기술자격',
    main_field: '전기·전자',
    ncs_large: '전기설계',
    managing_body: '한국산업인력공단',
    grade_code: '산업기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 45.0,
    avg_difficulty: 6.0,
    total_candidates: 22000,
  },
  {
    qual_id: 12,
    qual_name: '전자기사',
    qual_type: '국가기술자격',
    main_field: '전기·전자',
    ncs_large: '전자개발',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 38.5,
    avg_difficulty: 7.2,
    total_candidates: 28000,
  },
  {
    qual_id: 13,
    qual_name: '기계기사',
    qual_type: '국가기술자격',
    main_field: '기계',
    ncs_large: '기계설계',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 35.5,
    avg_difficulty: 7.8,
    total_candidates: 42000,
  },
  {
    qual_id: 14,
    qual_name: '건축기사',
    qual_type: '국가기술자격',
    main_field: '건설',
    ncs_large: '건축설계',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 32.0,
    avg_difficulty: 8.0,
    total_candidates: 38000,
  },
  {
    qual_id: 15,
    qual_name: '토목기사',
    qual_type: '국가기술자격',
    main_field: '건설',
    ncs_large: '토목설계',
    managing_body: '한국산업인력공단',
    grade_code: '기사',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 30.5,
    avg_difficulty: 8.2,
    total_candidates: 32000,
  },
  {
    qual_id: 16,
    qual_name: '회계관리 1급',
    qual_type: '국가기술자격',
    main_field: '경제·금융',
    ncs_large: '회계',
    managing_body: '한국산업인력공단',
    grade_code: '1급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 45.0,
    avg_difficulty: 6.5,
    total_candidates: 25000,
  },
  {
    qual_id: 17,
    qual_name: '회계관리 2급',
    qual_type: '국가기술자격',
    main_field: '경제·금융',
    ncs_large: '회계',
    managing_body: '한국산업인력공단',
    grade_code: '2급',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 55.0,
    avg_difficulty: 5.0,
    total_candidates: 18000,
  },
  {
    qual_id: 18,
    qual_name: 'AFPK',
    qual_type: '민간자격',
    main_field: '경제·금융',
    ncs_large: '금융기획',
    managing_body: '한국FPSB',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 65.0,
    avg_difficulty: 4.5,
    total_candidates: 12000,
  },
  {
    qual_id: 19,
    qual_name: '간호사',
    qual_type: '국가자격',
    main_field: '보건·의료',
    ncs_large: '간호',
    managing_body: '한국보건의료인국가시험원',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 85.0,
    avg_difficulty: 6.0,
    total_candidates: 55000,
  },
  {
    qual_id: 20,
    qual_name: '의사',
    qual_type: '국가자격',
    main_field: '보건·의료',
    ncs_large: '의료',
    managing_body: '한국보건의료인국가시험원',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 92.0,
    avg_difficulty: 9.0,
    total_candidates: 3200,
  },
  {
    qual_id: 21,
    qual_name: '약사',
    qual_type: '국가자격',
    main_field: '보건·의료',
    ncs_large: '약학',
    managing_body: '한국보건의료인국가시험원',
    grade_code: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    latest_pass_rate: 78.0,
    avg_difficulty: 8.5,
    total_candidates: 4500,
  },
];

// Sample stats data
const statsData: Record<number, QualificationStatsListResponse> = {
  1: {
    qual_id: 1,
    items: [
      { stat_id: 1, qual_id: 1, year: 2024, exam_round: 2, candidate_cnt: 16200, pass_cnt: 5670, pass_rate: 35.0, difficulty_score: 7.5, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 2, qual_id: 1, year: 2024, exam_round: 1, candidate_cnt: 15000, pass_cnt: 5250, pass_rate: 35.0, difficulty_score: 7.5, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 3, qual_id: 1, year: 2023, exam_round: 2, candidate_cnt: 15800, pass_cnt: 5214, pass_rate: 33.0, difficulty_score: 7.8, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 4, qual_id: 1, year: 2023, exam_round: 1, candidate_cnt: 14500, pass_cnt: 4785, pass_rate: 33.0, difficulty_score: 7.8, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 5, qual_id: 1, year: 2022, exam_round: 2, candidate_cnt: 14000, pass_cnt: 4900, pass_rate: 35.0, difficulty_score: 7.5, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ]
  },
  3: {
    qual_id: 3,
    items: [
      { stat_id: 6, qual_id: 3, year: 2024, exam_round: 2, candidate_cnt: 13500, pass_cnt: 8100, pass_rate: 60.0, difficulty_score: 5.2, exam_structure: '필기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 7, qual_id: 3, year: 2024, exam_round: 1, candidate_cnt: 12000, pass_cnt: 7500, pass_rate: 62.5, difficulty_score: 5.0, exam_structure: '필기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 8, qual_id: 3, year: 2023, exam_round: 2, candidate_cnt: 11500, pass_cnt: 6900, pass_rate: 60.0, difficulty_score: 5.0, exam_structure: '필기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 9, qual_id: 3, year: 2023, exam_round: 1, candidate_cnt: 11000, pass_cnt: 6600, pass_rate: 60.0, difficulty_score: 5.0, exam_structure: '필기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ]
  },
  5: {
    qual_id: 5,
    items: [
      { stat_id: 10, qual_id: 5, year: 2024, exam_round: 1, candidate_cnt: 8000, pass_cnt: 3900, pass_rate: 48.7, difficulty_score: 6.0, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 11, qual_id: 5, year: 2023, exam_round: 2, candidate_cnt: 7500, pass_cnt: 3600, pass_rate: 48.0, difficulty_score: 6.2, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ]
  },
  7: {
    qual_id: 7,
    items: [
      { stat_id: 12, qual_id: 7, year: 2024, exam_round: 1, candidate_cnt: 7000, pass_cnt: 2890, pass_rate: 41.3, difficulty_score: 6.5, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ]
  },
  10: {
    qual_id: 10,
    items: [
      { stat_id: 13, qual_id: 10, year: 2024, exam_round: 1, candidate_cnt: 10000, pass_cnt: 4000, pass_rate: 40.0, difficulty_score: 7.0, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { stat_id: 14, qual_id: 10, year: 2023, exam_round: 2, candidate_cnt: 9500, pass_cnt: 3800, pass_rate: 40.0, difficulty_score: 7.0, exam_structure: '필기 + 실기', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ]
  },
};

// Sample recommendations
const recommendations: Record<string, RecommendationListResponse> = {
  '컴퓨터공학': {
    major: '컴퓨터공학',
    total: 9,
    items: [
      { qual_id: 1, qual_name: '정보처리기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국산업인력공단', score: 10.0, reason: '전공과 직접 관련된 핵심 자격증', latest_pass_rate: 35.0 },
      { qual_id: 3, qual_name: 'SQLD', qual_type: '국가공인자격', main_field: '정보통신', managing_body: '한국데이터산업진흥원', score: 9.0, reason: '데이터베이스 필수 자격증', latest_pass_rate: 62.5 },
      { qual_id: 9, qual_name: '정볳보안기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국인터넷진흥원', score: 9.0, reason: '보안 분야 필수', latest_pass_rate: 25.0 },
      { qual_id: 5, qual_name: '리눅스마스터 1급', qual_type: '민간자격', main_field: '정보통신', managing_body: '한국정보통신진흥협회', score: 8.0, reason: '시스템 관리 필수', latest_pass_rate: 48.7 },
      { qual_id: 4, qual_name: 'SQLP', qual_type: '국가공인자격', main_field: '정보통신', managing_body: '한국데이터산업진흥원', score: 8.5, reason: '고급 데이터베이스 역량', latest_pass_rate: 30.0 },
    ]
  },
  '소프트웨어공학': {
    major: '소프트웨어공학',
    total: 3,
    items: [
      { qual_id: 1, qual_name: '정보처리기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국산업인력공단', score: 10.0, reason: '전공과 직접 관련된 핵심 자격증', latest_pass_rate: 35.0 },
      { qual_id: 3, qual_name: 'SQLD', qual_type: '국가공인자격', main_field: '정보통신', managing_body: '한국데이터산업진흥원', score: 9.0, reason: '데이터베이스 필수', latest_pass_rate: 62.5 },
      { qual_id: 9, qual_name: '정볳보안기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국인터넷진흥원', score: 8.5, reason: '보안 역량', latest_pass_rate: 25.0 },
    ]
  },
  '정보통신공학': {
    major: '정보통신공학',
    total: 5,
    items: [
      { qual_id: 7, qual_name: '네트워크관리사 1급', qual_type: '민간자격', main_field: '정보통신', managing_body: '한국정보통신진흥협회', score: 10.0, reason: '네트워크 전공 핵심', latest_pass_rate: 41.3 },
      { qual_id: 1, qual_name: '정보처리기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국산업인력공단', score: 9.0, reason: 'IT 기초 자격증', latest_pass_rate: 35.0 },
      { qual_id: 8, qual_name: '네트워크관리사 2급', qual_type: '민간자격', main_field: '정보통신', managing_body: '한국정보통신진흥협회', score: 8.5, reason: '네트워크 기초', latest_pass_rate: 50.0 },
      { qual_id: 5, qual_name: '리눅스마스터 1급', qual_type: '민간자격', main_field: '정보통신', managing_body: '한국정보통신진흥협회', score: 7.5, reason: '시스템 관리', latest_pass_rate: 48.7 },
      { qual_id: 9, qual_name: '정볳보안기사', qual_type: '국가기술자격', main_field: '정보통신', managing_body: '한국인터넷진흥원', score: 8.0, reason: '네트워크 보안', latest_pass_rate: 25.0 },
    ]
  },
  '전기공학': {
    major: '전기공학',
    total: 2,
    items: [
      { qual_id: 10, qual_name: '전기기사', qual_type: '국가기술자격', main_field: '전기·전자', managing_body: '한국산업인력공단', score: 10.0, reason: '전공 핵심 자격증', latest_pass_rate: 40.0 },
      { qual_id: 11, qual_name: '전기산업기사', qual_type: '국가기술자격', main_field: '전기·전자', managing_body: '한국산업인력공단', score: 8.0, reason: '전기 기초', latest_pass_rate: 45.0 },
    ]
  },
  '기계공학': {
    major: '기계공학',
    total: 1,
    items: [
      { qual_id: 13, qual_name: '기계기사', qual_type: '국가기술자격', main_field: '기계', managing_body: '한국산업인력공단', score: 10.0, reason: '전공 핵심 자격증', latest_pass_rate: 35.5 },
    ]
  },
  '건축학': {
    major: '건축학',
    total: 1,
    items: [
      { qual_id: 14, qual_name: '건축기사', qual_type: '국가기술자격', main_field: '건설', managing_body: '한국산업인력공단', score: 10.0, reason: '전공 핵심 자격증', latest_pass_rate: 32.0 },
    ]
  },
  '경영학': {
    major: '경영학',
    total: 3,
    items: [
      { qual_id: 18, qual_name: 'AFPK', qual_type: '민간자격', main_field: '경제·금융', managing_body: '한국FPSB', score: 9.0, reason: '금융 기획 전문', latest_pass_rate: 65.0 },
      { qual_id: 16, qual_name: '회계관리 1급', qual_type: '국가기술자격', main_field: '경제·금융', managing_body: '한국산업인력공단', score: 8.5, reason: '회계 기초', latest_pass_rate: 45.0 },
      { qual_id: 17, qual_name: '회계관리 2급', qual_type: '국가기술자격', main_field: '경제·금융', managing_body: '한국산업인력공단', score: 7.0, reason: '회계 입문', latest_pass_rate: 55.0 },
    ]
  },
  '회계학': {
    major: '회계학',
    total: 2,
    items: [
      { qual_id: 16, qual_name: '회계관리 1급', qual_type: '국가기술자격', main_field: '경제·금융', managing_body: '한국산업인력공단', score: 10.0, reason: '회계 전공 핵심', latest_pass_rate: 45.0 },
      { qual_id: 17, qual_name: '회계관리 2급', qual_type: '국가기술자격', main_field: '경제·금융', managing_body: '한국산업인력공단', score: 8.5, reason: '회계 기초', latest_pass_rate: 55.0 },
    ]
  },
  '간호학': {
    major: '간호학',
    total: 1,
    items: [
      { qual_id: 19, qual_name: '간호사', qual_type: '국가자격', main_field: '보건·의료', managing_body: '한국보건의료인국가시험원', score: 10.0, reason: '간호사 면허 필수', latest_pass_rate: 85.0 },
    ]
  },
  '의학': {
    major: '의학',
    total: 1,
    items: [
      { qual_id: 20, qual_name: '의사', qual_type: '국가자격', main_field: '보건·의료', managing_body: '한국보건의료인국가시험원', score: 10.0, reason: '의사 면허 필수', latest_pass_rate: 92.0 },
    ]
  },
  '약학': {
    major: '약학',
    total: 1,
    items: [
      { qual_id: 21, qual_name: '약사', qual_type: '국가자격', main_field: '보건·의료', managing_body: '한국보건의료인국가시험원', score: 10.0, reason: '약사 면허 필수', latest_pass_rate: 78.0 },
    ]
  },
};

// Filter options
const filterOptions: FilterOptions = {
  main_fields: ['정보통신', '전기·전자', '기계', '건설', '경제·금융', '보건·의료'],
  ncs_large: ['정보기술개발', '데이터분석', '시스템관리', '네트워크관리', '정볳보안', '전기설계', '전자개발', '기계설계', '건축설계', '토목설계', '회계', '금융기획', '간호', '의료', '약학'],
  qual_types: ['국가기술자격', '국가공인자격', '민간자격', '국가자격'],
  managing_bodies: ['한국산업인력공단', '한국데이터산업진흥원', '한국정보통신진흥협회', '한국인터넷진흥원', '한국FPSB', '한국보건의료인국가시험원'],
};

// Mock API functions
export const mockApi = {
  async getCertifications(params: {
    q?: string;
    main_field?: string;
    ncs_large?: string;
    qual_type?: string;
    managing_body?: string;
    sort?: string;
    page?: number;
    page_size?: number;
  }): Promise<QualificationListResponse> {

    let items = [...certifications];

    // Apply filters
    if (params.q) {
      const q = params.q.toLowerCase();
      items = items.filter(c => c.qual_name.toLowerCase().includes(q));
    }
    if (params.main_field) {
      items = items.filter(c => c.main_field === params.main_field);
    }
    if (params.ncs_large) {
      items = items.filter(c => c.ncs_large === params.ncs_large);
    }
    if (params.qual_type) {
      items = items.filter(c => c.qual_type === params.qual_type);
    }
    if (params.managing_body) {
      items = items.filter(c => c.managing_body === params.managing_body);
    }

    // Apply sorting
    const sort = params.sort || 'name';
    switch (sort) {
      case 'name':
        items.sort((a, b) => a.qual_name.localeCompare(b.qual_name));
        break;
      case 'pass_rate':
        items.sort((a, b) => (b.latest_pass_rate || 0) - (a.latest_pass_rate || 0));
        break;
      case 'difficulty':
        items.sort((a, b) => (b.avg_difficulty || 0) - (a.avg_difficulty || 0));
        break;
      case 'recent':
        items.sort((a, b) => (b.qual_id - a.qual_id));
        break;
    }

    // Apply pagination
    const page = params.page || 1;
    const page_size = params.page_size || 20;
    const total = items.length;
    const total_pages = Math.ceil(total / page_size);
    const start = (page - 1) * page_size;
    const paginatedItems = items.slice(start, start + page_size);

    return {
      items: paginatedItems,
      total,
      page,
      page_size,
      total_pages,
    };
  },

  async getCertificationDetail(qualId: number): Promise<QualificationDetail | null> {
    const cert = certifications.find(c => c.qual_id === qualId);
    if (!cert) return null;

    const stats = statsData[qualId]?.items || [];

    return {
      ...cert,
      stats,
      jobs: [],
      latest_pass_rate: stats[0]?.pass_rate || null,
      avg_difficulty: stats.length > 0
        ? stats.reduce((acc, s) => acc + (s.difficulty_score || 0), 0) / stats.length
        : null,
      total_candidates: stats.reduce((acc, s) => acc + (s.candidate_cnt || 0), 0),
    };
  },

  async getCertificationStats(qualId: number): Promise<QualificationStatsListResponse> {
    return statsData[qualId] || { qual_id: qualId, items: [] };
  },

  async getFilterOptions(): Promise<FilterOptions> {
    return filterOptions;
  },

  async getRecommendations(major: string): Promise<RecommendationListResponse> {

    // Try exact match first
    let result = recommendations[major];

    // Try case-insensitive match
    if (!result) {
      const key = Object.keys(recommendations).find(k => k.toLowerCase() === major.toLowerCase());
      if (key) {
        result = recommendations[key];
      }
    }

    if (!result) {
      throw new Error(`"${major}"에 대한 추천 결과가 없습니다.`);
    }

    return result;
  },

  async getAvailableMajors(): Promise<string[]> {
    return Object.keys(recommendations);
  },

  async getHealth(): Promise<HealthCheck> {
    return {
      status: 'healthy',
      database: 'healthy (mock)',
      redis: 'healthy (mock)',
      version: '1.0.0-mock',
    };
  },
};
