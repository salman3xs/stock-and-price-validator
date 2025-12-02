"""
Mock vendor implementations using JSON files with async I/O.

Assumption: Each vendor has different response schemas and data structures
to demonstrate normalization capabilities.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
import aiofiles
import os
import random
import asyncio
from app.models.models import VendorAResponse, VendorBResponse, VendorCResponse


class VendorA:
    """
    Mock Vendor A - Fast and reliable vendor.
    Returns data in format: product_code, inventory_count, unit_price, availability_status
    """
    
    name: str = "VendorA"
    _data_file: str = os.path.join(os.path.dirname(__file__), "vendor_a_products.json")
    _cache: Optional[Dict[str, Dict[str, Any]]] = None
    
    @classmethod
    async def _load_products(cls) -> Dict[str, Dict[str, Any]]:
        """
        Load product data from JSON file asynchronously.
        Returns:
            Dictionary of products keyed by SKU
        """
        # Simple cache to avoid reading file on every request
        # Assumption: In production, this would be replaced with Redis cache (Requirement 6)
        if cls._cache is not None:
            return cls._cache
        
        async with aiofiles.open(cls._data_file, mode='r') as f:
            content = await f.read()
            cls._cache = json.loads(content)
            return cls._cache
    
    @classmethod
    async def get_product(cls, sku: str) -> Optional[VendorAResponse]:
        """
        Fetch product data from Vendor A.
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            VendorAResponse if product exists, None otherwise
        """
        products = await cls._load_products()
        product_data = products.get(sku)
        
        if not product_data:
            return None
        
        # Determine timestamp
        # Requirement 9: Allow simulation of stale data via JSON
        if "last_updated" in product_data:
            last_updated = datetime.fromisoformat(product_data["last_updated"])
        else:
            last_updated = datetime.utcnow()

        return VendorAResponse(
            product_code=sku,
            inventory_count=product_data["inventory"],
            unit_price=product_data["price"],
            availability_status=product_data["status"],
            last_updated=last_updated
        )


class VendorB:
    """
    Mock Vendor B - Different schema and data types.
    Returns data in format: sku, stock_level, price_usd (as string), in_stock (boolean)
    """
    
    name: str = "VendorB"
    _data_file: str = os.path.join(os.path.dirname(__file__), "vendor_b_products.json")
    _cache: Optional[Dict[str, Dict[str, Any]]] = None
    
    @classmethod
    async def _load_products(cls) -> Dict[str, Dict[str, Any]]:
        """
        Load product data from JSON file asynchronously.
        
        Returns:
            Dictionary of products keyed by SKU
        """
        # Simple cache to avoid reading file on every request
        # Assumption: In production, this would be replaced with Redis cache (Requirement 6)
        if cls._cache is not None:
            return cls._cache
        
        async with aiofiles.open(cls._data_file, mode='r') as f:
            content = await f.read()
            cls._cache = json.loads(content)
            return cls._cache
    
    @classmethod
    async def get_product(cls, sku: str) -> Optional[VendorBResponse]:
        """
        Fetch product data from Vendor B.
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            VendorBResponse if product exists, None otherwise
        """
        products = await cls._load_products()
        product_data = products.get(sku)
        
        if not product_data:
            return None
        
        # Determine timestamp
        # Requirement 9: Allow simulation of stale data via JSON
        if "updated_at" in product_data:
            updated_at = product_data["updated_at"]
        else:
            updated_at = datetime.utcnow().isoformat()
        
        return VendorBResponse(
            sku=sku,
            stock_level=product_data["stock"],
            price_usd=product_data["price"],  # String format
            in_stock=product_data["in_stock"],
            updated_at=updated_at
        )


class VendorC:
    """
    Mock Vendor C - Simulates slow responses and intermittent failures.
    Requirement 8:
    - Slow responses (simulated delay)
    - Intermittent failures (random errors)
    - Different field structure
    """
    
    name: str = "VendorC"
    _data_file: str = os.path.join(os.path.dirname(__file__), "vendor_c_products.json")
    _cache: Optional[Dict[str, Dict[str, Any]]] = None
    
    @classmethod
    async def _load_products(cls) -> Dict[str, Dict[str, Any]]:
        """
        Load product data from JSON file asynchronously.
        """
        if cls._cache is not None:
            return cls._cache
        
        async with aiofiles.open(cls._data_file, mode='r') as f:
            content = await f.read()
            cls._cache = json.loads(content)
            return cls._cache
    
    @classmethod
    async def get_product(cls, sku: str) -> Optional[VendorCResponse]:
        """
        Fetch product data from Vendor C with simulated issues.
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            VendorCResponse if product exists, None otherwise
            
        Raises:
            Exception: Randomly raises exception to simulate failure
        """
        # Simulate slow response (0.1 to 2 seconds delay)
        # Requirement 8: Slow responses
        delay = random.uniform(0.1, 2.0)
        await asyncio.sleep(delay)
        
        # Simulate intermittent failure (20% chance)
        # Requirement 8: Intermittent failures
        if random.random() < 0.2:
            raise Exception("Vendor C connection timeout")
            
        products = await cls._load_products()
        product_data = products.get(sku)
        
        if not product_data:
            return None
            
        # Determine timestamp
        # Requirement 9: Allow simulation of stale data via JSON
        if "updated_at" in product_data:
            updated_at = product_data["updated_at"]
        else:
            updated_at = datetime.utcnow().isoformat()
            
        return VendorCResponse(
            id=sku,
            qty=product_data["qty"],
            cost=product_data["cost"],
            available=product_data["available"],
            updated_at=updated_at
        )
