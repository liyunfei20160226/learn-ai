from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

health_router = APIRouter()

@health_router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """Check API and database health"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "ok",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": str(e)
        }
