"""
Product routes.
Handles product related endpoints.
"""

from fastapi import APIRouter, Path
from app.models import ProductResponse, ErrorResponse
from app.controllers.product_controller import ProductController
from app.views.product_view import ProductView

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

# Initialize controller
controller = ProductController()


async def get_product(
    sku: str = Path(
        ...,
        description="Product SKU (alphanumeric, 3-20 characters)",
        example="SKU001"
    )
) -> ProductResponse:
    """
    Get product availability and pricing from multiple vendors.
    
    Args:
        sku: Product SKU to fetch
        
    Returns:
        ProductResponse with vendor, price, stock, and status
    """
    # Call Controller to get domain data
    product_data = await controller.get_product(sku)
    
    # Call View to render response
    return ProductView.render(sku, product_data)

router.add_api_route(
    "/{sku}",
    get_product,
    methods=["GET"],
    response_model=ProductResponse,
    responses={
        200: {
            "description": "Product found and available",
            "model": ProductResponse
        },
        400: {
            "description": "Invalid SKU format",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Get product by SKU"
)
