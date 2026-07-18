from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.modules.users.models import UserMonthlyLimit


class MonthlyLimitExceededError(Exception):
    """Exception raised when user exceeds monthly conversion limit."""
    pass


def get_or_create_monthly_limit(db: Session, user_id: UUID, year: int, month: int) -> UserMonthlyLimit:
    """
    Get or create UserMonthlyLimit for a user/year/month with SELECT FOR UPDATE.

    Uses FOR UPDATE to prevent race conditions when multiple requests try to
    create the limit row simultaneously.
    """
    # Try to get existing limit with FOR UPDATE
    limit_row = db.query(UserMonthlyLimit).\
        filter(
            UserMonthlyLimit.user_id == user_id,
            UserMonthlyLimit.year == year,
            UserMonthlyLimit.month == month
        ).\
        with_for_update().\
        first()

    if limit_row:
        return limit_row

    # Create new limit row if it doesn't exist
    try:
        limit_row = UserMonthlyLimit(
            user_id=user_id,
            year=year,
            month=month,
            conversions_used=0,
            conversions_limit=3
        )
        db.add(limit_row)
        db.flush()  # Make it visible in the same transaction
        return limit_row
    except IntegrityError:
        # Another transaction created the row first - retry SELECT FOR UPDATE
        db.rollback()
        # After rollback, retry the SELECT FOR UPDATE
        return db.query(UserMonthlyLimit).\
            filter(
                UserMonthlyLimit.user_id == user_id,
                UserMonthlyLimit.year == year,
                UserMonthlyLimit.month == month
            ).\
            with_for_update().\
            first()


def consume_conversion_slot(db: Session, user_id: UUID) -> UserMonthlyLimit:
    """
    Consume one conversion slot for the current month.

    Raises MonthlyLimitExceededError if limit is reached.
    """
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    # Get or create limit with FOR UPDATE to prevent race conditions
    limit_row = get_or_create_monthly_limit(db, user_id, year, month)

    # Check if limit is exceeded
    if limit_row.conversions_used >= limit_row.conversions_limit:
        raise MonthlyLimitExceededError(
            f"Monthly conversion limit of {limit_row.conversions_limit} reached"
        )

    # Increment used count
    limit_row.conversions_used += 1
    db.commit()

    return limit_row