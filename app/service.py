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

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service layer for product operations.
    Handles vendor integration, normalization, and business logic.
    """
    
    def __init__(self):
        self.normalizer = ProductNormalizer()
    
    async def _fetch_from_vendor_a(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor A.
        
        Args:
            sku: Product SKU
            
        Returns:
            Normalized product or None if not found/invalid
        """
        try:
            response = await VendorA.get_product(sku)
            if response is None:
                logger.info(f"VendorA: Product {sku} not found")
                return None
            
            return self.normalizer.normalize_vendor_a(response)
        except Exception as e:
            # Graceful error handling - if vendor fails, skip it
            logger.error(f"VendorA: Error fetching {sku}: {str(e)}")
            return None
    
    async def _fetch_from_vendor_b(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor B.
        
        Args:
            sku: Product SKU
            
        Returns:
            Normalized product or None if not found/invalid
        """
        try:
            response = await VendorB.get_product(sku)
            if response is None:
                logger.info(f"VendorB: Product {sku} not found")
                return None
            
            return self.normalizer.normalize_vendor_b(response)
        except Exception as e:
            # Graceful error handling - if vendor fails, skip it
            logger.error(f"VendorB: Error fetching {sku}: {str(e)}")
            return None

    async def _fetch_from_vendor_c(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Fetch and normalize product from Vendor C.
        
        Args:
            sku: Product SKU
            
        Returns:
            Normalized product or None if not found/invalid
        """
        try:
            response = await VendorC.get_product(sku)
            if response is None:
                logger.info(f"VendorC: Product {sku} not found")
                return None
            
            return self.normalizer.normalize_vendor_c(response)
        except Exception as e:
            # Graceful error handling - if vendor fails, skip it
            logger.error(f"VendorC: Error fetching {sku}: {str(e)}")
            return None
    
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
        
        # Requirement 6: Caching - Save to cache
        # Using model_dump() for Pydantic v2
        await cache.set(cache_key, best_product.model_dump())
        
        return best_product
