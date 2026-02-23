
import logging
from app.redis_client import redis_client

logger = logging.getLogger("stream_producer")

class StreamProducer:
    """
    Producer for real-time certification updates using Redis Pub/Sub.
    (Kafka dependency removed for 'Pay-as-you-NOT' optimization)
    """
    def __init__(self):
        self.channel = "cert_updates"
        logger.info("Redis Stream Producer initialized.")

    def produce_update(self, data: dict):
        """Send update to Redis channel."""
        try:
            receivers = redis_client.publish(self.channel, data)
            logger.info(f"Published update for cert {data.get('qual_id')} to {receivers} listeners.")
        except Exception as e:
            logger.error(f"Failed to publish redis message: {e}")

stream_producer = StreamProducer()
