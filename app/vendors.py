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
from app.models import VendorAResponse, VendorBResponse


class VendorA:
    """
    Mock Vendor A - Fast and reliable vendor.
    Returns data in format: product_code, inventory_count, unit_price, availability_status
    """
    
    name: str = "VendorA"
    _data_file: str = os.path.join(os.path.dirname(__file__), "data", "vendor_a_products.json")
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
        
        return VendorAResponse(
            product_code=sku,
            inventory_count=product_data["inventory"],
            unit_price=product_data["price"],
            availability_status=product_data["status"],
            last_updated=datetime.utcnow()
        )


class VendorB:
    """
    Mock Vendor B - Different schema and data types.
    Returns data in format: sku, stock_level, price_usd (as string), in_stock (boolean)
    """
    
    name: str = "VendorB"
    _data_file: str = os.path.join(os.path.dirname(__file__), "data", "vendor_b_products.json")
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
        
        return VendorBResponse(
            sku=sku,
            stock_level=product_data["stock"],
            price_usd=product_data["price"],  # String format
            in_stock=product_data["in_stock"],
            data_timestamp=int(datetime.utcnow().timestamp())
        )
