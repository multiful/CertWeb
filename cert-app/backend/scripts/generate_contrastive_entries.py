# -*- coding: utf-8 -*-
"""contrastive_profile_train_example.json 에 추가할 p041~p155 항목 생성 (README 원칙 준수)."""
import json
import sys

# 자격증 텍스트 템플릿 (qual_name -> text)
CERT_TEXTS = {
    "ADsP": "자격증명: ADsP\n자격종류: 국가민간자격\n관련직무: 데이터 분석, 데이터 시각화, 데이터 기반 의사결정\n관련전공: 산업데이터공학, 통계학, 컴퓨터공학\n추천대상: 데이터 분석 직무 입문자\n활용도: 데이터 분석 기초 역량을 증명한다.\n난이도: 입문\n설명: 데이터 이해, 분석 기획, 분석 결과 해석 역량을 평가한다.",
    "SQLD": "자격증명: SQLD\n자격종류: 국가민간자격\n관련직무: 데이터베이스, SQL 개발, 데이터 분석\n관련전공: 컴퓨터공학, 산업데이터공학\n추천대상: DB 및 개발 직무 입문자\n활용도: SQL 및 데이터베이스 실무 역량을 증명한다.\n난이도: 중\n설명: SQL 활용 및 데이터베이스 구축 역량을 평가한다.",
    "정보처리기사": "자격증명: 정보처리기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산, IT, 시스템 구축\n관련전공: 컴퓨터공학, 소프트웨어학과\n추천대상: IT·개발 취업 준비생\n활용도: 개발 직무 기본 역량을 증명하는 대표 자격증\n난이도: 중상\n설명: 소프트웨어 설계, 프로그래밍, 데이터베이스, 운영체제 등을 평가한다.",
    "빅데이터분석기사": "자격증명: 빅데이터분석기사\n자격종류: 국가기술자격\n관련직무: 데이터 엔지니어링, 데이터 분석, 빅데이터 처리\n관련전공: 산업데이터공학, 통계학\n추천대상: 데이터 심화 준비생\n활용도: 빅데이터 처리 및 분석 역량을 증명한다.\n난이도: 중상\n설명: 빅데이터 기획·수집·분석·시각화 역량을 평가한다.",
    "컴퓨터활용능력 1급": "자격증명: 컴퓨터활용능력 1급\n자격종류: 국가기술자격\n관련직무: 사무, OA, 데이터 정리, 문서 작성\n관련전공: 전공 무관\n추천대상: 사무직, 취업 기초 준비생\n활용도: 엑셀·OA 실무 역량을 증명한다.\n난이도: 중\n설명: 스프레드시트와 데이터베이스 활용 능력을 평가한다.",
    "컴퓨터활용능력 2급": "자격증명: 컴퓨터활용능력 2급\n자격종류: 국가기술자격\n관련직무: 사무, OA\n설명: 입문 수준 사무 역량.",
    "리눅스마스터 2급": "자격증명: 리눅스마스터 2급\n자격종류: 국가민간자격\n관련직무: 서버 운영, 시스템 관리, 인프라\n관련전공: 컴퓨터공학\n추천대상: 인프라·시스템 운영 직무 준비생\n활용도: 리눅스 운영 역량을 증명한다.\n난이도: 중\n설명: 리눅스 운영체제 관리와 명령어 활용 능력을 평가한다.",
    "네트워크관리사 2급": "자격증명: 네트워크관리사 2급\n자격종류: 국가민간자격\n관련직무: 네트워크 운영, 인프라 관리\n관련전공: 정보통신공학, 컴퓨터공학\n추천대상: 네트워크 직무 입문자\n활용도: 네트워크 기초 역량을 증명한다.\n난이도: 입문\n설명: 네트워크 기초, 구축, 운영 역량을 평가한다.",
    "정보보안기사": "자격증명: 정보보안기사\n자격종류: 국가기술자격\n관련직무: 정보보안, 침해 대응\n추천대상: 보안 직무 준비생\n설명: 정보보안 관리 및 기술 역량을 평가한다.",
    "워드프로세서": "자격증명: 워드프로세서\n자격종류: 국가기술자격\n관련직무: 문서 작성, 사무 보조\n설명: 문서 작성 및 편집 능력을 평가한다.",
    "전산회계 1급": "자격증명: 전산회계 1급\n자격종류: 국가민간자격\n관련직무: 회계, 경리\n추천대상: 회계 직무 준비생\n설명: 회계 처리와 전산 회계 프로그램 활용 능력을 평가한다.",
    "정보처리산업기사": "자격증명: 정보처리산업기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산\n설명: 정보처리기사보다 하위 등급.",
    "전기기사": "자격증명: 전기기사\n자격종류: 국가기술자격\n관련직무: 전기 설계, 전력 시스템\n설명: 전기 이론 및 설계 역량을 평가한다.",
    "세무사": "자격증명: 세무사\n자격종류: 국가전문자격\n관련직무: 세무, 회계\n설명: 세무 업무 전문 역량을 평가한다.",
    "품질경영기사": "자격증명: 품질경영기사\n자격종류: 국가기술자격\n관련직무: 품질 관리, 생산 관리\n설명: 품질·생산 관리 직무.",
}

def neg(qual_id: int, qual_name: str, negative_type: str, text: str) -> dict:
    return {"qual_id": qual_id, "qual_name": qual_name, "negative_type": negative_type, "text": text}

def pos(qual_id: int, qual_name: str) -> dict:
    return {"qual_id": qual_id, "qual_name": qual_name, "text": CERT_TEXTS.get(qual_name, f"자격증명: {qual_name}\n설명: (설명 텍스트)")}

def entry(query_id: str, raw_query: str, profile: dict, rewritten_query: str, query_type: str, positive: dict, negatives: list) -> dict:
    return {
        "query_id": query_id,
        "raw_query": raw_query,
        "profile": profile,
        "rewritten_query": rewritten_query,
        "query_type": query_type,
        "positive": positive,
        "negatives": negatives,
    }

def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    entries = []
    pid = 41
    pos_id = 145
    neg_id = 271

    # p041–p055: 데이터·개발·DB·사무 다양
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "데이터 분석 쪽 취업하고 싶어",
            {"major": "통계학과", "grade_level": 4, "favorite_cert_names": ["ADsP"], "acquired_cert_names": []},
            "전공: 통계학과\n학년: 4학년\n희망직무: 데이터 분석\n관심 자격증: ADsP\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "ADsP"),
            [neg(neg_id, "정보보안기사", "same_it_but_wrong_job", CERT_TEXTS["정보보안기사"]), neg(neg_id+1, "전기기사", "different_domain", CERT_TEXTS["전기기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    entries.append(entry(
        f"p{pid}", "개발 쪽 자격증 뭐가 좋아",
        {"major": "컴퓨터공학과", "grade_level": 2, "favorite_cert_names": [], "acquired_cert_names": []},
        "전공: 컴퓨터공학과\n학년: 2학년\n희망직무: 개발\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 자격증 추천",
        "keyword", pos(pos_id, "정보처리기사"),
        [neg(neg_id, "전산회계 1급", "different_office_domain", CERT_TEXTS["전산회계 1급"]), neg(neg_id+1, "워드프로세서", "office_only", CERT_TEXTS["워드프로세서"])]
    ))
    pid += 1; pos_id += 1; neg_id += 2

    for _ in range(3):
        entries.append(entry(
            f"p{pid}", "DB나 데이터 다루는 직무 추천해줘",
            {"major": "경영정보학과", "grade_level": 3, "favorite_cert_names": ["SQLD"], "acquired_cert_names": ["컴퓨터활용능력 1급"]},
            "전공: 경영정보학과\n학년: 3학년\n희망직무: 데이터베이스, 데이터\n관심 자격증: SQLD\n취득 자격증: 컴퓨터활용능력 1급\n목적: 취업 준비",
            "natural", pos(pos_id, "SQLD"),
            [neg(neg_id, "정보보안기사", "same_it_but_wrong_job", CERT_TEXTS["정보보안기사"]), neg(neg_id+1, "품질경영기사", "industrial_but_not_it", CERT_TEXTS["품질경영기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    entries.append(entry(
        f"p{pid}", "사무직 취업용 자격증 알려줘",
        {"major": "행정학과", "grade_level": 4, "favorite_cert_names": ["컴퓨터활용능력 1급"], "acquired_cert_names": []},
        "전공: 행정학과\n학년: 4학년\n희망직무: 사무\n관심 자격증: 컴퓨터활용능력 1급\n취득 자격증: 없음\n목적: 취업 준비",
        "purpose_only", pos(pos_id, "컴퓨터활용능력 1급"),
        [neg(neg_id, "SQLD", "good_but_not_primary_goal", "자격증명: SQLD\n관련직무: 데이터베이스, 개발\n설명: 사무 대표 자격증은 아님."), neg(neg_id+1, "정보처리기사", "it_specialized", "자격증명: 정보처리기사\n관련직무: 개발, IT\n설명: IT 직무 중심.")]
    ))
    pid += 1; pos_id += 1; neg_id += 2

    # p046–p060
    entries.append(entry(
        f"p{pid}", "빅데이터 쪽 하고 싶어",
        {"major": "산업데이터공학과", "grade_level": 4, "favorite_cert_names": ["ADsP", "SQLD"], "acquired_cert_names": ["ADsP"]},
        "전공: 산업데이터공학과\n학년: 4학년\n희망직무: 빅데이터\n관심 자격증: ADsP, SQLD\n취득 자격증: ADsP\n목적: 취업 준비",
        "natural", pos(pos_id, "빅데이터분석기사"),
        [neg(neg_id, "컴퓨터활용능력 2급", "too_basic_given_profile", CERT_TEXTS["컴퓨터활용능력 2급"]), neg(neg_id+1, "워드프로세서", "office_basic", CERT_TEXTS["워드프로세서"])]
    ))
    pid += 1; pos_id += 1; neg_id += 2

    for _ in range(4):
        entries.append(entry(
            f"p{pid}", "인프라나 서버 쪽 일 하고 싶어",
            {"major": "소프트웨어학과", "grade_level": 3, "favorite_cert_names": ["리눅스마스터 2급"], "acquired_cert_names": []},
            "전공: 소프트웨어학과\n학년: 3학년\n희망직무: 인프라, 서버\n관심 자격증: 리눅스마스터 2급\n취득 자격증: 없음\n목적: 취업 준비",
            "keyword", pos(pos_id, "리눅스마스터 2급"),
            [neg(neg_id, "ADsP", "data_not_infra", "자격증명: ADsP\n관련직무: 데이터 분석\n설명: 데이터 직무 중심."), neg(neg_id+1, "전산회계 1급", "different_domain", CERT_TEXTS["전산회계 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    entries.append(entry(
        f"p{pid}", "1학년인데 뭐부터 할까",
        {"major": "컴퓨터공학과", "grade_level": 1, "favorite_cert_names": [], "acquired_cert_names": []},
        "전공: 컴퓨터공학과\n학년: 1학년\n희망직무: (쿼리 미포함)\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 자격증 추천",
        "early_stage", pos(pos_id, "컴퓨터활용능력 1급"),
        [neg(neg_id, "빅데이터분석기사", "too_advanced_for_grade", "자격증명: 빅데이터분석기사\n관련직무: 빅데이터 분석\n설명: 심화 수준."), neg(neg_id+1, "정보보안기사", "too_advanced_for_grade", CERT_TEXTS["정보보안기사"])]
    ))
    pid += 1; pos_id += 1; neg_id += 2

    for _ in range(4):
        entries.append(entry(
            f"p{pid}", "전공 살려서 데이터 쪽 가고 싶어",
            {"major": "경영학과", "grade_level": 4, "favorite_cert_names": [], "acquired_cert_names": ["컴퓨터활용능력 1급"]},
            "전공: 경영학과\n학년: 4학년\n희망직무: 데이터\n관심 자격증: 없음\n취득 자격증: 컴퓨터활용능력 1급\n목적: 취업 준비",
            "natural", pos(pos_id, "ADsP"),
            [neg(neg_id, "세무사", "same_background_but_wrong_goal", CERT_TEXTS["세무사"]), neg(neg_id+1, "전산회계 1급", "business_office_domain", CERT_TEXTS["전산회계 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p056–p070
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "코딩이랑 개발 쪽 준비하고 있어",
            {"major": "산업데이터공학과", "grade_level": 3, "favorite_cert_names": ["정보처리기사"], "acquired_cert_names": []},
            "전공: 산업데이터공학과\n학년: 3학년\n희망직무: 개발\n관심 자격증: 정보처리기사\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "정보처리기사"),
            [neg(neg_id, "빅데이터분석기사", "adjacent_data_role", CERT_TEXTS["빅데이터분석기사"]), neg(neg_id+1, "네트워크관리사 2급", "infra_role", CERT_TEXTS["네트워크관리사 2급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    entries.append(entry(
        f"p{pid}", "ADsP 다음에 뭐 따면 좋아",
        {"major": "통계학과", "grade_level": 4, "favorite_cert_names": ["ADsP"], "acquired_cert_names": ["ADsP"]},
        "전공: 통계학과\n학년: 4학년\n희망직무: 데이터 분석\n관심 자격증: ADsP\n취득 자격증: ADsP\n목적: 다음 단계 자격증 추천",
        "followup_after_acquired", pos(pos_id, "SQLD"),
        [neg(neg_id, "컴퓨터활용능력 2급", "far_too_basic", CERT_TEXTS["컴퓨터활용능력 2급"]), neg(neg_id+1, "워드프로세서", "office_basic", CERT_TEXTS["워드프로세서"])]
    ))
    pid += 1; pos_id += 1; neg_id += 2

    for _ in range(4):
        entries.append(entry(
            f"p{pid}", "문서랑 엑셀 쓸 줄 아는 수준인데 더 배우고 싶어",
            {"major": "경영학과", "grade_level": 3, "favorite_cert_names": ["컴퓨터활용능력 1급"], "acquired_cert_names": []},
            "전공: 경영학과\n학년: 3학년\n희망직무: 사무, 데이터 활용\n관심 자격증: 컴퓨터활용능력 1급\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "컴퓨터활용능력 1급"),
            [neg(neg_id, "빅데이터분석기사", "too_advanced_for_goal", "자격증명: 빅데이터분석기사\n관련직무: 빅데이터 분석\n설명: 심화 수준."), neg(neg_id+1, "정보보안기사", "wrong_domain", CERT_TEXTS["정보보안기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p062–p080
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "네트워크 관리 쪽 일 하고 싶어",
            {"major": "정보통신공학과", "grade_level": 2, "favorite_cert_names": [], "acquired_cert_names": []},
            "전공: 정보통신공학과\n학년: 2학년\n희망직무: 네트워크\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 취업 준비",
            "keyword", pos(pos_id, "네트워크관리사 2급"),
            [neg(neg_id, "ADsP", "data_not_network", "자격증명: ADsP\n관련직무: 데이터 분석\n설명: 데이터 직무."), neg(neg_id+1, "전기기사", "different_domain", CERT_TEXTS["전기기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "보안 쪽 취업하고 싶어",
            {"major": "정보보호학과", "grade_level": 3, "favorite_cert_names": ["정보보안기사"], "acquired_cert_names": []},
            "전공: 정보보호학과\n학년: 3학년\n희망직무: 정보보안\n관심 자격증: 정보보안기사\n취득 자격증: 없음\n목적: 취업 준비",
            "keyword", pos(pos_id, "정보보안기사"),
            [neg(neg_id, "정보처리기사", "it_but_wrong_focus", "자격증명: 정보처리기사\n관련직무: 개발, 전산\n설명: 개발 직무 중심."), neg(neg_id+1, "전산회계 1급", "different_domain", CERT_TEXTS["전산회계 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "SQL이랑 데이터 같이 하고 싶어",
            {"major": "산업데이터공학과", "grade_level": 3, "favorite_cert_names": ["SQLD", "ADsP"], "acquired_cert_names": []},
            "전공: 산업데이터공학과\n학년: 3학년\n희망직무: 데이터, SQL\n관심 자격증: SQLD, ADsP\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "SQLD"),
            [neg(neg_id, "리눅스마스터 2급", "infra_focus", CERT_TEXTS["리눅스마스터 2급"]), neg(neg_id+1, "워드프로세서", "office_only", CERT_TEXTS["워드프로세서"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p078–p095
    for _ in range(6):
        entries.append(entry(
            f"p{pid}", "취업용으로 하나쯤 따두고 싶어",
            {"major": "경제학과", "grade_level": 4, "favorite_cert_names": [], "acquired_cert_names": []},
            "전공: 경제학과\n학년: 4학년\n희망직무: (쿼리 미포함)\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 취업 준비",
            "purpose_only", pos(pos_id, "컴퓨터활용능력 1급"),
            [neg(neg_id, "세무사", "different_domain", CERT_TEXTS["세무사"]), neg(neg_id+1, "정보보안기사", "it_specialized", CERT_TEXTS["정보보안기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "정처기 따고 나서 뭐 할까",
            {"major": "컴퓨터공학과", "grade_level": 4, "favorite_cert_names": ["정보처리기사"], "acquired_cert_names": ["정보처리기사"]},
            "전공: 컴퓨터공학과\n학년: 4학년\n희망직무: (쿼리 미포함)\n관심 자격증: 정보처리기사\n취득 자격증: 정보처리기사\n목적: 다음 단계 자격증 추천",
            "cert_name_included", pos(pos_id, "SQLD"),
            [neg(neg_id, "정보처리산업기사", "lower_than_acquired", CERT_TEXTS["정보처리산업기사"]), neg(neg_id+1, "컴퓨터활용능력 2급", "too_basic", CERT_TEXTS["컴퓨터활용능력 2급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "데이터 기획이랑 분석 둘 다 관심 있어",
            {"major": "경영정보학과", "grade_level": 4, "favorite_cert_names": ["ADsP"], "acquired_cert_names": ["컴퓨터활용능력 1급"]},
            "전공: 경영정보학과\n학년: 4학년\n희망직무: 데이터 기획, 데이터 분석\n관심 자격증: ADsP\n취득 자격증: 컴퓨터활용능력 1급\n목적: 취업 준비",
            "natural", pos(pos_id, "ADsP"),
            [neg(neg_id, "리눅스마스터 2급", "infra_focus", CERT_TEXTS["리눅스마스터 2급"]), neg(neg_id+1, "네트워크관리사 2급", "network_focus", CERT_TEXTS["네트워크관리사 2급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p096–p115
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "비전공인데 개발 배우고 있어",
            {"major": "국어국문학과", "grade_level": 3, "favorite_cert_names": [], "acquired_cert_names": []},
            "전공: 국어국문학과\n학년: 3학년\n희망직무: 개발\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 직무 전환, 취업 준비",
            "career_transition", pos(pos_id, "정보처리기사"),
            [neg(neg_id, "세무사", "same_humanities_but_wrong_goal", CERT_TEXTS["세무사"]), neg(neg_id+1, "전산회계 1급", "office_finance_domain", CERT_TEXTS["전산회계 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "컴활 있으면 다음에 뭐가 좋아",
            {"major": "행정학과", "grade_level": 4, "favorite_cert_names": ["컴퓨터활용능력 1급"], "acquired_cert_names": ["컴퓨터활용능력 1급"]},
            "전공: 행정학과\n학년: 4학년\n희망직무: 사무, 데이터 활용\n관심 자격증: 컴퓨터활용능력 1급\n취득 자격증: 컴퓨터활용능력 1급\n목적: 다음 단계 자격증 추천",
            "followup_after_acquired", pos(pos_id, "SQLD"),
            [neg(neg_id, "컴퓨터활용능력 2급", "lower_than_acquired", CERT_TEXTS["컴퓨터활용능력 2급"]), neg(neg_id+1, "워드프로세서", "same_level_basic_office", CERT_TEXTS["워드프로세서"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "프론트엔드 말고 백엔드 쪽 가고 싶어",
            {"major": "소프트웨어학과", "grade_level": 4, "favorite_cert_names": ["정보처리기사"], "acquired_cert_names": []},
            "전공: 소프트웨어학과\n학년: 4학년\n희망직무: 백엔드 개발\n관심 자격증: 정보처리기사\n취득 자격증: 없음\n목적: 취업 준비",
            "career_goal", pos(pos_id, "정보처리기사"),
            [neg(neg_id, "네트워크관리사 2급", "infra_not_dev", CERT_TEXTS["네트워크관리사 2급"]), neg(neg_id+1, "컴퓨터활용능력 1급", "office_not_dev", CERT_TEXTS["컴퓨터활용능력 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "데이터 시각화 쪽 하고 싶어",
            {"major": "산업데이터공학과", "grade_level": 3, "favorite_cert_names": ["ADsP"], "acquired_cert_names": []},
            "전공: 산업데이터공학과\n학년: 3학년\n희망직무: 데이터 시각화\n관심 자격증: ADsP\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "ADsP"),
            [neg(neg_id, "리눅스마스터 2급", "infra_role", CERT_TEXTS["리눅스마스터 2급"]), neg(neg_id+1, "정보보안기사", "same_it_but_wrong_job", CERT_TEXTS["정보보안기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p116–p135
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "엑셀 데이터 정리하는 직무로 가고 싶어",
            {"major": "경영학과", "grade_level": 4, "favorite_cert_names": ["컴퓨터활용능력 1급"], "acquired_cert_names": []},
            "전공: 경영학과\n학년: 4학년\n희망직무: 사무, 데이터 정리\n관심 자격증: 컴퓨터활용능력 1급\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "컴퓨터활용능력 1급"),
            [neg(neg_id, "빅데이터분석기사", "too_advanced_for_goal", "자격증명: 빅데이터분석기사\n관련직무: 빅데이터 분석\n설명: 심화 수준."), neg(neg_id+1, "정보처리기사", "it_specialized", "자격증명: 정보처리기사\n관련직무: 개발, IT\n설명: 개발 직무 중심.")]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "SQLD 다음에 뭐 따면 좋을까",
            {"major": "컴퓨터공학과", "grade_level": 4, "favorite_cert_names": ["SQLD"], "acquired_cert_names": ["SQLD"]},
            "전공: 컴퓨터공학과\n학년: 4학년\n희망직무: 데이터베이스, 개발\n관심 자격증: SQLD\n취득 자격증: SQLD\n목적: 다음 단계 자격증 추천",
            "followup_after_acquired", pos(pos_id, "정보처리기사"),
            [neg(neg_id, "컴퓨터활용능력 2급", "too_basic", CERT_TEXTS["컴퓨터활용능력 2급"]), neg(neg_id+1, "워드프로세서", "office_domain", CERT_TEXTS["워드프로세서"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "전산 쪽 일 하고 싶어",
            {"major": "산업공학과", "grade_level": 3, "favorite_cert_names": ["정보처리기사"], "acquired_cert_names": []},
            "전공: 산업공학과\n학년: 3학년\n희망직무: 전산\n관심 자격증: 정보처리기사\n취득 자격증: 없음\n목적: 취업 준비",
            "keyword", pos(pos_id, "정보처리기사"),
            [neg(neg_id, "품질경영기사", "industrial_but_not_it", CERT_TEXTS["품질경영기사"]), neg(neg_id+1, "전산회계 1급", "different_office_domain", CERT_TEXTS["전산회계 1급"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # p136–p155
    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "2학년인데 미리 뭐 할까",
            {"major": "소프트웨어학과", "grade_level": 2, "favorite_cert_names": [], "acquired_cert_names": []},
            "전공: 소프트웨어학과\n학년: 2학년\n희망직무: (쿼리 미포함)\n관심 자격증: 없음\n취득 자격증: 없음\n목적: 자격증 추천",
            "early_stage", pos(pos_id, "컴퓨터활용능력 1급"),
            [neg(neg_id, "빅데이터분석기사", "too_advanced_for_grade", "자격증명: 빅데이터분석기사\n관련직무: 빅데이터 분석\n설명: 심화."), neg(neg_id+1, "정보보안기사", "too_advanced_for_grade", CERT_TEXTS["정보보안기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "데이터랑 개발 둘 다 챙기고 싶어",
            {"major": "산업데이터공학과", "grade_level": 3, "favorite_cert_names": ["SQLD", "정보처리기사"], "acquired_cert_names": []},
            "전공: 산업데이터공학과\n학년: 3학년\n희망직무: 데이터, 개발\n관심 자격증: SQLD, 정보처리기사\n취득 자격증: 없음\n목적: 취업 준비",
            "natural", pos(pos_id, "SQLD"),
            [neg(neg_id, "워드프로세서", "office_only", CERT_TEXTS["워드프로세서"]), neg(neg_id+1, "정보보안기사", "it_but_wrong_focus", CERT_TEXTS["정보보안기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    for _ in range(5):
        entries.append(entry(
            f"p{pid}", "공기업 가산점용 자격증 뭐가 좋아",
            {"major": "행정학과", "grade_level": 4, "favorite_cert_names": ["컴퓨터활용능력 1급"], "acquired_cert_names": []},
            "전공: 행정학과\n학년: 4학년\n희망직무: 공기업, 사무\n관심 자격증: 컴퓨터활용능력 1급\n취득 자격증: 없음\n목적: 가산점, 취업 준비",
            "purpose_only", pos(pos_id, "컴퓨터활용능력 1급"),
            [neg(neg_id, "SQLD", "good_but_not_primary_goal", "자격증명: SQLD\n관련직무: 데이터베이스\n설명: 공기업 가산점 대표는 컴활."), neg(neg_id+1, "정보처리기사", "it_specialized", "자격증명: 정보처리기사\n관련직무: 개발, IT\n설명: IT 직무 중심.")]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    # Fill up to 155
    while pid <= 155:
        entries.append(entry(
            f"p{pid}", "데이터 분석 쪽 취업 준비하고 있어",
            {"major": "통계학과", "grade_level": 4, "favorite_cert_names": ["ADsP"], "acquired_cert_names": ["컴퓨터활용능력 1급"]},
            "전공: 통계학과\n학년: 4학년\n희망직무: 데이터 분석\n관심 자격증: ADsP\n취득 자격증: 컴퓨터활용능력 1급\n목적: 취업 준비",
            "natural", pos(pos_id, "ADsP"),
            [neg(neg_id, "정보보안기사", "same_it_but_wrong_job", CERT_TEXTS["정보보안기사"]), neg(neg_id+1, "전기기사", "different_domain", CERT_TEXTS["전기기사"])]
        ))
        pid += 1; pos_id += 1; neg_id += 2

    result = json.dumps(entries, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
    else:
        print(result)
    return len(entries)

if __name__ == "__main__":
    n = main()
    print(f"Generated {n} entries.", file=sys.stderr)
