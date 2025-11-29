"""
Product Controller.
Orchestrates the flow between the router, service, and view.
"""

from fastapi import HTTPException
import logging
import re
from app.service import ProductService
from app.models import NormalizedProduct
from typing import Optional

logger = logging.getLogger(__name__)

class ProductController:
    """
    Controller for Product related operations.
    """
    
    def __init__(self):
        self.service = ProductService()
    
    def _validate_sku(self, sku: str) -> bool:
        """
        Validate SKU format.
        
        Requirements:
        - Must be alphanumeric (letters and numbers only)
        - Length: 3-20 characters
        
        Args:
            sku: SKU string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Alphanumeric check with length constraint
        pattern = r'^[A-Za-z0-9]{3,20}$'
        return bool(re.match(pattern, sku))

    async def get_product(self, sku: str) -> Optional[NormalizedProduct]:
        """
        Handle get product request.
        
        Args:
            sku: Product SKU
            
        Returns:
            NormalizedProduct: The product domain model (or None if out of stock)
            
        Raises:
            HTTPException: If validation fails or internal error occurs
        """
        # 1. Input Validation
        if not self._validate_sku(sku):
            logger.warning(f"Invalid SKU format: {sku}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid SKU format",
                    "detail": "SKU must be alphanumeric and 3-20 characters long",
                    "received": sku
                }
            )
        
        try:
            logger.info(f"Processing request for SKU: {sku}")
            
            # 2. Call Service (Business Logic)
            product = await self.service.get_product(sku)
            
            logger.info(f"Successfully retrieved product data for SKU: {sku}")
            return product
            
        except Exception as e:
            logger.error(f"Error processing SKU {sku}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "detail": str(e)
                }
            )
