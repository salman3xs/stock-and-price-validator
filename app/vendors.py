"""
Mock vendor implementations.
Since real vendor APIs are not provided, we simulate them with mock data.

Assumption: Each vendor has different response schemas and data structures
to demonstrate normalization capabilities.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import random
from app.models import VendorAResponse, VendorBResponse


class VendorA:
    """
    Mock Vendor A - Fast and reliable vendor.
    Returns data in format: product_code, inventory_count, unit_price, availability_status
    """
    
    name: str = "VendorA"
    
    # Mock database of products
    # Assumption: We maintain a small set of SKUs for demonstration
    _products: Dict[str, Dict[str, Any]] = {
        "SKU001": {"inventory": 15, "price": 99.99, "status": "IN_STOCK"},
        "SKU002": {"inventory": None, "price": 149.99, "status": "IN_STOCK"},  # null inventory but IN_STOCK
        "SKU003": {"inventory": 0, "price": 79.99, "status": "OUT_OF_STOCK"},
        "SKU004": {"inventory": 25, "price": 199.99, "status": "IN_STOCK"},
        "SKU005": {"inventory": None, "price": 89.99, "status": "OUT_OF_STOCK"},  # null inventory and OUT_OF_STOCK
    }
    
    @classmethod
    async def get_product(cls, sku: str) -> Optional[VendorAResponse]:
        """
        Fetch product data from Vendor A.
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            VendorAResponse if product exists, None otherwise
        """
        product_data = cls._products.get(sku)
        
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
    
    # Mock database with different pricing and stock levels
    # Assumption: Vendor B has overlapping SKUs but different prices/stock
    _products: Dict[str, Dict[str, Any]] = {
        "SKU001": {"stock": 20, "price": "95.50", "in_stock": True},  # Lower price than Vendor A
        "SKU002": {"stock": 10, "price": "155.00", "in_stock": True},
        "SKU003": {"stock": None, "price": "75.99", "in_stock": True},  # null stock but in_stock=true
        "SKU004": {"stock": 0, "price": "189.99", "in_stock": False},
        "SKU006": {"stock": 30, "price": "129.99", "in_stock": True},  # Unique to Vendor B
    }
    
    @classmethod
    async def get_product(cls, sku: str) -> Optional[VendorBResponse]:
        """
        Fetch product data from Vendor B.
        
        Args:
            sku: Product SKU to fetch
            
        Returns:
            VendorBResponse if product exists, None otherwise
        """
        product_data = cls._products.get(sku)
        
        if not product_data:
            return None
        
        return VendorBResponse(
            sku=sku,
            stock_level=product_data["stock"],
            price_usd=product_data["price"],  # String format
            in_stock=product_data["in_stock"],
            data_timestamp=int(datetime.utcnow().timestamp())
        )


# Vendor registry for easy access
VENDORS = {
    "VendorA": VendorA,
    "VendorB": VendorB,
}
