
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models import Qualification
from app.redis_client import redis_client
import orjson
import time

logger = logging.getLogger("fast_sync")

class FastSyncService:
    """
    Ultra-fast synchronization service using Redis Pipelining and Bulk operations.
    Inspired by Antigravity's 'Zero Gravity' throughput patterns.
    """

    @staticmethod
    def sync_all_to_redis(db: Session):
        """
        Synchronize all qualifications from Database to Redis in a single pipeline.
        This provides O(1) read access for all certs with near-zero latency.
        """
        start_time = time.time()
        logger.info("Starting Full Synchronous Burst to Redis...")

        # 1. Fetch all active qualifications
        quals = db.query(Qualification).filter(Qualification.is_active == True).all()
        
        if not quals:
            logger.warning("No qualifications found to sync.")
            return

        # 2. Open Redis Pipeline for batching commands
        if not redis_client.client:
            logger.error("Redis client not initialized. Sync cancelled.")
            return

        pipe = redis_client.client.pipeline()
        
        count = 0
        for q in quals:
            # Prepare data (matching fastcert format used by Redis Worker and fast_certs api)
            data = {
                "qual_id": q.qual_id,
                "qual_name": q.qual_name,
                "qual_type": q.qual_type,
                "main_field": q.main_field,
                "ncs_large": q.ncs_large,
                "managing_body": q.managing_body,
                "grade_code": q.grade_code,
                "is_active": q.is_active
            }
            
            payload = {"status": "success", "data": data}
            
            # Using orjson + bytes (no decoding) for maximum throughput
            # Since our RedisClient uses decode_responses=True by default, 
            # we send strings, but pipeline will bundle them.
            pipe.set(f"fastcert:{q.qual_id}", orjson.dumps(payload).decode())
            count += 1

        # 3. Execute all commands in the buffer
        pipe.execute()
        
        duration = time.time() - start_time
        msg = f"Sync complete. {count} items pushed to Redis in {duration:.2f}s."
        logger.info(msg)
        print(msg)
        return count

if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.getcwd())
    from app.api.deps import get_db_session
    
    # Simple runner
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings
    
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    try:
        FastSyncService.sync_all_to_redis(db)
    finally:
        db.close()

fast_sync_service = FastSyncService()
