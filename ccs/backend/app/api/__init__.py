from fastapi import APIRouter
from .health import health_router
from .endpoints.small_box_info import router as small_box_info_router
# Add more routers here

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(small_box_info_router)
