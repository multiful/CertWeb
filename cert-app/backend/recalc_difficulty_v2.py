
import sys
import os
import math
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Qualification, QualificationStats

def get_global_avg_pass_rate(db):
    # Calculate global average pass rate, excluding small samples
    res = db.execute(text("""
        SELECT AVG(pass_rate) 
        FROM qualification_stats 
        WHERE pass_rate IS NOT NULL AND candidate_cnt > 50
    """)).scalar()
    return float(res) if res else 40.0

def calculate_difficulty(qual, stat, global_avg_rate):
    """
    Calculate difficulty score (1-10) using Bayesian Smoothing and Multipliers.
    """
    
    # 1. Get Raw Data
    if stat.candidate_cnt is None:
        candidate_cnt = 0
    else:
        candidate_cnt = stat.candidate_cnt
        
    if stat.pass_cnt is None:
        pass_cnt = 0
    else:
        pass_cnt = stat.pass_cnt
        
    # Raw Pass Rate
    if stat.pass_rate is not None:
        raw_rate = stat.pass_rate
    elif candidate_cnt > 0:
        raw_rate = (pass_cnt / candidate_cnt) * 100
    else:
        raw_rate = 0 # No data
        
    # 2. Bayesian Smoothing (Confidence Weighting)
    # Pulls small-sample rates towards the global average.
    # C is the "confidence" parameter (number of virtual samples)
    # Higher C = stronger pull to average (better for low-sample certs)
    C = 200  # Increased from 50 to prevent extreme scores for rare exams 
    
    # We need counts for Bayesian. Percentage isn't enough.
    # If we only have rate, we estimate counts or just use rate.
    # But we usually have counts.
    
    if candidate_cnt > 0:
        # Bayesian Average Formula: (RawPass + C * GlobalAvg) / (Candidates + C)
        # Note: GlobalAvg is percent (0-100), so we use C * (GlobalAvg/100) for virtual pass count?
        # No, simpler: Weighted Average of RawRate and GlobalRate
        # Rate = (Candidates * RawRate + C * GlobalRate) / (Candidates + C)
        
        smoothed_rate = (candidate_cnt * raw_rate + C * global_avg_rate) / (candidate_cnt + C)
    else:
        smoothed_rate = global_avg_rate # No data -> Average Difficulty
        
    # 3. Base Difficulty Score (0-10)
    # Lower pass rate = Higher difficulty
    base_score = (100 - smoothed_rate) / 10
    
    # 4. Multipliers
    
    # Type Multiplier (Reduced to prevent over-inflation)
    type_mult = 1.0
    if qual.qual_type == "국가전문자격":
        type_mult = 1.2  # Reduced from 1.5
    elif qual.qual_type == "국가민간자격":
        type_mult = 0.9  # Increased from 0.8
        
    # Grade Multiplier
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
        
    # Exam Structure Multiplier
    struct_mult = 1.0
    if stat.exam_structure:
        info = stat.exam_structure
        if "실기" in info or "면접" in info:
            struct_mult = 1.1
            
    # Calculate Final
    final_score = base_score * type_mult * grade_mult * struct_mult
    
    # 5. Candidate Count Penalty (Extra)
    # If simple sample counts are extremely low (< 10), we can add a small "Uncertainty Penalty" 
    # effectively making it slightly harder (safer bet) or just rely on Bayesian.
    # Bayesian already handles this by pulling to mean.
    # Check: If 1 person (Raw=100%, Diff=0) -> Smooth=48% -> Diff=5.2.
    # If 1 person (Raw=0%, Diff=10) -> Smooth=46% -> Diff=5.4.
    # So small samples congregate around the Mean (5.2-5.4). This is "Safe".
    # But User said "1 person 1 pass != 100%".
    # With Bayesian, 1/1 becomes ~48%. Correct.
    
    # Cap limits
    final_score = min(9.9, max(1.0, final_score))
    
    return round(final_score, 2)

def main():
    db = SessionLocal()
    try:
        print("Calculating Global Stats...")
        global_avg = get_global_avg_pass_rate(db)
        print(f"Global Average Pass Rate: {global_avg:.2f}%")
        
        quals = db.query(Qualification).all()
        print(f"Processing {len(quals)} qualifications...")
        
        count = 0
        total_stats = 0
        
        for q in quals:
            stats = db.query(QualificationStats).filter(
                QualificationStats.qual_id == q.qual_id
            ).all()
            
            for s in stats:
                total_stats += 1
                new_diff = calculate_difficulty(q, s, global_avg)
                if new_diff is not None:
                    s.difficulty_score = new_diff
                    count += 1
            
        db.commit()
        print(f"Updated difficulty for {count}/{total_stats} stats records.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
