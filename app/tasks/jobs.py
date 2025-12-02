"""
Background Jobs for scheduled tasks.

Implements Requirement 14: Background Job
- Runs every 5 minutes
- Prewarms cache for frequently-requested SKUs
- Logs vendor performance (latency + failures)
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from app.core.service import ProductService
from app.core.cache import cache

logger = logging.getLogger(__name__)


class BackgroundJobManager:
    """
    Manages background scheduled tasks.
    
    Requirement 14:
    - Cache prewarming for popular SKUs
    - Vendor performance monitoring
    """
    
    def __init__(self):
        """Initialize background job manager."""
        self.product_service = ProductService()
        
        # Track request statistics
        self.request_stats: Dict[str, int] = defaultdict(int)
        self.vendor_performance: Dict[str, Dict[str, Any]] = {
            "VendorA": {"total_calls": 0, "failures": 0, "total_latency": 0.0},
            "VendorB": {"total_calls": 0, "failures": 0, "total_latency": 0.0},
            "VendorC": {"total_calls": 0, "failures": 0, "total_latency": 0.0},
        }
        
        logger.info("Background job manager initialized")
    
    def track_request(self, sku: str):
        """
        Track SKU request for popularity analysis.
        
        Args:
            sku: Product SKU that was requested
        """
        self.request_stats[sku] += 1
    
    def track_vendor_call(self, vendor_name: str, success: bool, latency: float):
        """
        Track vendor API call performance.
        
        Args:
            vendor_name: Name of the vendor
            success: Whether the call succeeded
            latency: Call latency in seconds
        """
        stats = self.vendor_performance[vendor_name]
        stats["total_calls"] += 1
        stats["total_latency"] += latency
        
        if not success:
            stats["failures"] += 1
    
    def get_top_skus(self, limit: int = 10) -> List[str]:
        """
        Get most frequently requested SKUs.
        
        Args:
            limit: Maximum number of SKUs to return
            
        Returns:
            List of top SKU strings
        """
        sorted_skus = sorted(
            self.request_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [sku for sku, _ in sorted_skus[:limit]]
    
    async def prewarm_cache(self):
        """
        Prewarm cache for frequently-requested SKUs.
        
        Requirement 14: Cache Prewarming
        - Fetches top 10 most popular SKUs
        - Updates cache proactively
        - Runs every 5 minutes
        """
        logger.info("Starting cache prewarming job...")
        
        top_skus = self.get_top_skus(limit=10)
        
        if not top_skus:
            logger.info("No popular SKUs to prewarm (no requests yet)")
            return
        
        logger.info(f"Prewarming cache for {len(top_skus)} popular SKUs: {top_skus}")
        
        prewarmed = 0
        failed = 0
        
        for sku in top_skus:
            try:
                # Fetch product data (will update cache)
                start_time = time.time()
                product = await self.product_service.get_product(sku)
                latency = time.time() - start_time
                
                if product:
                    prewarmed += 1
                    logger.debug(f"Prewarmed cache for {sku} ({latency:.2f}s)")
                else:
                    logger.debug(f"SKU {sku} not available (skipped)")
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to prewarm {sku}: {str(e)}")
        
        logger.info(
            f"Cache prewarming complete: {prewarmed} successful, {failed} failed, "
            f"{len(top_skus) - prewarmed - failed} unavailable"
        )
    
    def log_vendor_performance(self):
        """
        Log vendor performance metrics.
        
        Requirement 14: Vendor Performance Logging
        - Logs latency statistics
        - Logs failure rates
        - Runs every 5 minutes
        """
        logger.info("=" * 80)
        logger.info("VENDOR PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        for vendor_name, stats in self.vendor_performance.items():
            total_calls = stats["total_calls"]
            failures = stats["failures"]
            total_latency = stats["total_latency"]
            
            if total_calls == 0:
                logger.info(f"{vendor_name}: No calls in this period")
                continue
            
            # Calculate metrics
            success_rate = ((total_calls - failures) / total_calls) * 100
            failure_rate = (failures / total_calls) * 100
            avg_latency = total_latency / total_calls
            
            logger.info(f"{vendor_name}:")
            logger.info(f"  Total Calls:   {total_calls}")
            logger.info(f"  Successful:    {total_calls - failures} ({success_rate:.1f}%)")
            logger.info(f"  Failed:        {failures} ({failure_rate:.1f}%)")
            logger.info(f"  Avg Latency:   {avg_latency:.3f}s")
            logger.info(f"  Total Latency: {total_latency:.2f}s")
        
        logger.info("=" * 80)
        
        # Reset stats for next period
        self._reset_vendor_stats()
    
    def _reset_vendor_stats(self):
        """Reset vendor performance statistics for next period."""
        for vendor_name in self.vendor_performance:
            self.vendor_performance[vendor_name] = {
                "total_calls": 0,
                "failures": 0,
                "total_latency": 0.0
            }
    
    async def run_scheduled_job(self):
        """
        Run all scheduled background tasks.
        
        Requirement 14: Runs every 5 minutes
        - Prewarm cache
        - Log vendor performance
        """
        logger.info(f"Running scheduled background job at {datetime.utcnow().isoformat()}")
        
        try:
            # Task 1: Prewarm cache for popular SKUs
            await self.prewarm_cache()
            
            # Task 2: Log vendor performance
            self.log_vendor_performance()
            
            logger.info("Scheduled background job completed successfully")
            
        except Exception as e:
            logger.error(f"Error in scheduled background job: {str(e)}", exc_info=True)


# Singleton instance
background_job_manager = BackgroundJobManager()
