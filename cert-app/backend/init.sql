-- Initial database setup with sample data

-- Create tables (if not using Alembic)
CREATE TABLE IF NOT EXISTS major (
    major_id SERIAL PRIMARY KEY,
    major_name VARCHAR(100) UNIQUE NOT NULL,
    major_category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    userid VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    birth_date VARCHAR(10),
    department VARCHAR(100),
    grade_year INTEGER,
    detail_major VARCHAR(100) REFERENCES major(major_name) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS qualification (
    qual_id SERIAL PRIMARY KEY,
    qual_name VARCHAR(255) NOT NULL,
    qual_type VARCHAR(100),
    main_field VARCHAR(100),
    ncs_large VARCHAR(100),
    managing_body VARCHAR(200),
    grade_code VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    written_cnt INTEGER DEFAULT 0,
    practical_cnt INTEGER DEFAULT 0,
    interview_cnt INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS qualification_stats (
    stat_id SERIAL PRIMARY KEY,
    qual_id INTEGER REFERENCES qualification(qual_id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    exam_round INTEGER NOT NULL,
    candidate_cnt INTEGER,
    pass_cnt INTEGER,
    pass_rate FLOAT,
    exam_structure TEXT,
    difficulty_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(qual_id, year, exam_round)
);

CREATE TABLE IF NOT EXISTS major_qualification_map (
    map_id SERIAL PRIMARY KEY,
    major VARCHAR(100) NOT NULL REFERENCES major(major_name) ON DELETE CASCADE,
    qual_id INTEGER REFERENCES qualification(qual_id) ON DELETE CASCADE,
    score FLOAT DEFAULT 1.0,
    weight FLOAT,
    reason VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(major, qual_id)
);

CREATE TABLE IF NOT EXISTS user_favorites (
    fav_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    qual_id INTEGER REFERENCES qualification(qual_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, qual_id)
);

CREATE TABLE IF NOT EXISTS user_acquired_certs (
    acq_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    qual_id INTEGER NOT NULL REFERENCES qualification(qual_id) ON DELETE CASCADE,
    acquired_at DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, qual_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_qual_name ON qualification(qual_name);
CREATE INDEX IF NOT EXISTS idx_qual_type ON qualification(qual_type);
CREATE INDEX IF NOT EXISTS idx_qual_main_field ON qualification(main_field);
CREATE INDEX IF NOT EXISTS idx_qual_ncs ON qualification(ncs_large);
CREATE INDEX IF NOT EXISTS idx_qual_active ON qualification(is_active);
CREATE INDEX IF NOT EXISTS idx_qual_managing_body ON qualification(managing_body);
CREATE INDEX IF NOT EXISTS idx_stats_qual_id ON qualification_stats(qual_id);
CREATE INDEX IF NOT EXISTS idx_stats_year ON qualification_stats(year);
CREATE INDEX IF NOT EXISTS idx_major_map_major ON major_qualification_map(major);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_acquired_certs_user ON user_acquired_certs(user_id);
CREATE INDEX IF NOT EXISTS idx_acquired_certs_qual ON user_acquired_certs(qual_id);

-- Insert sample data
INSERT INTO qualification (qual_name, qual_type, main_field, ncs_large, managing_body, grade_code, is_active) VALUES
('정보처리기사', '국가기술자격', '정보통신', '정보기술개발', '한국산업인력공단', '기사', TRUE),
('정보처리산업기사', '국가기술자격', '정보통신', '정보기술개발', '한국산업인력공단', '산업기사', TRUE),
('SQLD', '국가공인자격', '정보통신', '데이터분석', '한국데이터산업진흥원', NULL, TRUE),
('SQLP', '국가공인자격', '정보통신', '데이터분석', '한국데이터산업진흥원', NULL, TRUE),
('리눅스마스터1급', '민간자격', '정보통신', '시스템관리', '한국정보통신진흥협회', '1급', TRUE),
('리눅스마스터2급', '민간자격', '정보통신', '시스템관리', '한국정보통신진흥협회', '2급', TRUE),
('네트워크관리사1급', '민간자격', '정보통신', '네트워크관리', '한국정보통신진흥협회', '1급', TRUE),
('네트워크관리사2급', '민간자격', '정보통신', '네트워크관리', '한국정보통신진흥협회', '2급', TRUE),
('정볳보안기사', '국가기술자격', '정보통신', '정볳보안', '한국인터넷진흥원', '기사', TRUE),
('전기기사', '국가기술자격', '전기·전자', '전기설계', '한국산업인력공단', '기사', TRUE),
('전기산업기사', '국가기술자격', '전기·전자', '전기설계', '한국산업인력공단', '산업기사', TRUE),
('전자기사', '국가기술자격', '전기·전자', '전자개발', '한국산업인력공단', '기사', TRUE),
('기계기사', '국가기술자격', '기계', '기계설계', '한국산업인력공단', '기사', TRUE),
('건축기사', '국가기술자격', '건설', '건축설계', '한국산업인력공단', '기사', TRUE),
('토목기사', '국가기술자격', '건설', '토목설계', '한국산업인력공단', '기사', TRUE),
('회계관리1급', '국가기술자격', '경제·금융', '회계', '한국산업인력공단', '1급', TRUE),
('회계관리2급', '국가기술자격', '경제·금융', '회계', '한국산업인력공단', '2급', TRUE),
(' AFPK', '민간자격', '경제·금융', '금융기획', '한국FPSB', NULL, TRUE),
('간호사', '국가자격', '보건·의료', '간호', '한국보건의료인국가시험원', NULL, TRUE),
('의사', '국가자격', '보건·의료', '의료', '한국보건의료인국가시험원', NULL, TRUE),
('약사', '국가자격', '보건·의료', '약학', '한국보건의료인국가시험원', NULL, TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO major (major_name) VALUES
('컴퓨터공학'), ('소프트웨어공학'), ('정보통신공학'), ('전기공학'), ('전자공학'), ('기계공학'), ('건축학'), ('토목공학'), ('경영학'), ('회계학'), ('간호학'), ('의학'), ('약학')
ON CONFLICT DO NOTHING;

-- Insert sample stats
INSERT INTO qualification_stats (qual_id, year, exam_round, candidate_cnt, pass_cnt, pass_rate, difficulty_score) VALUES
(1, 2024, 1, 15000, 5250, 35.0, 7.5),
(1, 2024, 2, 16200, 5670, 35.0, 7.5),
(1, 2023, 1, 14500, 4785, 33.0, 7.8),
(1, 2023, 2, 15800, 5214, 33.0, 7.8),
(2, 2024, 1, 8000, 2800, 35.0, 6.5),
(3, 2024, 1, 12000, 7500, 62.5, 5.0),
(3, 2024, 2, 13500, 8100, 60.0, 5.2),
(3, 2023, 1, 11000, 6600, 60.0, 5.0),
(4, 2024, 1, 5000, 1500, 30.0, 8.0),
(5, 2024, 1, 8000, 3900, 48.7, 6.0),
(6, 2024, 1, 6000, 3300, 55.0, 5.5),
(7, 2024, 1, 7000, 2890, 41.3, 6.5),
(8, 2024, 1, 9000, 4500, 50.0, 5.8),
(9, 2024, 1, 5000, 1250, 25.0, 8.5),
(10, 2024, 1, 10000, 4000, 40.0, 7.0),
(11, 2024, 1, 8000, 3200, 40.0, 6.5)
ON CONFLICT DO NOTHING;

-- Insert major mappings
INSERT INTO major_qualification_map (major, qual_id, score, reason) VALUES
('컴퓨터공학', 1, 10.0, '전공과 직접 관련된 핵심 자격증'),
('컴퓨터공학', 2, 8.0, '기초 실무 역량 증명'),
('컴퓨터공학', 3, 9.0, '데이터베이스 필수 자격증'),
('컴퓨터공학', 4, 8.5, '고급 데이터베이스 역량'),
('컴퓨터공학', 5, 8.0, '시스템 관리 필수'),
('컴퓨터공학', 6, 7.0, '리눅스 기초'),
('컴퓨터공학', 7, 7.5, '네트워크 기초'),
('컴퓨터공학', 8, 6.5, '네트워크 입문'),
('컴퓨터공학', 9, 9.0, '보안 분야 필수'),
('소프트웨어공학', 1, 10.0, '전공과 직접 관련된 핵심 자격증'),
('소프트웨어공학', 3, 9.0, '데이터베이스 필수'),
('소프트웨어공학', 9, 8.5, '보안 역량'),
('정보통신공학', 1, 9.0, 'IT 기초 자격증'),
('정보통신공학', 7, 10.0, '네트워크 전공 핵심'),
('정보통신공학', 8, 8.5, '네트워크 기초'),
('정보통신공학', 5, 7.5, '시스템 관리'),
('정보통신공학', 9, 8.0, '네트워크 보안'),
('전기공학', 10, 10.0, '전공 핵심 자격증'),
('전기공학', 11, 8.0, '전기 기초'),
('전자공학', 12, 10.0, '전공 핵심 자격증'),
('기계공학', 13, 10.0, '전공 핵심 자격증'),
('건축학', 14, 10.0, '전공 핵심 자격증'),
('토목공학', 15, 10.0, '전공 핵심 자격증'),
('경영학', 16, 8.5, '회계 기초'),
('경영학', 17, 7.0, '회계 입문'),
('경영학', 18, 9.0, '금융 기획 전문'),
('회계학', 16, 10.0, '회계 전공 핵심'),
('회계학', 17, 8.5, '회계 기초'),
('간호학', 19, 10.0, '간호사 면허 필수'),
('의학', 20, 10.0, '의사 면허 필수'),
('약학', 21, 10.0, '약사 면허 필수')
ON CONFLICT DO NOTHING;
