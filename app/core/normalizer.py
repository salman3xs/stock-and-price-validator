"""
Data normalization logic for vendor responses.
Handles stock normalization, price validation, and conversion to unified format.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from app.models.models import (
    VendorAResponse, 
    VendorBResponse, 
    VendorCResponse,
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
    def _is_fresh(timestamp: datetime) -> bool:
        """
        Check if data is fresh (not older than 10 minutes).
        Requirement 9: Data Freshness Rule
        """
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        is_fresh = timestamp >= cutoff
        if not is_fresh:
            logger.warning(f"Data is stale! Timestamp: {timestamp}, Cutoff: {cutoff}")
        return is_fresh
    
    @classmethod
    def normalize_vendor_a(cls, response: VendorAResponse) -> Optional[NormalizedProduct]:
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
            # Requirement 9: Data Freshness
            if not cls._is_fresh(response.last_updated):
                logger.warning(f"VendorA: Stale data for {response.product_code}, discarding.")
                return None

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
                stock=stock,
                source_timestamp=response.last_updated
            )
            
            logger.info(f"VendorA: Successfully normalized {response.product_code}")
            return normalized
            
        except ValueError as e:
            logger.warning(f"VendorA: Invalid price for {response.product_code}: {response.unit_price} - {str(e)}")
            return None
    
    @classmethod
    def normalize_vendor_b(cls, response: VendorBResponse) -> Optional[NormalizedProduct]:
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
            # Convert timestamp (Standardized ISO string)
            timestamp = datetime.fromisoformat(response.updated_at)
            
            # Requirement 9: Data Freshness
            if not cls._is_fresh(timestamp):
                logger.warning(f"VendorB: Stale data for {response.sku}, discarding.")
                return None

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
            except (ValueError, TypeError):
                logger.warning(f"VendorB: Cannot convert price to float for {response.sku}: {response.price_usd}")
                return None
            
            # Price validation - Pydantic model will validate price > 0
            normalized = NormalizedProduct(
                sku=response.sku,
                vendor_name="VendorB",
                price=price,
                stock=stock,
                source_timestamp=timestamp
            )
            
            logger.info(
                f"VendorB: Successfully normalized {response.sku} - "
                f"price={normalized.price}, stock={normalized.stock}"
            )
            return normalized
            
        except ValueError as e:
            logger.warning(f"VendorB: Invalid data for {response.sku} - {str(e)}")
            return None

    @classmethod
    def normalize_vendor_c(cls, response: VendorCResponse) -> Optional[NormalizedProduct]:
        """
        Normalize Vendor C response.
        
        Business Rules:
        - Stock Normalization: 
          - Convert qty string to int. If invalid/null, use 0.
          - If available="no", stock = 0 regardless of qty.
          - If qty is null/0 but available="yes", stock = 5 (consistent with other vendors).
        - Price Validation: Must be numeric and > 0
        
        Args:
            response: Raw response from Vendor C
            
        Returns:
            NormalizedProduct if valid, None if price is invalid
        """
        try:
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(response.updated_at)
            except ValueError:
                logger.warning(f"VendorC: Invalid timestamp format for {response.id}: {response.updated_at}")
                return None
                
            # Requirement 9: Data Freshness
            if not cls._is_fresh(timestamp):
                logger.warning(f"VendorC: Stale data for {response.id}, discarding.")
                return None

            # Stock normalization logic
            stock = 0
            
            # Parse quantity string
            try:
                if response.qty:
                    stock = int(response.qty)
            except (ValueError, TypeError):
                logger.warning(f"VendorC: Invalid quantity format for {response.id}: {response.qty}")
                stock = 0
            
            # Apply availability logic
            if response.available.lower() == "no":
                stock = 0
                logger.info(f"VendorC: {response.id} - available='no', setting stock=0")
            elif stock == 0 and response.available.lower() == "yes":
                stock = 5
                logger.info(f"VendorC: {response.id} - qty=0/null with available='yes', assuming stock=5")
            
            # Price validation
            normalized = NormalizedProduct(
                sku=response.id,
                vendor_name="VendorC",
                price=response.cost,
                stock=stock,
                source_timestamp=timestamp
            )
            
            logger.info(f"VendorC: Successfully normalized {response.id}")
            return normalized
            
        except ValueError as e:
            logger.warning(f"VendorC: Invalid data for {response.id} - {str(e)}")
            return None
    
    @classmethod
    def select_best_vendor(cls, products: List[NormalizedProduct]) -> Optional[NormalizedProduct]:
        """
        Select the best vendor based on business rules.
        
        Business Rules (Requirement 10):
        - Filter products with stock > 0
        - If price difference > 10%: Choose vendor with higher stock
        - Otherwise: Choose vendor with lowest price
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
        
        # If only one vendor has stock, return it
        if len(in_stock_products) == 1:
            best_product = in_stock_products[0]
            logger.info(
                f"Only one vendor in stock: {best_product.vendor_name} - "
                f"SKU={best_product.sku}, price={best_product.price}, stock={best_product.stock}"
            )
            return best_product
        
        # Find min and max prices
        min_price = min(p.price for p in in_stock_products)
        max_price = max(p.price for p in in_stock_products)
        
        # Calculate price difference percentage
        price_diff_percentage = ((max_price - min_price) / min_price) * 100
        
        # Requirement 10: If price difference > 10%, choose vendor with higher stock
        if price_diff_percentage > 10:
            best_product = max(in_stock_products, key=lambda p: p.stock)
            logger.info(
                f"Price difference {price_diff_percentage:.2f}% > 10%, selecting vendor with highest stock: "
                f"{best_product.vendor_name} - SKU={best_product.sku}, price={best_product.price}, stock={best_product.stock}"
            )
        else:
            # Otherwise, select product with lowest price
            best_product = min(in_stock_products, key=lambda p: p.price)
            logger.info(
                f"Price difference {price_diff_percentage:.2f}% <= 10%, selecting vendor with lowest price: "
                f"{best_product.vendor_name} - SKU={best_product.sku}, price={best_product.price}, stock={best_product.stock}"
            )
        
        return best_product

