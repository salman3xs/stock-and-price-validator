"""
Rate Limiting Middleware for API requests.

Implements Requirement 15: Rate Limiting
- 60 requests per minute per API key
- Uses Redis for distributed rate limiting
- Returns 429 Too Many Requests when limit exceeded
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.cache import cache

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Requirement 15:
    - 60 requests per minute per API key
    - Uses Redis for distributed counting
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests allowed per minute (default: 60)
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60  # 1 minute window
        logger.info(f"Rate limiter initialized: {requests_per_minute} requests per minute")
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            API key or None if not present
        """
        # Check x-api-key header (case-insensitive)
        api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        return api_key
    
    def _get_rate_limit_key(self, api_key: str) -> str:
        """
        Generate Redis key for rate limiting.
        
        Args:
            api_key: API key from request
            
        Returns:
            Redis key for rate limit counter
        """
        # Use current minute as part of the key for sliding window
        current_minute = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        return f"rate_limit:{api_key}:{current_minute}"
    
    async def _check_rate_limit(self, api_key: str) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            api_key: API key from request
            
        Returns:
            Tuple of (allowed: bool, current_count: int, limit: int)
        """
        rate_limit_key = self._get_rate_limit_key(api_key)
        
        # Get current count from Redis
        current_count_str = await cache.get(rate_limit_key)
        current_count = int(current_count_str) if current_count_str else 0
        
        # Check if limit exceeded
        if current_count >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for API key {api_key[:8]}***: "
                f"{current_count}/{self.requests_per_minute}"
            )
            return False, current_count, self.requests_per_minute
        
        # Increment counter
        new_count = current_count + 1
        
        # Set with TTL of window_seconds
        await cache.set(rate_limit_key, new_count, ttl=self.window_seconds)
        
        logger.debug(
            f"Rate limit check for {api_key[:8]}***: "
            f"{new_count}/{self.requests_per_minute}"
        )
        
        return True, new_count, self.requests_per_minute
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or 429 error if rate limited
        """
        # Extract API key
        api_key = self._get_api_key(request)
        
        # If no API key, reject request
        if not api_key:
            logger.warning(f"Request without API key from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Missing API Key",
                    "detail": "x-api-key header is required",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Check rate limit
        allowed, current_count, limit = await self._check_rate_limit(api_key)
        
        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "detail": f"Maximum {limit} requests per minute allowed",
                    "current_count": current_count,
                    "limit": limit,
                    "retry_after": 60,  # seconds
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(60),
                    "Retry-After": "60"
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Add rate limit info headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - current_count)
        response.headers["X-RateLimit-Reset"] = str(self.window_seconds)
        
        return response
