import schedule
import time
import logging
from datetime import datetime

from app.database import SessionLocal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")


def run_monthly_update():
    """월별 자격증/법령 데이터 업데이트. Render cron 또는 APScheduler로 호출 가능."""
    logger.info(f"Starting scheduled monthly update at {datetime.now()}")
    db = SessionLocal()
    try:
        # law_update_pipeline 등 실제 업데이트 로직 호출
        # from app.services.law_update_pipeline import law_update_pipeline
        # law_update_pipeline.process_updates(db)  # 구현 시 사용
        logger.info("Monthly update completed (no-op: pipeline not wired).")
    except Exception as e:
        logger.error(f"Error during monthly update: {e}")
    finally:
        db.close()

def start_scheduler():
    """스케줄러 루프. 월 1회 03:00 또는 30일 간격으로 run_monthly_update 실행."""
    logger.info("Scheduler started. Monitoring Q-Net and Legal changes every month.")
    # schedule.every().month.at("03:00").do(run_monthly_update)
    schedule.every(30).days.do(run_monthly_update)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # If run directly, logic to execute once or start loop
    print("Running as standalone scheduler...")
    # run_monthly_update() # Execute once for testing if needed
    # start_scheduler()
