
import sys
import os
import math

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Qualification, QualificationStats
from sqlalchemy import text

def calculate_difficulty(qual, stat):
    """
    Calculate difficulty score (1-10) based on pass rate and qualification metadata.
    
    Logic:
    1. Base Difficulty = (100 - Pass Rate) / 10. (0 to 10)
    2. Multipliers:
       - National Professional (전문): * 1.5 (These are hard!)
       - National Technical (기술): * 1.0
       - National Private (민간): * 0.8
    3. Grade/Level Multiplier:
       - Professional Engineer (기술사): * 1.3
       - Master Craftsman (기능장): * 1.2
       - Engineer (기사): * 1.1
       - Industrial Engineer (산업기사): * 1.0
       - Craftsman (기능사): * 0.8
    """
    
    if stat.pass_rate is None:
        if stat.candidate_cnt and stat.candidate_cnt > 0 and stat.pass_cnt is not None:
             pass_rate = (stat.pass_cnt / stat.candidate_cnt) * 100
        else:
             return None
    else:
        pass_rate = stat.pass_rate
        
    # 1. Base Score
    base_score = (100 - pass_rate) / 10
    
    # 2. Type Multiplier
    type_mult = 1.0
    if qual.qual_type == "국가전문자격":
        type_mult = 1.5
    elif qual.qual_type == "국가민간자격":
        type_mult = 0.8
        
    # 3. Grade Multiplier
    grade_mult = 1.0
    name = qual.qual_name
    if "기술사" in name:
        grade_mult = 1.3
    elif "기능장" in name:
        grade_mult = 1.2
    elif "기사" in name and "산업기사" not in name:
        grade_mult = 1.1
    elif "산업기사" in name:
        grade_mult = 1.0
    elif "기능사" in name:
        grade_mult = 0.8
        
    # Calculate
    final_score = base_score * type_mult * grade_mult
    
    # Cap at 10.0 and Min 1.0
    final_score = min(9.9, max(1.0, final_score))
    
    return round(final_score, 2)

def main():
    db = SessionLocal()
    try:
        quals = db.query(Qualification).all()
        print(f"Processing {len(quals)} qualifications...")
        
        count = 0
        for q in quals:
            stats = db.query(QualificationStats).filter(
                QualificationStats.qual_id == q.qual_id
            ).all()
            
            for s in stats:
                new_diff = calculate_difficulty(q, s)
                if new_diff is not None:
                    s.difficulty_score = new_diff
                    count += 1
            
        db.commit()
        print(f"Updated difficulty for {count} stats records.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
