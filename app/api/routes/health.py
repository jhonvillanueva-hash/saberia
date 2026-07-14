from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db = Depends(get_db)):
    try:
        result = db.execute(text("SELECT current_database();"))
        db_name = result.scalar()
        return {"status": "healthy", "database": db_name}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
