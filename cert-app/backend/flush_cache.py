from app.redis_client import redis_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if redis_client.is_connected():
        logger.info("Connected to Redis. Flushing cache...")
        redis_client.client.flushall()
        logger.info("Redis cache flushed successfully.")
    else:
        logger.warning("Could not connect to Redis to flush cache.")
