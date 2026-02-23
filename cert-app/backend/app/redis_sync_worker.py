import logging
import orjson
from app.redis_client import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("redis_worker")

def start_redis_sync_worker():
    """
    Redis Pub/Sub을 사용하여 자격증 데이터 변경을 수신하고
    즉시 캐시를 갱신하는 초경량 워커 (안티그래비티 'Zero Cost' 동기화)
    """
    pubsub = redis_client.get_pubsub()
    if not pubsub:
        logger.error("Redis client not available.")
        return

    channel = "cert_updates"
    pubsub.subscribe(channel)
    logger.info(f"Subscribed to {channel}. Waiting for updates...")

    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                # RedisClient publishes serialized data
                data = orjson.loads(message['data'])
                cert_id = data.get("qual_id")
                
                if cert_id:
                    # fastcert format for ultra-low latency API
                    payload = {"status": "success", "data": data}
                    val_bytes = orjson.dumps(payload)
                    
                    # Update cache instantly
                    redis_client.client.set(f"fastcert:{cert_id}", val_bytes.decode())
                    logger.info(f"Cache updated instantly for cert {cert_id}")
            except Exception as e:
                logger.error(f"Sync worker error: {e}")

if __name__ == "__main__":
    try:
        start_redis_sync_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
