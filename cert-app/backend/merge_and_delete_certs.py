"""
자격증 병합 및 삭제 스크립트
- 변경된 자격증: 이전 자격증의 직무/전공 매핑을 새 자격증으로 이동
- 삭제된 자격증: 연결된 직무/전공 매핑 삭제 후 자격증 삭제
"""

from app.database import SessionLocal
from app.models import Qualification, QualificationStats, UserFavorite, QualificationJobMap, MajorQualificationMap
from sqlalchemy import text

db = SessionLocal()

def find_qual_by_name(name):
    """자격증 이름으로 검색"""
    return db.query(Qualification).filter(Qualification.qual_name == name).first()

def merge_qualification(from_name, to_name, log_fn=print):
    """
    자격증 병합: from_name의 모든 관계를 to_name으로 이동 후 삭제
    """
    try:
        source = find_qual_by_name(from_name)
        target = find_qual_by_name(to_name)
        
        if not source:
            log_fn(f"⚠️  소스 자격증 없음: {from_name}")
            return False
            
        if not target:
            log_fn(f"⚠️  타겟 자격증 없음: {to_name}")
            return False

        log_fn(f"🔄 병합 중: {from_name} ({source.qual_id}) → {to_name} ({target.qual_id})")

        # 1. 즐겨찾기 이동
        favs = db.query(UserFavorite).filter(UserFavorite.qual_id == source.qual_id).all()
        for f in favs:
            exists = db.query(UserFavorite).filter(
                UserFavorite.user_id == f.user_id,
                UserFavorite.qual_id == target.qual_id
            ).first()
            if not exists:
                f.qual_id = target.qual_id
            else:
                db.delete(f)
        
        # 2. 직무 매핑 이동
        job_maps = db.query(QualificationJobMap).filter(QualificationJobMap.qual_id == source.qual_id).all()
        moved_jobs = 0
        for j in job_maps:
            exists = db.query(QualificationJobMap).filter(
                QualificationJobMap.job_id == j.job_id,
                QualificationJobMap.qual_id == target.qual_id
            ).first()
            if not exists:
                j.qual_id = target.qual_id
                moved_jobs += 1
            else:
                db.delete(j)
                
        # 3. 전공 매핑 이동
        major_maps = db.query(MajorQualificationMap).filter(MajorQualificationMap.qual_id == source.qual_id).all()
        moved_majors = 0
        for m in major_maps:
            exists = db.query(MajorQualificationMap).filter(
                MajorQualificationMap.major == m.major,
                MajorQualificationMap.qual_id == target.qual_id
            ).first()
            if not exists:
                m.qual_id = target.qual_id
                moved_majors += 1
            else:
                db.delete(m)
                
        # 4. 통계 삭제 (타겟에 이미 있다고 가정)
        db.query(QualificationStats).filter(QualificationStats.qual_id == source.qual_id).delete()
        
        # 5. 소스 자격증 삭제
        db.delete(source)
        
        db.commit()
        log_fn(f"✅ 완료: 직무 {moved_jobs}개, 전공 {moved_majors}개 이동")
        return True
        
    except Exception as e:
        log_fn(f"❌ 에러: {from_name} → {to_name}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

def delete_qualification(name, log_fn=print):
    """
    자격증 삭제: 모든 관계 삭제 후 자격증 삭제
    """
    try:
        qual = find_qual_by_name(name)
        
        if not qual:
            log_fn(f"⚠️  자격증 없음: {name}")
            return False

        log_fn(f"🗑️  삭제 중: {name} ({qual.qual_id})")

        # 1. 즐겨찾기 삭제
        db.query(UserFavorite).filter(UserFavorite.qual_id == qual.qual_id).delete()
        
        # 2. 직무 매핑 삭제
        job_count = db.query(QualificationJobMap).filter(QualificationJobMap.qual_id == qual.qual_id).count()
        db.query(QualificationJobMap).filter(QualificationJobMap.qual_id == qual.qual_id).delete()
        
        # 3. 전공 매핑 삭제
        major_count = db.query(MajorQualificationMap).filter(MajorQualificationMap.qual_id == qual.qual_id).count()
        db.query(MajorQualificationMap).filter(MajorQualificationMap.qual_id == qual.qual_id).delete()
        
        # 4. 통계 삭제
        db.query(QualificationStats).filter(QualificationStats.qual_id == qual.qual_id).delete()
        
        # 5. 자격증 삭제
        db.delete(qual)
        
        db.commit()
        log_fn(f"✅ 완료: 직무 {job_count}개, 전공 {major_count}개 삭제됨")
        return True
        
    except Exception as e:
        log_fn(f"❌ 에러: {name}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

if __name__ == "__main__":
    import sys
    
    # 파일로 출력 저장
    log_file = open("merge_log.txt", "w", encoding="utf-8")
    
    def log_print(msg):
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()
    
    log_print("=" * 80)
    log_print("자격증 병합 및 삭제 작업 시작")
    log_print("=" * 80)
    
    # ========== 병합 작업 ==========
    log_print("\n📋 [병합 작업]")
    
    merges = [
        ("수상원동기자격증 1급", "동력수상레저기구조종면허"),
        ("수상원동기자격증 2급", "동력수상레저기구조종면허"),
        ("언어치료사", "언어재활사 1급"),  # 1급과 2급 중 1급으로 통합
        ("GTQi(그래픽기술자격일러스트)", "GTQi(그래픽기술자격 일러스트) 1급"),  # 1급으로 통합
        ("신재생에너지발전설비기사(태양광)", "신재생에너지발전설비(태양광)기사"),
        ("가정복지사", "건강가정사"),
        
        # 무대예술전문인 - 음향
        ("무대예술전문인자격(무대음향) 3급", "무대예술전문인(무대음향) 3급"),
        ("무대예술전문인3급(무대음향)", "무대예술전문인(무대음향) 3급"),
        ("무대예술전문인자격(무대음향) 2급", "무대예술전문인(무대음향) 2급"),
        ("무대예술전문인2급(무대음향)", "무대예술전문인(무대음향) 2급"),
        ("무대예술전문인자격(무대음향) 1급", "무대예술전문인(무대음향) 1급"),
        ("무대예술전문인1급(무대음향)", "무대예술전문인(무대음향) 1급"),
        
        # 무대예술전문인 - 조명
        ("무대예술전문인자격(무대조명) 3급", "무대예술전문인(무대조명) 3급"),
        ("무대예술전문인3급(무대조명)", "무대예술전문인(무대조명) 3급"),
        ("무대예술전문인자격(무대조명) 2급", "무대예술전문인(무대조명) 2급"),
        ("무대예술전문인2급(무대조명)", "무대예술전문인(무대조명) 2급"),
        ("무대예술전문인자격(무대조명) 1급", "무대예술전문인(무대조명) 1급"),
        ("무대예술전문인1급(무대조명)", "무대예술전문인(무대조명) 1급"),
        
        # 무대예술전문인 - 기계
        ("무대예술전문인자격(무대기계) 3급", "무대예술전문인(무대기계) 3급"),
        ("무대예술전문인3급(무대기계)", "무대예술전문인(무대기계) 3급"),
        ("무대예술전문인자격(무대기계) 2급", "무대예술전문인(무대기계) 2급"),
        ("무대예술전문인2급(무대기계)", "무대예술전문인(무대기계) 2급"),
        ("무대예술전문인자격(무대기계) 1급", "무대예술전문인(무대기계) 1급"),
        ("무대예술전문인1급(무대기계)", "무대예술전문인(무대기계) 1급"),
        
        # 번역능력인정시험
        ("번역능력인정시험(TCT)3급", "번역능력인정시험(TCT) 3급"),
        ("번역능력인정시험(TCT)2급", "번역능력인정시험(TCT) 2급"),
        ("번역능력인정시험(TCT)1급", "번역능력인정시험(TCT) 1급"),
        
        # 기타
        ("식품기사", "식품안전기사"),
        ("문화재수리기술자(조경)", "국가유산수리기술자(조경)"),
        ("문화재수리기능자(조경공)", "국가유산수리기능자(조경공)"),
        ("생물공학기사", "바이오화학제품제조기사"),
        ("인쇄기사", "인쇄설계기사"),
        ("웹디자인기능사", "웹디자인개발기능사"),
        ("인쇄산업기사", "디지털인쇄산업기사"),
    ]
    
    success_count = 0
    for from_name, to_name in merges:
        if merge_qualification(from_name, to_name, log_print):
            success_count += 1
        log_print("")
    
    log_print(f"✅ 병합 완료: {success_count}/{len(merges)}")
    
    # ========== 삭제 작업 ==========
    log_print("\n📋 [삭제 작업]")
    
    deletes = [
        "문화재수리기능자",
        "멀티미디어콘텐츠제작전문가기사",
        "멀티미디어콘텐츠제작",
        "무대예술전문인",  # 세부 분야로 분리되었으므로 삭제
    ]
    
    delete_count = 0
    for name in deletes:
        if delete_qualification(name, log_print):
            delete_count += 1
        log_print("")
    
    log_print(f"✅ 삭제 완료: {delete_count}/{len(deletes)}")
    
    log_print("\n" + "=" * 80)
    log_print("작업 완료!")
    log_print("=" * 80)
    
    log_file.close()
    db.close()
