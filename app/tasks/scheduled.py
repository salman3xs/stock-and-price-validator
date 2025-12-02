"""
Celery tasks for background job execution.

Implements Requirement 14: Background Job
- Cache prewarming for popular SKUs
- Vendor performance logging
"""

import asyncio
import logging
from app.tasks.celery_app import celery_app
from app.tasks.jobs import background_job_manager

logger = logging.getLogger(__name__)


@celery_app.task(name='app.celery_tasks.run_scheduled_background_job')
def run_scheduled_background_job():
    """
    Celery task wrapper for scheduled background job.
    
    Requirement 14: Runs every 5 minutes
    - Prewarms cache for popular SKUs
    - Logs vendor performance metrics
    """
    logger.info("Celery task started: run_scheduled_background_job")
    
    try:
        # Run async job in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(background_job_manager.run_scheduled_job())
            logger.info("Celery task completed successfully")
            return {"status": "success", "message": "Background job completed"}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Celery task failed: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(name='app.celery_tasks.prewarm_cache_for_sku')
def prewarm_cache_for_sku(sku: str):
    """
    Celery task to prewarm cache for a specific SKU.
    
    Args:
        sku: Product SKU to prewarm
        
    Returns:
        Task result dictionary
    """
    logger.info(f"Celery task started: prewarm_cache_for_sku({sku})")
    
    try:
        from app.core.service import ProductService
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            service = ProductService()
            product = loop.run_until_complete(service.get_product(sku))
            
            if product:
                logger.info(f"Successfully prewarmed cache for {sku}")
                return {"status": "success", "sku": sku, "available": True}
            else:
                logger.info(f"SKU {sku} not available")
                return {"status": "success", "sku": sku, "available": False}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to prewarm {sku}: {str(e)}", exc_info=True)
        return {"status": "error", "sku": sku, "message": str(e)}
