# -*- coding: utf-8 -*-
"""
72+ contrastive rows 생성: 9개 영역 × 8 row, row당 hard negative 5종, profile 변형 4종.
출력: data/contrastive_profile_new.json (병합 가능한 JSON 배열)
"""
import json
from pathlib import Path

# 자격증 텍스트 (qual_name -> text)
CERT = {
    "ADsP": "자격증명: ADsP\n자격종류: 국가공인 민간자격\n관련직무: 데이터 분석, 데이터 기반 의사결정\n추천대상: 데이터 분석 직무 입문자\n설명: 데이터 이해, 분석 기획, 분석 결과 해석 역량을 평가한다.",
    "SQLD": "자격증명: SQLD\n자격종류: 국가공인 민간자격\n관련직무: 개발, 데이터베이스, 데이터 분석\n추천대상: DB 및 개발 직무 입문자\n설명: SQL 활용 및 데이터베이스 구축 역량을 평가한다.",
    "정보처리기사": "자격증명: 정보처리기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산, IT, 시스템 구축\n추천대상: IT·개발 취업 준비생\n설명: 소프트웨어 설계, 프로그래밍, 데이터베이스, 운영체제 등을 평가한다.",
    "빅데이터분석기사": "자격증명: 빅데이터분석기사\n자격종류: 국가기술자격\n관련직무: 데이터 분석, 데이터 엔지니어링\n추천대상: 데이터 직무 심화 준비생\n설명: 빅데이터 기획·수집·분석 역량을 평가한다.",
    "사회조사분석사": "자격증명: 사회조사분석사\n자격종류: 국가기술자격\n관련직무: 시장조사, 리서치, 데이터 수집\n추천대상: 시장조사·리서치 직무 준비생\n설명: 설문 설계, 데이터 수집·분석 역량을 평가한다.",
    "정보보안기사": "자격증명: 정보보안기사\n자격종류: 국가기술자격\n관련직무: 정보보안, 침해 대응\n추천대상: 보안 직무 준비생\n설명: 정보보안 관리 및 기술 역량을 평가한다.",
    "리눅스마스터 2급": "자격증명: 리눅스마스터 2급\n자격종류: 국가공인 민간자격\n관련직무: 시스템 운영, 서버 관리\n추천대상: 인프라 직무 준비생\n설명: 리눅스 운영체제 관리와 명령어 활용 능력을 평가한다.",
    "네트워크관리사 2급": "자격증명: 네트워크관리사 2급\n자격종류: 국가공인 민간자격\n관련직무: 네트워크 운영, 인프라 관리\n추천대상: 네트워크 직무 입문자\n설명: 네트워크 기초와 운영 역량을 평가한다.",
    "정보처리산업기사": "자격증명: 정보처리산업기사\n자격종류: 국가기술자격\n관련직무: 개발, 전산\n추천대상: 정보처리기사 준비 전 단계\n설명: 정보처리기사보다 하위 등급.",
    "전산회계 1급": "자격증명: 전산회계 1급\n자격종류: 국가공인 민간자격\n관련직무: 회계, 경리, 재무 사무\n추천대상: 회계 직무 준비생\n설명: 회계 처리와 전산 회계 프로그램 활용 능력을 평가한다.",
    "회계관리 1급": "자격증명: 회계관리 1급\n자격종류: 국가기술자격\n관련직무: 회계, 재무\n추천대상: 회계·재무 직무 준비생\n설명: 회계 관리 실무 역량을 평가한다.",
    "세무사": "자격증명: 세무사\n자격종류: 국가전문자격\n관련직무: 세무, 회계\n추천대상: 세무 전문가\n설명: 세무 업무 전문 역량을 평가한다.",
    "인사관리사": "자격증명: 인사관리사\n자격종류: 국가공인 민간자격\n관련직무: 인사, 채용, 교육\n추천대상: 인사 직무 준비생\n설명: 인사 관리 및 채용 역량을 평가한다.",
    "노동관리사": "자격증명: 노동관리사\n자격종류: 국가공인 민간자격\n관련직무: 노동법, 인사\n추천대상: 노동·인사 직무 준비생\n설명: 노동 관계 및 인사 관리 역량을 평가한다.",
    "경영지도사": "자격증명: 경영지도사\n자격종류: 국가공인 민간자격\n관련직무: 경영 컨설팅, 인사\n추천대상: 경영·인사 직무 준비생\n설명: 경영 진단 및 지도 역량을 평가한다.",
    "컴퓨터활용능력 1급": "자격증명: 컴퓨터활용능력 1급\n자격종류: 국가기술자격\n관련직무: 사무, OA, 데이터 정리, 문서 작성\n추천대상: 사무직, 행정직, 일반 취업 준비생\n설명: 스프레드시트와 데이터베이스 활용 능력을 평가한다.",
    "컴퓨터활용능력 2급": "자격증명: 컴퓨터활용능력 2급\n자격종류: 국가기술자격\n관련직무: 사무, OA\n추천대상: 사무 입문자\n설명: 입문 수준 사무 역량을 평가한다.",
    "워드프로세서": "자격증명: 워드프로세서\n자격종류: 국가기술자격\n관련직무: 문서 작성, 사무 보조\n추천대상: 문서 작성 입문자\n설명: 문서 작성 및 편집 능력을 평가한다.",
    "행정사": "자격증명: 행정사\n자격종류: 국가전문자격\n관련직무: 행정 대리, 민원\n추천대상: 행정 직무 준비생\n설명: 행정 업무 대리 역량을 평가한다.",
    "사회복지사": "자격증명: 사회복지사\n자격종류: 국가전문자격\n관련직무: 사회복지, 상담\n추천대상: 사회복지 직무 준비생\n설명: 사회복지 실무 역량을 평가한다.",
    "조리기능사": "자격증명: 조리기능사\n자격종류: 국가기술자격\n관련직무: 조리, 음식 제조\n추천대상: 조리 직무 준비생\n설명: 조리 기초 역량을 평가한다.",
    "양식조리기능사": "자격증명: 양식조리기능사\n자격종류: 국가기술자격\n관련직무: 양식 조리\n추천대상: 양식 조리 직무 준비생\n설명: 양식 조리 역량을 평가한다.",
    "중식조리기능사": "자격증명: 중식조리기능사\n자격종류: 국가기술자격\n관련직무: 중식 조리\n추천대상: 중식 조리 직무 준비생\n설명: 중식 조리 역량을 평가한다.",
    "일식조리기능사": "자격증명: 일식조리기능사\n자격종류: 국가기술자격\n관련직무: 일식 조리\n추천대상: 일식 조리 직무 준비생\n설명: 일식 조리 역량을 평가한다.",
    "부동산거래관리사": "자격증명: 부동산거래관리사\n자격종류: 국가전문자격\n관련직무: 부동산 거래, 중개 보조\n추천대상: 부동산 직무 준비생\n설명: 부동산 거래 관리 역량을 평가한다.",
    "공인중개사": "자격증명: 공인중개사\n자격종류: 국가전문자격\n관련직무: 부동산 중개, 컨설팅\n추천대상: 부동산 중개 직무 준비생\n설명: 부동산 중개 업무 역량을 평가한다.",
    "간호사": "자격증명: 간호사\n자격종류: 국가면허\n관련직무: 의료, 간호\n추천대상: 간호 직무 준비생\n설명: 의료·간호 실무 역량을 평가한다.",
    "요양보호사": "자격증명: 요양보호사\n자격종류: 국가자격\n관련직무: 요양, 돌봄\n추천대상: 요양 직무 준비생\n설명: 요양 보호 실무 역량을 평가한다.",
    "건강관리사": "자격증명: 건강관리사\n자격종류: 국가공인 민간자격\n관련직무: 건강 관리, 예방\n추천대상: 보건·건강 직무 준비생\n설명: 건강 관리 및 예방 교육 역량을 평가한다.",
    "품질경영기사": "자격증명: 품질경영기사\n자격종류: 국가기술자격\n관련직무: 품질 관리, 생산 관리\n추천대상: 품질·생산 직무 준비생\n설명: 품질·생산 관리 직무 역량을 평가한다.",
    "전기기사": "자격증명: 전기기사\n자격종류: 국가기술자격\n관련직무: 전기 설계, 전력 시스템\n추천대상: 전기 직무 준비생\n설명: 전기 이론 및 설계 역량을 평가한다.",
}


def neg(qual_name: str, negative_type: str) -> dict:
    return {"qual_name": qual_name, "negative_type": negative_type, "text": CERT.get(qual_name, f"자격증명: {qual_name}\n자격종류: -\n관련직무: -\n추천대상: -\n설명: -")}


def pos(qual_name: str) -> dict:
    return {"qual_name": qual_name, "text": CERT.get(qual_name, f"자격증명: {qual_name}\n자격종류: -\n관련직무: -\n추천대상: -\n설명: -")}


def rew(major: str, grade: int, hope: str, fav: list, acq: list, purpose: str) -> str:
    fav_s = ", ".join(fav) if fav else "없음"
    acq_s = ", ".join(acq) if acq else "없음"
    return f"전공: {major}\n학년: {grade}학년\n희망직무: {hope}\n관심 자격증: {fav_s}\n취득 자격증: {acq_s}\n목적: {purpose}"


def row(qid: str, raw: str, profile: dict, rq: str, qtype: str, single_pos=None, multi_pos=None, negs: list = None):
    out = {"query_id": qid, "raw_query": raw, "profile": profile, "rewritten_query": rq, "query_type": qtype, "negatives": negs or []}
    if single_pos is not None:
        out["positive"] = single_pos
    else:
        out["positives"] = multi_pos or []
    return out


def main():
    rows = []
    idx = 1

    # ---- 데이터 분석 (8) ----
    raw_a = "데이터 쪽 취업하고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("통계학과", 4, ["ADsP"], [], "취업 준비"),
        ("경영학과", 3, ["SQLD"], ["컴퓨터활용능력 2급"], "취업 준비"),
        ("산업데이터공학", 2, [], [], "진로 탐색"),
        ("컴퓨터공학과", 4, ["ADsP", "SQLD"], ["ADsP"], "취업 준비"),
    ]:
        rq = rew(major, grade, "데이터 분석", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("정보보안기사", "same_domain_different_role"),
            neg("품질경영기사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("SQLD", "bookmark_confusion") if "ADsP" in (fav or []) else neg("정보처리기사", "bookmark_confusion"),
            neg("사회조사분석사", "retrieved_topk_confusion"),
        ]
        if acq and "컴퓨터활용능력 2급" in acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_a, profile, rq, "profile_personalized", multi_pos=[pos("ADsP"), pos("SQLD"), pos("빅데이터분석기사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("경영정보학과", 4, ["빅데이터분석기사"], [], "실무 역량 강화"),
        ("사회학과", 2, [], [], "자격증 추천"),
        ("산업공학과", 3, ["SQLD"], ["컴퓨터활용능력 1급"], "취업 준비"),
        ("경제학과", 4, [], [], "이직 준비"),
    ]:
        rq = rew(major, grade, "데이터 분석", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("정보보안기사", "same_domain_different_role"),
            neg("품질경영기사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("정보처리기사", "bookmark_confusion") if not fav else neg("세무사", "bookmark_confusion"),
            neg("사회조사분석사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_a, profile, rq, "profile_personalized", multi_pos=[pos("ADsP"), pos("SQLD")], negs=negs))
        idx += 1

    # ---- 개발 (8) ----
    raw_b = "개발 쪽 준비하고 있어"
    for (major, grade, fav, acq, purpose) in [
        ("소프트웨어학과", 3, ["정보처리기사"], [], "취업 준비"),
        ("컴퓨터공학과", 2, [], [], "진로 탐색"),
        ("산업데이터공학", 4, ["SQLD"], ["ADsP"], "취업 준비"),
        ("경영정보학과", 3, ["정보처리기사"], ["컴퓨터활용능력 1급"], "취업 준비"),
    ]:
        rq = rew(major, grade, "개발", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("정보보안기사", "same_domain_different_role"),
            neg("리눅스마스터 2급", "same_level_but_wrong_track"),
            neg("정보처리산업기사", "lower_than_acquired") if "정보처리기사" in (fav or []) else (neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired")),
            neg("ADsP", "bookmark_confusion") if "SQLD" in (fav or []) else neg("전산회계 1급", "bookmark_confusion"),
            neg("품질경영기사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_b, profile, rq, "profile_personalized", multi_pos=[pos("정보처리기사"), pos("SQLD")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("전자공학과", 4, [], [], "취업 준비"),
        ("산업공학과", 2, ["SQLD"], [], "자격증 추천"),
        ("통계학과", 3, ["정보처리기사"], [], "실무 역량 강화"),
        ("경영학과", 4, [], ["컴퓨터활용능력 1급"], "이직 준비"),
    ]:
        rq = rew(major, grade, "개발", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("정보보안기사", "same_domain_different_role"),
            neg("네트워크관리사 2급", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("빅데이터분석기사", "bookmark_confusion") if not fav else neg("세무사", "bookmark_confusion"),
            neg("전기기사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_b, profile, rq, "profile_personalized", multi_pos=[pos("정보처리기사"), pos("SQLD"), pos("ADsP")], negs=negs))
        idx += 1

    # ---- 보안 (8) ----
    raw_c = "보안 쪽 일 하고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("정보보안학과", 4, ["정보보안기사"], [], "취업 준비"),
        ("컴퓨터공학과", 3, [], [], "진로 탐색"),
        ("소프트웨어학과", 2, ["리눅스마스터 2급"], [], "자격증 추천"),
        ("산업데이터공학", 4, ["정보보안기사"], ["정보처리기사"], "취업 준비"),
    ]:
        rq = rew(major, grade, "보안", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("리눅스마스터 2급", "same_domain_different_role"),
            neg("네트워크관리사 2급", "same_level_but_wrong_track"),
            neg("정보처리산업기사", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("정보처리기사", "bookmark_confusion") if acq else neg("ADsP", "bookmark_confusion"),
            neg("SQLD", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("정보처리산업기사", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_c, profile, rq, "profile_personalized", single_pos=pos("정보보안기사"), negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("전자공학과", 3, ["네트워크관리사 2급"], [], "취업 준비"),
        ("경영학과", 4, [], [], "이직 준비"),
        ("정보통신공학과", 2, ["정보보안기사"], [], "실무 역량 강화"),
        ("수학과", 3, [], ["컴퓨터활용능력 1급"], "자격증 추천"),
    ]:
        rq = rew(major, grade, "보안", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("네트워크관리사 2급", "same_domain_different_role"),
            neg("정보처리기사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("리눅스마스터 2급", "bookmark_confusion") if fav else neg("품질경영기사", "bookmark_confusion"),
            neg("ADsP", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_c, profile, rq, "profile_personalized", multi_pos=[pos("정보보안기사"), pos("리눅스마스터 2급")], negs=negs))
        idx += 1

    # ---- 회계 (8) ----
    raw_d = "회계 쪽 취업 준비할게"
    for (major, grade, fav, acq, purpose) in [
        ("회계학과", 4, ["전산회계 1급"], [], "취업 준비"),
        ("경영학과", 3, [], ["컴퓨터활용능력 1급"], "취업 준비"),
        ("경제학과", 2, ["회계관리 1급"], [], "진로 탐색"),
        ("무역학과", 4, ["전산회계 1급"], ["전산회계 1급"], "다음 단계 자격증 추천"),
    ]:
        rq = rew(major, grade, "회계", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("세무사", "same_domain_different_role"),
            neg("인사관리사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("회계관리 1급", "bookmark_confusion") if "전산회계 1급" in (fav or []) else neg("정보처리기사", "bookmark_confusion"),
            neg("정보처리기사", "retrieved_topk_confusion"),
        ]
        if acq and "전산회계 1급" in acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_d, profile, rq, "profile_personalized", multi_pos=[pos("전산회계 1급"), pos("회계관리 1급")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("부동산학과", 3, [], [], "자격증 추천"),
        ("국제통상학과", 4, ["전산회계 1급"], [], "실무 역량 강화"),
        ("세무학과", 2, ["세무사"], [], "취업 준비"),
        ("금융학과", 4, [], ["전산회계 1급"], "이직 준비"),
    ]:
        rq = rew(major, grade, "회계", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("인사관리사", "same_domain_different_role"),
            neg("부동산거래관리사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("세무사", "bookmark_confusion") if "세무사" in (fav or []) else neg("노동관리사", "bookmark_confusion"),
            neg("SQLD", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_d, profile, rq, "profile_personalized" if idx % 2 else "career_goal", single_pos=pos("전산회계 1급"), negs=negs))
        idx += 1

    # ---- 인사 (8) ----
    raw_e = "인사 직무로 가고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("경영학과", 4, ["인사관리사"], [], "취업 준비"),
        ("심리학과", 3, [], [], "진로 탐색"),
        ("사회학과", 2, ["노동관리사"], [], "자격증 추천"),
        ("행정학과", 4, ["인사관리사"], ["컴퓨터활용능력 1급"], "취업 준비"),
    ]:
        rq = rew(major, grade, "인사", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("노동관리사", "same_domain_different_role"),
            neg("경영지도사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("경영지도사", "bookmark_confusion") if fav else neg("전산회계 1급", "bookmark_confusion"),
            neg("전산회계 1급", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_e, profile, rq, "profile_personalized", multi_pos=[pos("인사관리사"), pos("노동관리사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("교육학과", 3, [], [], "실무 역량 강화"),
        ("경제학과", 4, ["인사관리사"], [], "이직 준비"),
        ("법학과", 2, ["노동관리사"], [], "취업 준비"),
        ("국어국문학과", 4, [], ["워드프로세서"], "자격증 추천"),
    ]:
        rq = rew(major, grade, "인사", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("경영지도사", "same_domain_different_role"),
            neg("전산회계 1급", "same_level_but_wrong_track"),
            neg("워드프로세서", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("사회복지사", "bookmark_confusion") if not fav else neg("행정사", "bookmark_confusion"),
            neg("회계관리 1급", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("워드프로세서", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_e, profile, rq, "profile_personalized", single_pos=pos("인사관리사"), negs=negs))
        idx += 1

    # ---- 행정 (8) ----
    raw_f = "행정·사무 쪽 준비하고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("행정학과", 4, ["컴퓨터활용능력 1급"], [], "취업 준비"),
        ("정치외교학과", 3, [], [], "진로 탐색"),
        ("법학과", 2, ["행정사"], [], "자격증 추천"),
        ("사회학과", 4, ["컴퓨터활용능력 1급"], ["컴퓨터활용능력 2급"], "취업 준비"),
    ]:
        rq = rew(major, grade, "행정, 사무", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("전산회계 1급", "same_domain_different_role"),
            neg("사회복지사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("워드프로세서", "bookmark_confusion") if "컴퓨터활용능력" in str(fav) else neg("인사관리사", "bookmark_confusion"),
            neg("인사관리사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_f, profile, rq, "profile_personalized", multi_pos=[pos("컴퓨터활용능력 1급"), pos("행정사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("국어국문학과", 3, [], [], "실무 역량 강화"),
        ("역사학과", 4, ["행정사"], [], "이직 준비"),
        ("경영학과", 2, ["컴퓨터활용능력 1급"], [], "취업 준비"),
        ("공공행정학과", 4, [], ["워드프로세서"], "자격증 추천"),
    ]:
        rq = rew(major, grade, "행정, 사무", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("인사관리사", "same_domain_different_role"),
            neg("회계관리 1급", "same_level_but_wrong_track"),
            neg("워드프로세서", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("사회복지사", "bookmark_confusion") if "행정사" in (fav or []) else neg("노동관리사", "bookmark_confusion"),
            neg("노동관리사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("워드프로세서", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_f, profile, rq, "profile_personalized", single_pos=pos("컴퓨터활용능력 1급"), negs=negs))
        idx += 1

    # ---- 조리 (8) ----
    raw_g = "조리 쪽 일 해보고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("조리학과", 4, ["조리기능사"], [], "취업 준비"),
        ("호텔경영학과", 3, [], [], "진로 탐색"),
        ("외식조리학과", 2, ["양식조리기능사"], [], "자격증 추천"),
        ("식품영양학과", 4, ["조리기능사"], ["조리기능사"], "다음 단계 추천"),
    ]:
        rq = rew(major, grade, "조리", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("양식조리기능사", "same_domain_different_role"),
            neg("중식조리기능사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("중식조리기능사", "bookmark_confusion") if "양식" in str(fav) else neg("일식조리기능사", "bookmark_confusion"),
            neg("전산회계 1급", "retrieved_topk_confusion"),
        ]
        rows.append(row(f"tmp{idx:03d}", raw_g, profile, rq, "profile_personalized", multi_pos=[pos("조리기능사"), pos("양식조리기능사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("글로벌조리학과", 3, [], [], "실무 역량 강화"),
        ("외식산업학과", 4, ["중식조리기능사"], [], "이직 준비"),
        ("호텔관광학과", 2, ["조리기능사"], [], "취업 준비"),
        ("경영학과", 4, [], [], "자격증 추천"),
    ]:
        rq = rew(major, grade, "조리", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("일식조리기능사", "same_domain_different_role"),
            neg("컴퓨터활용능력 1급", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired"),
            neg("양식조리기능사", "bookmark_confusion") if fav else neg("부동산거래관리사", "bookmark_confusion"),
            neg("인사관리사", "retrieved_topk_confusion"),
        ]
        rows.append(row(f"tmp{idx:03d}", raw_g, profile, rq, "profile_personalized", single_pos=pos("조리기능사"), negs=negs))
        idx += 1

    # ---- 부동산 (8) ----
    raw_h = "부동산 쪽으로 취업하고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("부동산학과", 4, ["부동산거래관리사"], [], "취업 준비"),
        ("경영학과", 3, [], [], "진로 탐색"),
        ("법학과", 2, ["공인중개사"], [], "자격증 추천"),
        ("경제학과", 4, ["부동산거래관리사"], ["컴퓨터활용능력 1급"], "취업 준비"),
    ]:
        rq = rew(major, grade, "부동산", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("공인중개사", "same_domain_different_role"),
            neg("전산회계 1급", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("공인중개사", "bookmark_confusion") if "부동산거래관리사" in (fav or []) else neg("회계관리 1급", "bookmark_confusion"),
            neg("회계관리 1급", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_h, profile, rq, "profile_personalized", multi_pos=[pos("부동산거래관리사"), pos("공인중개사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("토목공학과", 3, [], [], "실무 역량 강화"),
        ("행정학과", 4, ["공인중개사"], [], "이직 준비"),
        ("국어국문학과", 2, ["부동산거래관리사"], [], "취업 준비"),
        ("무역학과", 4, [], [], "자격증 추천"),
    ]:
        rq = rew(major, grade, "부동산", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("회계관리 1급", "same_domain_different_role"),
            neg("인사관리사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("부동산거래관리사", "bookmark_confusion") if "공인중개사" in (fav or []) else neg("세무사", "bookmark_confusion"),
            neg("세무사", "retrieved_topk_confusion"),
        ]
        rows.append(row(f"tmp{idx:03d}", raw_h, profile, rq, "profile_personalized", single_pos=pos("부동산거래관리사"), negs=negs))
        idx += 1

    # ---- 보건 (8) ----
    raw_i = "보건·의료 쪽 일 하고 싶어"
    for (major, grade, fav, acq, purpose) in [
        ("간호학과", 4, ["간호사"], [], "취업 준비"),
        ("보건행정학과", 3, [], [], "진로 탐색"),
        ("물리치료학과", 2, ["요양보호사"], [], "자격증 추천"),
        ("식품영양학과", 4, ["건강관리사"], ["컴퓨터활용능력 2급"], "취업 준비"),
    ]:
        rq = rew(major, grade, "보건", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("요양보호사", "same_domain_different_role"),
            neg("건강관리사", "same_level_but_wrong_track"),
            neg("컴퓨터활용능력 2급", "lower_than_acquired") if acq else neg("워드프로세서", "lower_than_acquired"),
            neg("건강관리사", "bookmark_confusion") if "간호사" in (fav or []) else neg("조리기능사", "bookmark_confusion"),
            neg("조리기능사", "retrieved_topk_confusion"),
        ]
        if acq:
            negs[2] = neg("컴퓨터활용능력 2급", "lower_than_acquired")
        rows.append(row(f"tmp{idx:03d}", raw_i, profile, rq, "profile_personalized", multi_pos=[pos("간호사"), pos("요양보호사")], negs=negs))
        idx += 1
    for (major, grade, fav, acq, purpose) in [
        ("의료공학과", 3, [], [], "실무 역량 강화"),
        ("사회복지학과", 4, ["요양보호사"], [], "이직 준비"),
        ("스포츠과학과", 2, ["건강관리사"], [], "취업 준비"),
        ("경영학과", 4, [], [], "자격증 추천"),
    ]:
        rq = rew(major, grade, "보건", fav, acq, purpose)
        profile = {"major": major, "grade_level": grade, "favorite_cert_names": fav, "acquired_cert_names": acq}
        negs = [
            neg("건강관리사", "same_domain_different_role"),
            neg("인사관리사", "same_level_but_wrong_track"),
            neg("워드프로세서", "lower_than_acquired"),
            neg("요양보호사", "bookmark_confusion") if fav else neg("전산회계 1급", "bookmark_confusion"),
            neg("전산회계 1급", "retrieved_topk_confusion"),
        ]
        rows.append(row(f"tmp{idx:03d}", raw_i, profile, rq, "profile_personalized", single_pos=pos("요양보호사"), negs=negs))
        idx += 1

    # Dedup: (raw_query, profile_key, positive_set)
    def row_key(r):
        raw = " ".join((r.get("raw_query") or "").split())
        p = r.get("profile") or {}
        prof = (p.get("major"), p.get("grade_level"), tuple(sorted(p.get("favorite_cert_names") or [])), tuple(sorted(p.get("acquired_cert_names") or [])))
        pos_set = set()
        if "positives" in r and r["positives"]:
            for x in r["positives"]:
                pos_set.add((x.get("qual_name") or "").strip())
        elif r.get("positive"):
            pos_set.add((r["positive"].get("qual_name") or "").strip())
        return (raw, prof, frozenset(pos_set))

    seen = {}
    deduped = []
    for r in rows:
        k = row_key(r)
        if k in seen:
            if len(r.get("negatives") or []) > len(seen[k].get("negatives") or []):
                deduped.remove(seen[k])
                deduped.append(r)
                seen[k] = r
        else:
            seen[k] = r
            deduped.append(r)

    # Re-assign query_id
    for i, r in enumerate(deduped):
        r["query_id"] = f"tmp{i+1:03d}"

    out_path = Path(__file__).resolve().parent.parent / "data" / "contrastive_profile_new.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(len(deduped))
    return deduped


if __name__ == "__main__":
    main()
