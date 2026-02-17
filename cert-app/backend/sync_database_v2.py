
import os
import re
import csv
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import sys

# Add current directory to path to import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app.models import Base, Qualification, QualificationStats, Job, Major, MajorQualificationMap
from app.services.data_loader import data_loader

def sync_data():
    print("Starting comprehensive database synchronization...")
    
    # 1. Initialize DataLoader
    data_loader.load_data()
    print(f"DataLoader loaded: {len(data_loader.qualifications)} quals, {len(data_loader.jobs)} jobs, {len(data_loader.major_mappings)} major groupings")

    db = SessionLocal()
    try:
        # 2. Sync Qualifications
        print("Syncing qualifications...")
        db.execute(text("TRUNCATE TABLE qualification RESTART IDENTITY CASCADE"))
        for q_obj in data_loader.qualifications:
            new_q = Qualification(
                qual_id=q_obj.qual_id,
                qual_name=q_obj.qual_name,
                qual_type=q_obj.qual_type,
                main_field=q_obj.main_field,
                ncs_large=q_obj.ncs_large,
                managing_body=q_obj.managing_body,
                grade_code=q_obj.grade_code,
                is_active=q_obj.is_active
            )
            db.add(new_q)
        db.commit()
        print("Qualifications synced.")

        # 3. Sync Jobs
        print("Syncing jobs...")
        db.execute(text("TRUNCATE TABLE job RESTART IDENTITY CASCADE"))
        for j_obj in data_loader.jobs:
            new_j = Job(
                job_id=j_obj.job_id,
                job_name=j_obj.job_name,
                work_conditions=j_obj.work_conditions,
                outlook_summary=j_obj.outlook_summary,
                entry_salary=j_obj.entry_salary,
                similar_jobs=j_obj.similar_jobs,
                aptitude=j_obj.aptitude,
                employment_path=j_obj.employment_path,
                reward=j_obj.reward,
                stability=j_obj.stability,
                development=j_obj.development,
                condition=j_obj.condition,
                professionalism=j_obj.professionalism,
                equality=j_obj.equality
            )
            db.add(new_j)
        db.commit()
        print("Jobs synced.")

        # 4. Sync Stats
        print("Syncing qualification stats...")
        db.execute(text("TRUNCATE TABLE qualification_stats RESTART IDENTITY CASCADE"))
        for qual_id, stats_list in data_loader.stats.items():
            for stat in stats_list:
                new_stat = QualificationStats(
                    qual_id=stat.qual_id,
                    year=stat.year,
                    exam_round=stat.exam_round,
                    candidate_cnt=stat.candidate_cnt,
                    pass_cnt=stat.pass_cnt,
                    pass_rate=stat.pass_rate,
                    exam_structure=stat.exam_structure,
                    difficulty_score=stat.difficulty_score
                )
                db.add(new_stat)
        db.commit()
        print("Stats synced.")

        # 5. Populate All Majors from detail_major1.csv
        print("Syncing ALL 8000+ detailed majors...")
        db.execute(text("TRUNCATE TABLE major RESTART IDENTITY CASCADE"))
        
        detail_major_file = os.path.join("dataset", "detail_major1.csv")
        if os.path.exists(detail_major_file):
            with open(detail_major_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    m_name = row.get("detail_name", "").strip()
                    if m_name:
                        major = Major(major_name=m_name, major_category="기타")
                        db.add(major)
            db.commit()
        print(f"Major table populated. Total: {db.query(Major).count()}")

        # 6. Sync Major-Qualification Mappings
        # We need to map detail_major to integrated_code to get certs
        print("Syncing major-qualification mappings...")
        db.execute(text("TRUNCATE TABLE major_qualification_map RESTART IDENTITY CASCADE"))
        
        # Load mapping of detail_id -> integrated_code
        detail_to_integrated = {}
        detail_integrated_file = os.path.join("dataset", "detail_major_integrated1.csv")
        if os.path.exists(detail_integrated_file):
            with open(detail_integrated_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    detail_to_integrated[row['detail_id']] = row['integrated_code']

        # Load detail_id -> detail_name
        detail_id_to_name = {}
        if os.path.exists(detail_major_file):
            with open(detail_major_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    detail_id_to_name[row['detail_id']] = row['detail_name']

        # Group detail names by integrated_code
        integrated_to_details = {}
        for d_id, i_code in detail_to_integrated.items():
            if i_code not in integrated_to_details: integrated_to_details[i_code] = []
            name = detail_id_to_name.get(d_id)
            if name: integrated_to_details[i_code].append(name)

        # Load integrated_code -> cert_id
        major_cert_file = os.path.join("dataset", "integrated_major_certificate1.csv")
        if os.path.exists(major_cert_file):
            with open(major_cert_file, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    i_code = row['integrated_code']
                    cert_id_str = row['cert_id']
                    qual_id = data_loader.str_id_to_int.get(cert_id_str)
                    
                    if qual_id and i_code in integrated_to_details:
                        for d_name in integrated_to_details[i_code]:
                            mapping = MajorQualificationMap(
                                major=d_name,
                                qual_id=qual_id,
                                score=9.0, # Default high score for explicitly mapped certs
                                reason="전공 관련 전문 자격증"
                            )
                            db.add(mapping)
        db.commit()
        print("Major-Qualification mappings synced.")

        # 7. Sync Qualification-Job Mappings
        print("Syncing qualification-job mappings...")
        db.execute(text("TRUNCATE TABLE qualification_job_map RESTART IDENTITY CASCADE"))
        for qual_id, jobs in data_loader.qual_job_mapping.items():
            for job in jobs:
                db.execute(
                    text("INSERT INTO qualification_job_map (qual_id, job_id) VALUES (:qid, :jid)"),
                    {"qid": qual_id, "jid": job.job_id}
                )
        db.commit()
        print("Qualification-Job mappings synced.")

        print("SUCCESS: Database is now fully synchronized with CSV data.")
        
    except Exception as e:
        print(f"CRITICAL ERROR during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_data()
