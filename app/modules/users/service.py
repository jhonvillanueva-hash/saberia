from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.modules.users.models import UserMonthlyLimit


class MonthlyLimitExceededError(Exception):
    pass


def get_or_create_monthly_limit(db: Session, user_id: UUID, year: int, month: int) -> UserMonthlyLimit:
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

    try:
        limit_row = UserMonthlyLimit(
            user_id=user_id,
            year=year,
            month=month,
            conversions_used=0,
            conversions_limit=3
        )
        db.add(limit_row)
        db.flush()
        return limit_row
    except IntegrityError:
        db.rollback()
        return db.query(UserMonthlyLimit).\
            filter(
                UserMonthlyLimit.user_id == user_id,
                UserMonthlyLimit.year == year,
                UserMonthlyLimit.month == month
            ).\
            with_for_update().\
            first()


def consume_conversion_slot(db: Session, user_id: UUID) -> UserMonthlyLimit:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    limit_row = get_or_create_monthly_limit(db, user_id, year, month)

    if limit_row.conversions_used >= limit_row.conversions_limit:
        raise MonthlyLimitExceededError(
            f"Monthly conversion limit of {limit_row.conversions_limit} reached"
        )

    limit_row.conversions_used += 1
    db.commit()

    return limit_row


def get_current_year_month():
    now = datetime.now(timezone.utc)
    return now.year, now.month