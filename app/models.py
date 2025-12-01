"""
Data models for the product normalization service.
All models use Pydantic for validation and static typing.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class VendorAResponse(BaseModel):
    """
    Vendor A schema - uses snake_case and specific field names.
    This vendor returns inventory_count as an integer and availability_status as string.
    """
    product_code: str
    inventory_count: Optional[int] = None  # Can be null
    unit_price: float
    availability_status: str  # e.g., "IN_STOCK", "OUT_OF_STOCK"
    last_updated: datetime


class VendorBResponse(BaseModel):
    """
    Vendor B schema - uses different field names and data types.
    This vendor returns stock_level as integer and price as string (needs conversion).
    """
    sku: str
    stock_level: Optional[int] = None  # Can be null
    price_usd: str  # Price as string, needs to be converted to float
    in_stock: bool
    updated_at: str  # ISO string timestamp (Standardized)


class VendorCResponse(BaseModel):
    """
    Vendor C schema - distinct structure for Requirement 8.
    Simulates a legacy system or different provider.
    """
    id: str  # SKU equivalent
    qty: Optional[str] = None  # Quantity as string
    cost: float  # Price
    available: str  # "yes" or "no"
    updated_at: str  # ISO string timestamp


class NormalizedProduct(BaseModel):
    """
    Normalized product data after processing vendor responses.
    This is the internal representation used for business logic.
    """
    sku: str
    vendor_name: str
    price: float
    stock: int
    source_timestamp: datetime  # Requirement 9: Data Freshness
    is_valid: bool = True  # Flag to mark if data is valid after normalization
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        """
        Price validation: Must be numeric and > 0.
        Invalid prices will cause validation error.
        """
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v


class ProductResponse(BaseModel):
    """
    API response model for GET /products/{sku}.
    Returns either available product or out of stock status.
    """
    sku: str
    vendor: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    status: Literal["AVAILABLE", "OUT_OF_STOCK"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
