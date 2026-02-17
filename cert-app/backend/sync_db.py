import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add data loader path logic to handle both dev and notebook contexts
sys.path.append(os.path.join(os.getcwd(), 'cert-app', 'backend'))
try:
    from app.services.data_loader import DataLoader
except ImportError:
    # If initial import fails, try relative import if running from backend dir
    sys.path.append(os.getcwd())
    from app.services.data_loader import DataLoader

# Load .env intelligently
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, '.env')):
    load_dotenv(os.path.join(current_dir, '.env'))
else:
    load_dotenv('cert-app/backend/.env')

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL not found.")
    sys.exit(1)

if '!' in db_url and '%' not in db_url:
    db_url = db_url.replace('!', '%21')

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def sync_data():
    dataset_path = 'cert-app/backend/dataset'
    if not os.path.exists(dataset_path):
        dataset_path = 'dataset' # If running from backend dir
        
    dl = DataLoader(dataset_path)
    dl.load_data()
    print(f"Loaded {len(dl.qualifications)} quals")

    db = SessionLocal()
    try:
        print("Truncating old data...")
        # Use CASCADE to clean up dependent tables
        db.execute(text("TRUNCATE TABLE major_qualification_map, qualification_job_map, qualification_stats, job, qualification RESTART IDENTITY CASCADE"))
        db.commit()
        
        print("Inserting qualifications...")
        quals_data = [{
            "id": q.qual_id, "name": q.qual_name, "type": q.qual_type,
            "field": q.main_field, "ncs": q.ncs_large, "body": q.managing_body,
            "grade": q.grade_code, "active": q.is_active
        } for q in dl.qualifications]
        
        sql = text("INSERT INTO qualification (qual_id, qual_name, qual_type, main_field, ncs_large, managing_body, grade_code, is_active) VALUES (:id, :name, :type, :field, :ncs, :body, :grade, :active)")
        db.execute(sql, quals_data)
        db.commit()
        
        print("Inserting jobs...")
        jobs_data = [{
            "id": j.job_id, "name": j.job_name, "outlook": j.outlook, "salary": j.salary_info, "cond": j.work_conditions,
            "desc": j.description, "out_sum": j.outlook_summary, "entry": j.entry_salary,
            "r": j.reward, "s": j.stability, "d": j.development, "c": j.condition, "p": j.professionalism, "e": j.equality,
            "sim": j.similar_jobs, "apt": j.aptitude, "path": j.employment_path
        } for j in dl.jobs]
        
        if jobs_data:
            sql_jobs = text("INSERT INTO job (job_id, job_name, outlook, salary_info, work_conditions, description, outlook_summary, entry_salary, reward, stability, development, condition, professionalism, equality, similar_jobs, aptitude, employment_path) VALUES (:id, :name, :outlook, :salary, :cond, :desc, :out_sum, :entry, :r, :s, :d, :c, :p, :e, :sim, :apt, :path)")
            db.execute(sql_jobs, jobs_data)
            db.commit()

        print("Inserting stats...")
        stats_data = []
        for qual_id, stats in dl.stats.items():
            for s in stats:
                stats_data.append({
                    "qid": qual_id, "year": s.year, "round": s.exam_round, "can": s.candidate_cnt,
                    "pass": s.pass_cnt, "rate": s.pass_rate, "struct": s.exam_structure, "diff": s.difficulty_score
                })
        
        if stats_data:
            sql_stats = text("INSERT INTO qualification_stats (qual_id, year, exam_round, candidate_cnt, pass_cnt, pass_rate, exam_structure, difficulty_score) VALUES (:qid, :year, :round, :can, :pass, :rate, :struct, :diff)")
            db.execute(sql_stats, stats_data)
            db.commit()
            
        print("Inserting mappings...")
        # Major maps
        major_data = []
        for major, mappings in dl.major_mappings.items():
            for m in mappings:
                major_data.append({
                    "major": major, "qid": m.qual_id, "score": m.score, "weight": m.weight, "reason": m.reason
                })
        if major_data:
            sql_major = text("INSERT INTO major_qualification_map (major, qual_id, score, weight, reason) VALUES (:major, :qid, :score, :weight, :reason)")
            db.execute(sql_major, major_data)
            db.commit()
            
        # Job maps
        job_map_data = []
        for qual_id, jobs in dl.qual_job_mapping.items():
            for j in jobs:
                if j.job_id:
                    job_map_data.append({"qid": qual_id, "jid": j.job_id})
        
        if job_map_data:
            # unique constraint might be hit if dupes, but TRUNCATE cleared it
            sql_job_map = text("INSERT INTO qualification_job_map (qual_id, job_id) VALUES (:qid, :jid) ON CONFLICT DO NOTHING")
            db.execute(sql_job_map, job_map_data)
            db.commit()

        print("--- Verification ---")
        q_cnt = db.execute(text("SELECT count(*) FROM qualification")).scalar()
        j_cnt = db.execute(text("SELECT count(*) FROM job")).scalar()
        print(f"Total: {q_cnt} qualifications, {j_cnt} jobs")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        
    print("SYNC COMPLETE")

if __name__ == "__main__":
    sync_data()
