from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.users.schemas import MonthlyUsageResponse
from app.modules.users.service import get_or_create_monthly_limit
from app.modules.auth.dependencies import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/limits", response_model=MonthlyUsageResponse)
def get_monthly_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's monthly conversion limits."""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    # Get or create limit (without consuming a slot)
    limit_row = get_or_create_monthly_limit(db, current_user.id, year, month)

    return MonthlyUsageResponse(
        year=limit_row.year,
        month=limit_row.month,
        conversions_used=limit_row.conversions_used,
        conversions_limit=limit_row.conversions_limit,
        remaining=limit_row.conversions_limit - limit_row.conversions_used
    )