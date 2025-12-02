"""
FastAPI application entry point.
"""

from fastapi import FastAPI
import logging
from app.routers import products
from app.cache import cache
from app.rate_limiter import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Product Availability & Pricing Normalization Service",
    version="1.0.0",
    docs_url="/docs"
)

# Requirement 15: Add Rate Limiting Middleware
# 60 requests per minute per API key
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Redis Connection Lifecycle
@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup."""
    await cache.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown."""
    await cache.disconnect()

# Include routers
app.include_router(products.router)


@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "service": "Product Availability & Pricing Normalization Service",
        "version": "1.0.0",
        "endpoints": {
            "get_product": "/products/{sku}",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "product-normalization-service"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
