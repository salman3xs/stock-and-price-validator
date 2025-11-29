"""
Data normalization logic for vendor responses.
Handles stock normalization, price validation, and conversion to unified format.
"""

from typing import Optional, List
from app.models import (
    VendorAResponse, 
    VendorBResponse, 
    NormalizedProduct
)
import logging

logger = logging.getLogger(__name__)


class ProductNormalizer:
    """
    Normalizes product data from different vendor schemas into a unified format.
    Implements business rules for stock and price normalization.
    """
    
    @staticmethod
    def normalize_vendor_a(response: VendorAResponse) -> Optional[NormalizedProduct]:
        """
        Normalize Vendor A response.
        
        Business Rules:
        - Stock Normalization: If inventory = null AND status = "IN_STOCK" → stock = 5
        - Otherwise: stock = 0 if inventory is null or 0
        - Price Validation: Must be numeric and > 0
        
        Args:
            response: Raw response from Vendor A
            
        Returns:
            NormalizedProduct if valid, None if price is invalid
        """
        try:
            # Stock normalization logic
            if response.inventory_count is None:
                # If inventory is null, check status
                if response.availability_status == "IN_STOCK":
                    stock = 5  # Assume stock = 5 as per business rule
                    logger.info(
                        f"VendorA: {response.product_code} - null inventory with IN_STOCK status, assuming stock=5"
                    )
                else:
                    stock = 0
                    logger.info(
                        f"VendorA: {response.product_code} - null inventory with non-IN_STOCK status, stock=0"
                    )
            else:
                stock = max(0, response.inventory_count)  # Ensure non-negative
            
            # Price validation - Pydantic model will validate price > 0
            # If price is invalid, this will raise ValueError
            normalized = NormalizedProduct(
                sku=response.product_code,
                vendor_name="VendorA",
                price=response.unit_price,
                stock=stock
            )
            
            logger.info(
                f"VendorA: Successfully normalized {response.product_code} - "
                f"price={normalized.price}, stock={normalized.stock}"
            )
            return normalized
            
        except ValueError as e:
            # Price validation failed
            logger.warning(
                f"VendorA: Invalid price for {response.product_code}: {response.unit_price} - {str(e)}"
            )
            return None
    
    @staticmethod
    def normalize_vendor_b(response: VendorBResponse) -> Optional[NormalizedProduct]:
        """
        Normalize Vendor B response.
        
        Business Rules:
        - Stock Normalization: If stock_level = null AND in_stock = true → stock = 5
        - Price Conversion: Convert string price to float
        - Price Validation: Must be numeric and > 0
        
        Args:
            response: Raw response from Vendor B
            
        Returns:
            NormalizedProduct if valid, None if price is invalid
        """
        try:
            # Stock normalization logic
            if response.stock_level is None:
                # If stock is null, check in_stock flag
                if response.in_stock:
                    stock = 5  # Assume stock = 5 as per business rule
                    logger.info(
                        f"VendorB: {response.sku} - null stock_level with in_stock=true, assuming stock=5"
                    )
                else:
                    stock = 0
                    logger.info(
                        f"VendorB: {response.sku} - null stock_level with in_stock=false, stock=0"
                    )
            else:
                stock = max(0, response.stock_level)  # Ensure non-negative
            
            # Convert string price to float
            # Assumption: Price string is in valid decimal format (e.g., "99.99")
            try:
                price = float(response.price_usd)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"VendorB: Cannot convert price to float for {response.sku}: {response.price_usd}"
                )
                return None
            
            # Price validation - Pydantic model will validate price > 0
            normalized = NormalizedProduct(
                sku=response.sku,
                vendor_name="VendorB",
                price=price,
                stock=stock
            )
            
            logger.info(
                f"VendorB: Successfully normalized {response.sku} - "
                f"price={normalized.price}, stock={normalized.stock}"
            )
            return normalized
            
        except ValueError as e:
            # Price validation failed
            logger.warning(
                f"VendorB: Invalid data for {response.sku} - {str(e)}"
            )
            return None
    
    @classmethod
    def select_best_vendor(cls, products: List[NormalizedProduct]) -> Optional[NormalizedProduct]:
        """
        Select the best vendor based on business rules.
        
        Business Rules:
        - Vendor with stock > 0 and lowest price wins
        - If all vendors are out of stock, return None
        
        Args:
            products: List of normalized products from different vendors
            
        Returns:
            Best product or None if all out of stock
        """
        # Filter products with stock > 0
        in_stock_products = [p for p in products if p.stock > 0]
        
        if not in_stock_products:
            logger.info("All vendors are out of stock")
            return None
        
        # Select product with lowest price
        best_product = min(in_stock_products, key=lambda p: p.price)
        
        logger.info(
            f"Best vendor selected: {best_product.vendor_name} - "
            f"SKU={best_product.sku}, price={best_product.price}, stock={best_product.stock}"
        )
        
        return best_product
