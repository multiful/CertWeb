import orjson
import hashlib
import logging
from typing import Optional, Any, List
from datetime import datetime
import redis
from functools import wraps
import json

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for caching and rate limiting."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            if not settings.REDIS_URL or "localhost" in settings.REDIS_URL:
                if not settings.DEBUG:
                    logger.warning("REDIS_URL is not set for production. Caching will be disabled.")
                    self.client = None
                    return

            self.client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2, # Faster timeout
                socket_timeout=2,
                health_check_interval=30,
            )
            self.client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}. Performance may be degraded.")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected safely."""
        if self.client is None:
            return False
        try:
            return self.client.ping()
        except Exception:
            self.client = None # Reset on failure
            return False
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string using high-performance orjson."""
        try:
            # orjson returns bytes, we decode to str for redis-py (if decode_responses=True)
            return orjson.dumps(value, option=orjson.OPT_SERIALIZE_DATETIME).decode()
        except Exception:
            return str(value)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value using high-performance orjson."""
        try:
            return orjson.loads(value)
        except Exception:
            return value
    
    # ============== Cache Operations ==============
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not self.client:
            return False
        try:
            serialized = self._serialize(value)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self.client:
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    def flush_all(self) -> bool:
        """Flush all cache (use with caution!)."""
        if not self.client:
            return False
        try:
            self.client.flushall()
            return True
        except Exception as e:
            logger.error(f"Redis flush_all error: {e}")
            return False
    
    # ============== Rate Limiting ==============
    
    def check_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            tuple: (allowed, remaining, reset_after)
        """
        if not self.client:
            # If Redis is down, allow the request
            return True, max_requests, 0
        
        try:
            pipe = self.client.pipeline()
            now = datetime.utcnow().timestamp()
            window_start = now - window_seconds
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry on the key
            pipe.expire(key, window_seconds)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count > max_requests:
                # Remove the request we just added
                self.client.zrem(key, str(now))
                reset_after = int(window_seconds - (now - window_start))
                return False, 0, reset_after
            
            remaining = max_requests - current_count
            reset_after = window_seconds
            
            return True, remaining, reset_after
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, max_requests, 0
            
    # ============== Trending Operations ==============
    
    def increment_trending(self, key: str, member: str, amount: float = 1.0) -> bool:
        """Increment score for a member in a sorted set (trending)."""
        if not self.client:
            return False
        try:
            self.client.zincrby(key, amount, member)
            # Keep only top 100 to save memory
            self.client.zremrangebyrank(key, 0, -101)
            return True
        except Exception as e:
            logger.error(f"Redis zincrby error: {e}")
            return False
            
    def get_trending(self, key: str, top_n: int = 10) -> List[tuple[str, float]]:
        """Get top members from a sorted set with scores."""
        if not self.client:
            return []
        try:
            return self.client.zrevrange(key, 0, top_n - 1, withscores=True)
        except Exception as e:
            logger.error(f"Redis zrevrange error: {e}")
            return []
            
    # ============== List Operations (Recent Items) ==============
    
    def push_recent(self, key: str, value: str, max_items: int = 10) -> bool:
        """Add item to a list and keep it at most max_items."""
        if not self.client:
            return False
        try:
            pipe = self.client.pipeline()
            # Remove duplicate if exists to move it to front
            pipe.lrem(key, 0, value)
            # Push to front
            pipe.lpush(key, value)
            # Trim to max_items
            pipe.ltrim(key, 0, max_items - 1)
            # Expire after 30 days of inactivity
            pipe.expire(key, 30 * 86400)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis push_recent error: {e}")
            return False
            
    def get_recent(self, key: str, count: int = 10) -> List[str]:
        """Get recent items from a list."""
        if not self.client:
            return []
        try:
            return self.client.lrange(key, 0, count - 1)
        except Exception as e:
            logger.error(f"Redis lrange error: {e}")
            return []

    # ============== Pub/Sub Operations ==============

    def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a channel."""
        if not self.client:
            return 0
        try:
            serialized = self._serialize(message)
            return self.client.publish(channel, serialized)
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return 0

    def get_pubsub(self):
        """Get a pubsub instance."""
        if not self.client:
            return None
        return self.client.pubsub()
    
    # ============== Cache Key Helpers ==============
    
    @staticmethod
    def make_cache_key(prefix: str, *args, **kwargs) -> str:
        """Create a cache key from prefix and parameters."""
        key_parts = [prefix]
        
        for arg in args:
            key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def hash_query_params(**params) -> str:
        """Hash query parameters for cache key."""
        # Filter out None values and sort
        filtered = {k: v for k, v in params.items() if v is not None}
        param_str = json.dumps(filtered, sort_keys=True, default=str)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]


# Global Redis client instance
redis_client = RedisClient()


def cached(prefix: str, ttl: int):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = redis_client.make_cache_key(
                prefix,
                *args,
                **{k: v for k, v in kwargs.items() if k != 'db'}
            )
            
            # Try to get from cache
            cached_value = redis_client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache the result
            redis_client.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str) -> int:
    """Invalidate cache by pattern."""
    return redis_client.delete_pattern(pattern)
