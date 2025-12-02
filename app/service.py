"""
Product service - Core business logic for fetching and normalizing product data.
Implements concurrent vendor calls and error handling.
"""

import asyncio
from typing import List, Optional
import logging
from app.models import NormalizedProduct, ProductResponse
from app.vendors import VendorA, VendorB, VendorC
from app.normalizer import ProductNormalizer
from app.cache import cache
from app.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service layer for product operations.
    Handles vendor integration, normalization, and business logic.
    """
    
    def __init__(self):
        self.normalizer = ProductNormalizer()
        
        # Requirement 13: Circuit Breakers for each vendor
        self.circuit_breaker_a = CircuitBreaker("VendorA", failure_threshold=3, cooldown_seconds=30)
        self.circuit_breaker_b = CircuitBreaker("VendorB", failure_threshold=3, cooldown_seconds=30)
        self.circuit_breaker_c = CircuitBreaker("VendorC", failure_threshold=3, cooldown_seconds=30)
    
    async def _fetch_with_retry(self, fetch_func, vendor_name: str, retries: int = 2, timeout: float = 2.0):
        """
        Helper method to execute a fetch function with timeout and retries.
        
        Requirement 11:
        - Timeout: 2 seconds
        - Retries: 2 attempts (total 3 tries)
        """
        attempt = 0
        last_exception = None
        
        while attempt <= retries:
            try:
                # Use asyncio.wait_for to enforce timeout
                return await asyncio.wait_for(fetch_func(), timeout=timeout)
            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Request timed out after {timeout}s")
                logger.warning(f"{vendor_name}: Timeout on attempt {attempt + 1}/{retries + 1}")
            except Exception as e:
                last_exception = e
                logger.warning(f"{vendor_name}: Error on attempt {attempt + 1}/{retries + 1}: {str(e)}")
            
            attempt += 1
            if attempt <= retries:
                # Exponential backoff or simple delay could be added here
                await asyncio.sleep(0.1 * attempt)
        
        logger.error(f"{vendor_name}: Failed after {retries + 1} attempts. Last error: {str(last_exception)}")
        return None

    async def _fetch_from_vendor_a(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor A with circuit breaker and retry logic.
        """
        async def fetch():
            response = await VendorA.get_product(sku)
            if response is None:
                logger.info(f"VendorA: Product {sku} not found")
                return None
            return self.normalizer.normalize_vendor_a(response)

        # Requirement 13: Circuit breaker wraps the retry logic
        return await self.circuit_breaker_a.call(self._fetch_with_retry, fetch, "VendorA")
    
    async def _fetch_from_vendor_b(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor B with circuit breaker and retry logic.
        """
        async def fetch():
            response = await VendorB.get_product(sku)
            if response is None:
                logger.info(f"VendorB: Product {sku} not found")
                return None
            return self.normalizer.normalize_vendor_b(response)

        # Requirement 13: Circuit breaker wraps the retry logic
        return await self.circuit_breaker_b.call(self._fetch_with_retry, fetch, "VendorB")

    async def _fetch_from_vendor_c(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor C with circuit breaker and retry logic.
        """
        async def fetch():
            response = await VendorC.get_product(sku)
            if response is None:
                logger.info(f"VendorC: Product {sku} not found")
                return None
            return self.normalizer.normalize_vendor_c(response)

        # Requirement 13: Circuit breaker wraps the retry logic
        return await self.circuit_breaker_c.call(self._fetch_with_retry, fetch, "VendorC")
    
    async def get_product(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Get product from all vendors concurrently and return the best option.
        
        Business Logic:
        1. Check Redis cache
        2. Call all vendors (A, B, C) in parallel using asyncio.gather()
        3. Normalize responses from each vendor
        4. Select best vendor (stock > 0, lowest price)
        5. Save to Redis cache
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            NormalizedProduct (best vendor) or None if all out of stock
        """
        # Requirement 6: Caching - Check cache first
        cache_key = cache.get_cache_key("product", sku)
        cached_data = await cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Returning cached data for SKU: {sku}")
            return NormalizedProduct(**cached_data)
            
        logger.info(f"Fetching product {sku} from all vendors")
        
        # Requirement 4 & 8: Concurrency - Call all vendors in parallel
        # Using asyncio.gather() to execute vendor calls concurrently
        vendor_results = await asyncio.gather(
            self._fetch_from_vendor_a(sku),
            self._fetch_from_vendor_b(sku),
            self._fetch_from_vendor_c(sku),
            return_exceptions=False  # We handle exceptions in individual methods
        )
        
        # Filter out None results (failed/not found vendors)
        valid_products: List[NormalizedProduct] = [
            product for product in vendor_results if product is not None
        ]
        
        logger.info(f"Received {len(valid_products)} valid responses for {sku}")
        
        # Requirement 3: Best Vendor Selection
        best_product = self.normalizer.select_best_vendor(valid_products)
        
        if best_product is None:
            # All vendors are out of stock or no valid data
            logger.info(f"Product {sku} is OUT_OF_STOCK across all vendors")
            return None
        
        # Requirement 12: Mandatory Redis Cache with TTL = 2 minutes (120s)
        # Using model_dump(mode='json') for Pydantic v2 with datetime serialization
        await cache.set(cache_key, best_product.model_dump(mode='json'), ttl=120)
        
        return best_product
