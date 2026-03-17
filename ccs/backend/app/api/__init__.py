from fastapi import APIRouter
from .health import health_router
# Add more routers here

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
