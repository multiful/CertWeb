# -*- coding: utf-8 -*-
"""contrastive_profile_train_example.json p156~p300 (145건). 다양한 분야 자격증 + hard negative 비중 높임."""
import json
import sys

# 다양한 분야: 국가기술·국가민간·국가전문 (IT 외 회계·금융·행정·인사·부동산·조리 등)
CERT_TEXTS = {
    # IT·데이터
    "ADsP": "자격증명: ADsP\n자격종류: 국가민간자격\n관련직무: 데이터 분석, 데이터 시각화, 데이터 기반 의사결정\n관련전공: 산업데이터공학, 통계학, 컴퓨터공학\n추천대상: 데이터 분석 직무 입문자\n활용도: 데이터 분석 기초 역량을 증명한다.\n난이도: 입문\n설명: 데이터 이해, 분석 기획, 분석 결과 해석 역량을 평가한다.",
    "SQLD": "자격증명: SQLD\n자격종류: 국가민간자격\n관련직무: 데이터베이스, SQL 개발, 데이터 분석\n관련전공: 컴퓨터공학, 산업데이터공학\n추천대상: DB 및 개발 직무 입문자\n활용도: SQL 및 데이터베이스 실무 역량을 증명한다.\n난이도: 중\n설명: SQL 활용 및 데이터베이스 구축 역량을 평가한다.",
    "SQLP": "자격증명: SQLP\n자격종류: 국가공인 민간자격\n관련직무: 데이터베이스, SQL 고급 개발, 성능 튜닝\n관련전공: 컴퓨터공학, 산업데이터공학\n추천대상: SQLD 취득 후 심화, DB 전문가\n활용도: 고급 SQL 및 DB 설계 역량을 증명한다.\n난이도: 상\n설명: SQL 전문가 수준의 설계·튜닝 역량을 평가한다.",
    "정보처리기사": "자격증명: 정보처리기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산, IT, 시스템 구축\n관련전공: 컴퓨터공학, 소프트웨어학과\n추천대상: IT·개발 취업 준비생\n활용도: 개발 직무 기본 역량을 증명하는 대표 자격증\n난이도: 중상\n설명: 소프트웨어 설계, 프로그래밍, 데이터베이스, 운영체제 등을 평가한다.",
    "정보처리산업기사": "자격증명: 정보처리산업기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산\n추천대상: 정보처리기사 준비 전 단계\n설명: 정보처리기사보다 하위 등급.",
    "빅데이터분석기사": "자격증명: 빅데이터분석기사\n자격종류: 국가기술자격\n관련직무: 데이터 엔지니어링, 데이터 분석, 빅데이터 처리\n관련전공: 산업데이터공학, 통계학\n추천대상: 데이터 심화 준비생\n활용도: 빅데이터 처리 및 분석 역량을 증명한다.\n난이도: 중상\n설명: 빅데이터 기획·수집·분석·시각화 역량을 평가한다.",
    "컴퓨터활용능력 1급": "자격증명: 컴퓨터활용능력 1급\n자격종류: 국가기술자격\n관련직무: 사무, OA, 데이터 정리, 문서 작성\n관련전공: 전공 무관\n추천대상: 사무직, 취업 기초 준비생\n활용도: 엑셀·OA 실무 역량을 증명한다.\n난이도: 중\n설명: 스프레드시트와 데이터베이스 활용 능력을 평가한다.",
    "컴퓨터활용능력 2급": "자격증명: 컴퓨터활용능력 2급\n자격종류: 국가기술자격\n관련직무: 사무, OA\n설명: 입문 수준 사무 역량.",
    "리눅스마스터 1급": "자격증명: 리눅스마스터 1급\n자격종류: 국가민간자격\n관련직무: 서버 운영, 시스템 설계, 인프라\n관련전공: 컴퓨터공학\n추천대상: 인프라·시스템 심화 준비생\n활용도: 리눅스 고급 운영 역량을 증명한다.\n난이도: 상\n설명: 리눅스 시스템 설계 및 고급 관리 역량을 평가한다.",
    "리눅스마스터 2급": "자격증명: 리눅스마스터 2급\n자격종류: 국가민간자격\n관련직무: 서버 운영, 시스템 관리, 인프라\n관련전공: 컴퓨터공학\n추천대상: 인프라·시스템 운영 직무 준비생\n활용도: 리눅스 운영 역량을 증명한다.\n난이도: 중\n설명: 리눅스 운영체제 관리와 명령어 활용 능력을 평가한다.",
    "네트워크관리사 1급": "자격증명: 네트워크관리사 1급\n자격종류: 국가민간자격\n관련직무: 네트워크 설계, 인프라 관리\n관련전공: 정보통신공학, 컴퓨터공학\n추천대상: 네트워크 심화 준비생\n활용도: 네트워크 설계·관리 역량을 증명한다.\n난이도: 중\n설명: 네트워크 설계 및 고급 운영 역량을 평가한다.",
    "네트워크관리사 2급": "자격증명: 네트워크관리사 2급\n자격종류: 국가민간자격\n관련직무: 네트워크 운영, 인프라 관리\n관련전공: 정보통신공학, 컴퓨터공학\n추천대상: 네트워크 직무 입문자\n활용도: 네트워크 기초 역량을 증명한다.\n난이도: 입문\n설명: 네트워크 기초, 구축, 운영 역량을 평가한다.",
    "정보보안기사": "자격증명: 정보보안기사\n자격종류: 국가기술자격\n관련직무: 정보보안, 침해 대응\n추천대상: 보안 직무 준비생\n설명: 정보보안 관리 및 기술 역량을 평가한다.",
    "워드프로세서": "자격증명: 워드프로세서\n자격종류: 국가기술자격\n관련직무: 문서 작성, 사무 보조\n설명: 문서 작성 및 편집 능력을 평가한다.",
    # 회계·금융
    "전산회계 1급": "자격증명: 전산회계 1급\n자격종류: 국가민간자격\n관련직무: 회계, 경리\n추천대상: 회계 직무 준비생\n설명: 회계 처리와 전산 회계 프로그램 활용 능력을 평가한다.",
    "회계관리 1급": "자격증명: 회계관리 1급\n자격종류: 국가기술자격\n관련직무: 회계, 재무\n추천대상: 회계·재무 직무 준비생\n설명: 회계 관리 실무 역량을 평가한다.",
    "회계관리 2급": "자격증명: 회계관리 2급\n자격종류: 국가기술자격\n관련직무: 회계, 재무\n설명: 회계 기초 역량.",
    "세무사": "자격증명: 세무사\n자격종류: 국가전문자격\n관련직무: 세무, 회계\n추천대상: 세무·회계 전문가\n설명: 세무 업무 전문 역량을 평가한다.",
    "공인회계사": "자격증명: 공인회계사\n자격종류: 국가전문자격\n관련직무: 회계, 감사, 재무\n추천대상: 회계·감사 전문가\n설명: 회계·감사 전문 역량을 평가한다.",
    # 기타 국가기술·민간·전문
    "품질경영기사": "자격증명: 품질경영기사\n자격종류: 국가기술자격\n관련직무: 품질 관리, 생산 관리\n추천대상: 품질·생산 직무 준비생\n설명: 품질·생산 관리 직무.",
    "사회조사분석사": "자격증명: 사회조사분석사\n자격종류: 국가기술자격\n관련직무: 시장조사, 리서치, 데이터 수집\n관련전공: 경영학, 통계학, 사회학\n추천대상: 시장조사·리서치 직무 준비생\n설명: 설문 설계, 데이터 수집·분석 역량을 평가한다.",
    "공인중개사": "자격증명: 공인중개사\n자격종류: 국가전문자격\n관련직무: 부동산 중개, 컨설팅\n추천대상: 부동산 직무 준비생\n설명: 부동산 중개 및 관련 법규 역량을 평가한다.",
    "비서": "자격증명: 비서\n자격종류: 국가기술자격\n관련직무: 사무 보조, 행정, 스케줄 관리\n추천대상: 사무·비서 직무 준비생\n설명: 비서 실무 및 문서·일정 관리 역량을 평가한다.",
    "한식조리기능사": "자격증명: 한식조리기능사\n자격종류: 국가기술자격\n관련직무: 한식 조리, 외식\n추천대상: 조리·외식 직무 준비생\n설명: 한식 조리 기술 역량을 평가한다.",
    "감정평가사": "자격증명: 감정평가사\n자격종류: 국가전문자격\n관련직무: 부동산·동산 감정평가\n추천대상: 감정평가 전문가\n설명: 감정평가 실무 역량을 평가한다.",
    "변리사": "자격증명: 변리사\n자격종류: 국가전문자격\n관련직무: 특허·지식재산권\n추천대상: 지식재산권 직무 준비생\n설명: 특허 출원·관리 역량을 평가한다.",
    "노무사": "자격증명: 노무사\n자격종류: 국가전문자격\n관련직무: 노동법, 인사·노무\n추천대상: 노무·인사 직무 준비생\n설명: 노동법·노무 실무 역량을 평가한다.",
    "전기기사": "자격증명: 전기기사\n자격종류: 국가기술자격\n관련직무: 전기 설계, 전력 시스템\n설명: 전기 이론 및 설계 역량을 평가한다.",
    "전기산업기사": "자격증명: 전기산업기사\n자격종류: 국가기술자격\n관련직무: 전기, 전력\n설명: 전기 실무 역량을 평가한다.",
}

def _t(name: str) -> str:
    return CERT_TEXTS.get(name, f"자격증명: {name}\n설명: (설명 텍스트)")

def neg(qual_id: int, qual_name: str, negative_type: str, text: str) -> dict:
    return {"qual_id": qual_id, "qual_name": qual_name, "negative_type": negative_type, "text": text}

def pos(qual_id: int, qual_name: str) -> dict:
    return {"qual_id": qual_id, "qual_name": qual_name, "text": _t(qual_name)}

def entry(query_id: str, raw_query: str, profile: dict, rewritten_query: str, query_type: str, positive: dict, negatives: list) -> dict:
    return {"query_id": query_id, "raw_query": raw_query, "profile": profile, "rewritten_query": rewritten_query, "query_type": query_type, "positive": positive, "negatives": negatives}

def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    entries = []
    pid = 156
    pos_id = 260
    neg_id = 501

    majors = ["산업데이터공학과", "컴퓨터공학과", "소프트웨어학과", "경영정보학과", "통계학과", "경영학과", "행정학과", "정보보호학과", "정보통신공학과", "산업공학과", "경제학과", "국어국문학과", "심리학과", "회계학과", "전기공학과", "전자공학과"]
    query_types = ["natural", "keyword", "profile_personalized", "purpose_only", "followup_after_acquired", "career_transition", "career_goal", "early_stage", "cert_name_included"]

    # Hard negative 위주: 같은 IT/데이터 계열, 같은 자격종류, 같은 추천대상 다른 직무, 하위 단계, bookmark 혼동, 검색 오답. 쉬운 오답(different_domain) 최소화.
    templates = [
        ("데이터 분석 쪽 일하고 싶어", "데이터 분석", "ADsP", [("정보보안기사", "same_it_but_wrong_job"), ("빅데이터분석기사", "same_data_domain_wrong_job")]),
        ("개발자 되려면 뭐 따야 해", "개발", "정보처리기사", [("빅데이터분석기사", "adjacent_data_role"), ("리눅스마스터 2급", "infra_role")]),
        ("DB 쪽 취업하고 싶어", "데이터베이스", "SQLD", [("정보처리기사", "same_qual_type"), ("ADsP", "same_data_domain_wrong_job")]),
        ("사무직 취업용 자격증 알려줘", "사무", "컴퓨터활용능력 1급", [("SQLD", "good_but_not_primary_goal"), ("정보처리기사", "it_specialized")]),
        ("빅데이터 쪽 하고 싶어", "빅데이터", "빅데이터분석기사", [("ADsP", "same_data_domain_wrong_job"), ("컴퓨터활용능력 2급", "lower_than_acquired")]),
        ("서버 운영 쪽 가고 싶어", "서버, 시스템 운영", "리눅스마스터 2급", [("ADsP", "same_data_domain_wrong_job"), ("SQLD", "db_focus_not_server")]),
        ("네트워크 쪽 일 하고 싶어", "네트워크", "네트워크관리사 2급", [("ADsP", "same_data_domain_wrong_job"), ("리눅스마스터 2급", "same_target_different_job")]),
        ("보안 쪽 취업하고 싶어", "정보보안", "정보보안기사", [("정보처리기사", "retrieval_frequent_false_positive"), ("네트워크관리사 2급", "same_it_but_wrong_job")]),
        ("1학년인데 미리 뭐 할까", "(쿼리 미포함)", "컴퓨터활용능력 1급", [("빅데이터분석기사", "too_advanced_for_grade"), ("정보처리기사", "too_advanced_for_grade")]),
        ("정처기 다음 뭐 할까", "(쿼리 미포함)", "SQLD", [("정보처리산업기사", "lower_than_acquired"), ("컴퓨터활용능력 2급", "too_basic")]),
        ("SQLD 다음에 뭐 따면 좋아", "데이터베이스, 개발", "정보처리기사", [("정보처리산업기사", "lower_than_acquired"), ("ADsP", "bookmark_confusable")]),
        ("ADsP 다음에 뭐 할까", "데이터 분석", "SQLD", [("컴퓨터활용능력 2급", "lower_than_acquired"), ("사회조사분석사", "same_target_different_job")]),
        ("비전공인데 IT 쪽 가고 싶어", "IT", "정보처리기사", [("전산회계 1급", "same_qual_type"), ("회계관리 1급", "same_target_different_job")]),
        ("회계 말고 전산 쪽으로 가고 싶어", "전산", "정보처리기사", [("전산회계 1급", "bookmark_confusable"), ("회계관리 1급", "already_acquired_same_domain")]),
        ("문서·엑셀 쓰는 직무로 가고 싶어", "사무, 데이터 활용", "컴퓨터활용능력 1급", [("빅데이터분석기사", "too_advanced_for_goal"), ("SQLD", "retrieval_frequent_false_positive")]),
        ("공기업 가산점용 자격증 뭐가 좋아", "공기업, 사무", "컴퓨터활용능력 1급", [("SQLD", "good_but_not_primary_goal"), ("정보처리기사", "it_specialized")]),
        ("데이터 시각화 쪽 하고 싶어", "데이터 시각화", "ADsP", [("리눅스마스터 2급", "same_it_but_wrong_job"), ("정보보안기사", "same_it_but_wrong_job")]),
        ("인프라 쪽 일 하고 싶어", "인프라", "리눅스마스터 2급", [("SQLD", "db_focus_not_server"), ("ADsP", "same_data_domain_wrong_job")]),
        ("전산 직무 추천해줘", "전산", "정보처리기사", [("품질경영기사", "same_qual_type"), ("전산회계 1급", "bookmark_confusable")]),
        ("데이터랑 통계 쪽 커리어 쌓고 싶어", "데이터 분석, 통계", "ADsP", [("사회조사분석사", "same_target_different_job"), ("빅데이터분석기사", "same_data_domain_wrong_job")]),
        ("실무적으로 바로 쓰는 개발 자격증 있을까", "개발", "정보처리기사", [("컴퓨터활용능력 1급", "useful_but_not_best_match"), ("SQLD", "retrieval_frequent_false_positive")]),
        ("백엔드 개발 쪽 가고 싶어", "백엔드 개발", "정보처리기사", [("네트워크관리사 2급", "infra_role"), ("리눅스마스터 2급", "same_it_but_wrong_job")]),
        ("데이터 직무 준비하는데 SQL 꼭 챙기고 싶어", "데이터 직무", "SQLD", [("정보보안기사", "same_it_but_wrong_job"), ("빅데이터분석기사", "same_data_domain_wrong_job")]),
        ("분석 말고 운영 쪽이 맞는 것 같아", "시스템 운영", "리눅스마스터 2급", [("ADsP", "bookmark_confusable"), ("SQLD", "db_focus_not_ops")]),
        ("취업 전에 데이터 자격증 하나 챙기고 싶어", "데이터 활용", "ADsP", [("리눅스마스터 2급", "same_it_but_wrong_job"), ("네트워크관리사 2급", "same_it_but_wrong_job")]),
        ("지금까지 딴 거 바탕으로 더 좋은 거 추천해줘", "데이터 분석, 개발", "빅데이터분석기사", [("컴퓨터활용능력 2급", "lower_than_acquired"), ("ADsP", "too_easy_given_acquired")]),
        ("OA는 했고 이제 한 단계 더 가고 싶어", "사무, 데이터 활용", "SQLD", [("컴퓨터활용능력 2급", "lower_than_acquired"), ("워드프로세서", "same_level_basic_office")]),
        ("데이터 관련해서 더 어려운 걸 해보고 싶어", "데이터 분석", "빅데이터분석기사", [("ADsP", "too_easy_given_acquired"), ("SQLD", "retrieval_frequent_false_positive")]),
        ("SQL 전문가 쪽 가고 싶어", "데이터베이스", "SQLP", [("정보처리산업기사", "lower_than_acquired"), ("정보처리기사", "same_qual_type")]),
        ("리눅스 1급 도전해보고 싶어", "서버, 시스템", "리눅스마스터 1급", [("리눅스마스터 2급", "lower_than_acquired"), ("네트워크관리사 2급", "same_it_but_wrong_job")]),
        ("네트워크 1급 있으면 좋을까", "네트워크", "네트워크관리사 1급", [("네트워크관리사 2급", "lower_than_acquired"), ("ADsP", "same_data_domain_wrong_job")]),
        ("회계 쪽 자격증 뭐가 있어", "회계", "전산회계 1급", [("회계관리 1급", "same_target_different_job"), ("정보처리기사", "same_qual_type")]),
        ("품질 관리 쪽 취업하고 싶어", "품질 관리", "품질경영기사", [("정보처리기사", "same_qual_type"), ("전산회계 1급", "same_target_different_job")]),
        ("2학년인데 미리 뭐 할까", "(쿼리 미포함)", "컴퓨터활용능력 1급", [("빅데이터분석기사", "too_advanced_for_grade"), ("정보처리기사", "retrieval_frequent_false_positive")]),
        ("개발이랑 DB 둘 다 챙기고 싶어", "개발, 데이터베이스", "SQLD", [("정보보안기사", "same_it_but_wrong_job"), ("ADsP", "same_data_domain_wrong_job")]),
        ("데이터 분석이랑 기획 둘 다 하고 싶어", "데이터 분석, 분석 기획", "ADsP", [("리눅스마스터 2급", "same_it_but_wrong_job"), ("빅데이터분석기사", "same_data_domain_wrong_job")]),
        ("사무직인데 데이터도 다루고 싶어", "사무, 데이터 활용", "컴퓨터활용능력 1급", [("빅데이터분석기사", "too_advanced_for_goal"), ("SQLD", "retrieval_frequent_false_positive")]),
        ("뭐 따면 좋을까", "(쿼리 미포함)", "정보처리기사", [("컴퓨터활용능력 2급", "lower_than_acquired"), ("정보처리산업기사", "lower_than_acquired")]),
        ("IT 쪽 취업하고 싶어", "IT", "정보처리기사", [("빅데이터분석기사", "adjacent_data_role"), ("정보보안기사", "same_it_but_wrong_job")]),
        ("데이터베이스랑 개발 둘 다 하고 싶어", "데이터베이스, 개발", "SQLD", [("정보처리기사", "retrieval_frequent_false_positive"), ("ADsP", "same_data_domain_wrong_job")]),
        ("미리 준비하고 싶어", "(쿼리 미포함)", "컴퓨터활용능력 1급", [("정보보안기사", "too_advanced_for_grade"), ("빅데이터분석기사", "too_advanced_for_grade")]),
        ("컴활만 있는데 IT로 가려면", "IT", "정보처리기사", [("전산회계 1급", "same_qual_type"), ("회계관리 1급", "same_target_different_job")]),
        ("취업용으로 실무 쪽", "실무", "SQLD", [("정보처리산업기사", "lower_than_acquired"), ("컴퓨터활용능력 2급", "too_basic")]),
        ("도전하고 싶어", "(쿼리 미포함)", "빅데이터분석기사", [("컴퓨터활용능력 2급", "lower_than_acquired"), ("정보처리산업기사", "lower_than_acquired")]),
        # 비공대·다양 분야
        ("시장조사 리서치 쪽 하고 싶어", "시장조사, 리서치", "사회조사분석사", [("ADsP", "same_data_domain_wrong_job"), ("정보처리기사", "same_qual_type")]),
        ("부동산 중개 쪽 취업하고 싶어", "부동산", "공인중개사", [("감정평가사", "same_target_different_job"), ("세무사", "same_qual_type")]),
        ("비서·행정 쪽 자격증 뭐가 있어", "비서, 행정", "비서", [("컴퓨터활용능력 1급", "retrieval_frequent_false_positive"), ("워드프로세서", "same_qual_type")]),
        ("조리·외식 쪽 하고 싶어", "조리", "한식조리기능사", [("컴퓨터활용능력 1급", "same_qual_type"), ("비서", "same_target_different_job")]),
        ("인사·노무 쪽 자격증 알려줘", "인사, 노무", "노무사", [("회계관리 1급", "same_target_different_job"), ("전산회계 1급", "bookmark_confusable")]),
        ("세무 쪽 전문가 되려면", "세무", "세무사", [("공인회계사", "same_target_different_job"), ("전산회계 1급", "lower_than_acquired")]),
    ]

    def make_rewritten(major: str, grade: int, job: str, fav: list, acq: list, purpose: str) -> str:
        fav_s = ", ".join(fav) if fav else "없음"
        acq_s = ", ".join(acq) if acq else "없음"
        return f"전공: {major}\n학년: {grade}학년\n희망직무: {job}\n관심 자격증: {fav_s}\n취득 자격증: {acq_s}\n목적: {purpose}"

    idx = 0
    for i in range(145):
        t = templates[i % len(templates)]
        raw_query, job, pos_cert, neg_list = t
        m = majors[i % len(majors)]
        g = (i % 4) + 1
        qt = query_types[i % len(query_types)]
        fav = [pos_cert] if i % 3 != 0 else []
        acq = [] if i % 4 != 0 else (["컴퓨터활용능력 1급"] if "컴퓨터활용" in pos_cert or "사무" in job else [])
        if "다음" in raw_query or "딴 다음" in raw_query:
            acq = [pos_cert] if pos_cert in ["SQLD", "정보처리기사", "ADsP"] else acq
        purpose = "취업 준비" if g >= 3 else "자격증 추천"
        if "다음" in raw_query or "한 단계" in raw_query:
            purpose = "다음 단계 자격증 추천"
        if "가산점" in raw_query:
            purpose = "가산점, 취업 준비"
        rewritten = make_rewritten(m, g, job, fav, acq, purpose)

        n1_name, n1_type = neg_list[0]
        n2_name, n2_type = neg_list[1]
        negatives = [
            neg(neg_id, n1_name, n1_type, _t(n1_name)),
            neg(neg_id + 1, n2_name, n2_type, _t(n2_name)),
        ]
        entries.append(entry(
            f"p{pid}",
            raw_query,
            {"major": m, "grade_level": g, "favorite_cert_names": fav, "acquired_cert_names": acq},
            rewritten,
            qt,
            pos(pos_id, pos_cert),
            negatives,
        ))
        pid += 1
        pos_id += 1
        neg_id += 2

    result = json.dumps(entries, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
    else:
        print(result)
    return len(entries)

if __name__ == "__main__":
    n = main()
    print(f"Generated {n} entries (p156–p300).", file=sys.stderr)
