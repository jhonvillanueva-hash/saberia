from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import SessionLocal

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT current_database();"))
        db_name = result.scalar()
        db.close()
        return {"status": "healthy", "database": db_name}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
