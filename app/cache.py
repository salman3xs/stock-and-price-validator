"""
Centralized Redis Cache Manager for async operations.

Implements Requirement 6: Caching
- Redis-based caching
- TTL = 60 seconds (configurable via environment)
- Cache per SKU

This module provides a singleton Redis connection pool and async cache operations.
"""

from typing import Optional, Any
import json
import logging
from redis import asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Centralized Redis cache manager with async operations.
    
    Implements singleton pattern to ensure single connection pool.
    Provides async methods for get, set, delete, and exists operations.
    """
    
    _instance: Optional['RedisCache'] = None
    _redis_client: Optional[Redis] = None
    
    def __new__(cls):
        """
        Singleton pattern implementation.
        Ensures only one instance of RedisCache exists.
        """
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize Redis cache configuration.
        
        Configuration is loaded from environment variables:
        - REDIS_HOST: Redis server host (default: localhost)
        - REDIS_PORT: Redis server port (default: 6379)
        - REDIS_DB: Redis database number (default: 0)
        - REDIS_PASSWORD: Redis password (optional)
        - CACHE_TTL: Cache time-to-live in seconds (default: 60)
        """
        # Only initialize once
        if not hasattr(self, '_initialized'):
            self.host = os.getenv('REDIS_HOST', 'localhost')
            self.port = int(os.getenv('REDIS_PORT', '6379'))
            self.db = int(os.getenv('REDIS_DB', '0'))
            self.password = os.getenv('REDIS_PASSWORD', None)
            self.ttl = int(os.getenv('CACHE_TTL', '60'))  # Requirement 6: TTL = 60 seconds
            self._initialized = True
            logger.info(f"Redis cache configured: {self.host}:{self.port}, DB={self.db}, TTL={self.ttl}s")
    
    async def connect(self) -> None:
        """
        Establish async connection to Redis.
        
        Creates a connection pool for efficient connection reuse.
        Should be called during application startup.
        
        Raises:
            RedisError: If connection fails
        """
        if self._redis_client is None:
            try:
                self._redis_client = await aioredis.from_url(
                    f"redis://{self.host}:{self.port}/{self.db}",
                    password=self.password if self.password else None,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=10  # Connection pool size
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("✅ Redis connection established successfully")
            except RedisError as e:
                logger.error(f"❌ Failed to connect to Redis: {str(e)}")
                raise
    
    async def disconnect(self) -> None:
        """
        Close Redis connection.
        
        Should be called during application shutdown.
        """
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        if not self._redis_client:
            logger.warning("Redis client not connected, skipping cache get")
            return None
        
        try:
            value = await self._redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be serialized to JSON)
            ttl: Time-to-live in seconds (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._redis_client:
            logger.warning("Redis client not connected, skipping cache set")
            return False
        
        try:
            ttl_seconds = ttl if ttl is not None else self.ttl
            serialized_value = json.dumps(value)
            await self._redis_client.setex(key, ttl_seconds, serialized_value)
            logger.debug(f"Cache SET: {key} (TTL={ttl_seconds}s)")
            return True
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {str(e)}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error for key '{key}': {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self._redis_client:
            logger.warning("Redis client not connected, skipping cache delete")
            return False
        
        try:
            result = await self._redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key} (deleted={result > 0})")
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._redis_client:
            return False
        
        try:
            result = await self._redis_client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Useful for cache invalidation of related items.
        
        Args:
            pattern: Redis key pattern (e.g., "product:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._redis_client:
            logger.warning("Redis client not connected, skipping pattern clear")
            return 0
        
        try:
            keys = []
            async for key in self._redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self._redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"Redis CLEAR PATTERN error for '{pattern}': {str(e)}")
            return 0
    
    def get_cache_key(self, prefix: str, identifier: str) -> str:
        """
        Generate standardized cache key.
        
        Args:
            prefix: Key prefix (e.g., "product", "vendor")
            identifier: Unique identifier (e.g., SKU)
            
        Returns:
            Formatted cache key (e.g., "product:SKU001")
        """
        return f"{prefix}:{identifier}"


# Singleton instance
cache = RedisCache()
