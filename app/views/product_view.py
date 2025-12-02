"""
Product View.
Responsible for formatting the product data for the API response.
"""

from app.models.models import ProductResponse, NormalizedProduct
from typing import Optional

class ProductView:
    """
    View layer for Product resources.
    Handles the transformation of domain models to API response models.
    """

    @staticmethod
    def render(sku: str, product: Optional[NormalizedProduct] = None) -> ProductResponse:
        """
        Render the product response.
        
        Args:
            sku: The requested SKU
            product: The normalized product data (if found/available)
            
        Returns:
            ProductResponse: The formatted API response
        """
        if product is None:
            return ProductResponse(
                sku=sku,
                status="OUT_OF_STOCK"
            )
            
        return ProductResponse(
            sku=sku,
            vendor=product.vendor_name,
            price=product.price,
            stock=product.stock,
            status="AVAILABLE"
        )
