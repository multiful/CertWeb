"""Redis client for caching and rate limiting."""
import json
import hashlib
import logging
from typing import Optional, Any, List
from datetime import datetime
import redis
from functools import wraps

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
            self.client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            self.client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except:
            return False
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
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
