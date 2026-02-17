
from app.database import SessionLocal
from app.models import Qualification, QualificationStats, UserFavorite, QualificationJobMap, MajorQualificationMap
from sqlalchemy import text

db = SessionLocal()

def merge_qualification(from_id, to_id, db):
    """
    Merges data from source qualification (from_id) to target (to_id).
    Then deletes source.
    """
    try:
        source = db.query(Qualification).filter(Qualification.qual_id == from_id).first()
        target = db.query(Qualification).filter(Qualification.qual_id == to_id).first()
        
        if not source or not target:
            print(f"Skipping merge: {from_id} -> {to_id} (Source or Target not found)")
            return

        print(f"Merging {source.qual_name} ({from_id}) -> {target.qual_name} ({to_id})")

        # 1. Update Favorites
        favs = db.query(UserFavorite).filter(UserFavorite.qual_id == from_id).all()
        for f in favs:
            # Check if duplicate exists
            exists = db.query(UserFavorite).filter(
                UserFavorite.user_id == f.user_id,
                UserFavorite.qual_id == to_id
            ).first()
            if not exists:
                f.qual_id = to_id
            else:
                db.delete(f) # Remove duplicate source fav
        
        # 2. Update Job Maps
        jobs = db.query(QualificationJobMap).filter(QualificationJobMap.qual_id == from_id).all()
        for j in jobs:
            exists = db.query(QualificationJobMap).filter(
                QualificationJobMap.job_id == j.job_id,
                QualificationJobMap.qual_id == to_id
            ).first()
            if not exists:
                j.qual_id = to_id
            else:
                db.delete(j)
                
        # 3. Update Major Maps
        majors = db.query(MajorQualificationMap).filter(MajorQualificationMap.qual_id == from_id).all()
        for m in majors:
            exists = db.query(MajorQualificationMap).filter(
                MajorQualificationMap.major_id == m.major_id,
                MajorQualificationMap.qual_id == to_id
            ).first()
            if not exists:
                m.qual_id = to_id
            else:
                db.delete(m)
                
        # 4. Delete Source Stats (Assuming Target has better/newer stats, or duplicate)
        # Usually we just delete source stats to avoid conflict.
        db.query(QualificationStats).filter(QualificationStats.qual_id == from_id).delete()
        
        # 5. Delete Source Qualification
        db.delete(source)
        
        db.commit()
        print("Merge complete.")
        
    except Exception as e:
        print(f"Error merging {from_id} -> {to_id}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

def create_missing_certs(db):
    """
    Creates missing Cultural Heritage certifications if they don't exist.
    """
    try:
        # Check '문화재수리기술자' (Generic)
        name = "문화재수리기술자"
        exists = db.query(Qualification).filter(Qualification.qual_name == name).first()
        if not exists:
            print(f"Creating missing {name}...")
            new_qual = Qualification(
                qual_name=name,
                qual_type="국가전문자격", 
                managing_body="문화재청", # Cultural Heritage Administration
                is_active=True
            )
            db.add(new_qual)
            db.commit()
            print(f"Created {name}")
        else:
            print(f"{name} already exists.")

        # Check '문화재수리기능자' (Generic) - ID 1170 exists, so check logic not needed usually.
        # But maybe implied 'other' varieties?
        # User said "Deleted ones... should be created".
        # If 1170 exists, maybe it was inactive?
        # My check_output.txt showed it as Active.
        
    except Exception as e:
        print(f"Error creating certs: {e}")
        db.rollback()

if __name__ == "__main__":
    # Merge '산업위생기사' (1289) -> '산업위생관리기사' (335)
    # IDs from check_output.txt
    merge_qualification(1289, 335, db)
    
    # Create missing Cultural Heritage certs
    create_missing_certs(db)
    
    db.close()
