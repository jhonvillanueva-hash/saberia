import pytest
import uuid
import threading
from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.modules.users.models import User, UserMonthlyLimit
from app.modules.users.service import get_or_create_monthly_limit, consume_conversion_slot, MonthlyLimitExceededError
from app.modules.auth.security import create_access_token


def test_get_monthly_limits_unauthorized(client):
    """Test /users/me/limits without authentication."""
    response = client.get("/users/me/limits")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_monthly_limits_first_time(client: Session, test_db: Session):
    """Test /users/me/limits creates limit row automatically for new user."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="limits@example.com",
        display_name="Limits User",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    test_db.commit()

    # Generate token
    access_token = create_access_token(user.id)

    # Call endpoint
    response = client.get(
        "/users/me/limits",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["year"] == datetime.now(timezone.utc).year
    assert data["month"] == datetime.now(timezone.utc).month
    assert data["conversions_used"] == 0
    assert data["conversions_limit"] == 3
    assert data["remaining"] == 3

    # Verify only one row was created
    limit_rows = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        all()
    assert len(limit_rows) == 1
    assert limit_rows[0].conversions_used == 0
    assert limit_rows[0].conversions_limit == 3


def test_get_monthly_limits_reuse_existing(client: Session, test_db: Session):
    # Create user with existing limit
    user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        display_name="Existing User",
        is_active=True
    )
    test_db.add(user)

    now = datetime.now(timezone.utc)
    limit_row = UserMonthlyLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        year=now.year,
        month=now.month,
        conversions_used=1,
        conversions_limit=3
    )
    test_db.add(limit_row)
    test_db.commit()

    # Generate token
    access_token = create_access_token(user.id)

    # Call endpoint twice
    response1 = client.get(
        "/users/me/limits",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    response2 = client.get(
        "/users/me/limits",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK

    # Verify only one row exists
    limit_rows = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        all()
    assert len(limit_rows) == 1
    assert limit_rows[0].conversions_used == 1


def test_get_monthly_limits_persistence_with_fresh_session(client: Session):
    # Create user without existing limit
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="freshsession@example.com",
        display_name="Fresh Session User",
        is_active=True
    )
    from tests.conftest import TestingSessionLocal
    fresh_session = TestingSessionLocal()
    try:
        fresh_session.add(user)
        fresh_session.commit()
    finally:
        fresh_session.close()

    # Generate token
    access_token = create_access_token(user_id)

    # Call endpoint to create limit row
    response = client.get(
        "/users/me/limits",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_200_OK

    # Verify persistence with a completely fresh session (simulates production behavior)
    fresh_session = TestingSessionLocal()
    try:
        limit_row = fresh_session.query(UserMonthlyLimit).\
            filter(UserMonthlyLimit.user_id == user_id).\
            first()
        assert limit_row is not None
        assert limit_row.conversions_used == 0
        assert limit_row.conversions_limit == 3
    finally:
        fresh_session.close()


def test_consume_conversion_slot_success(test_db: Session):
    """Test consume_conversion_slot increments count correctly."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="consume@example.com",
        display_name="Consume User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Consume 3 slots
    for i in range(3):
        limit_row = consume_conversion_slot(test_db, user.id)
        assert limit_row.conversions_used == i + 1

    # Verify final state
    final_row = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        first()
    assert final_row.conversions_used == 3


def test_consume_conversion_slot_exceeds_limit(test_db: Session):
    """Test consume_conversion_slot raises error when limit exceeded."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="exceed@example.com",
        display_name="Exceed User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Consume all 3 slots
    for i in range(3):
        consume_conversion_slot(test_db, user.id)

    # Try to consume one more
    with pytest.raises(MonthlyLimitExceededError):
        consume_conversion_slot(test_db, user.id)

    # Verify count didn't exceed limit
    final_row = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        first()
    assert final_row.conversions_used == 3


def test_concurrent_consumption(test_db: Session):
    """Test concurrent consumption with race condition prevention."""
    # Create user with limit of 1 conversion
    user = User(
        id=uuid.uuid4(),
        email="concurrent@example.com",
        display_name="Concurrent User",
        is_active=True
    )
    test_db.add(user)

    # Create limit with conversions_limit=1
    now = datetime.now(timezone.utc)
    limit_row = UserMonthlyLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        year=now.year,
        month=now.month,
        conversions_used=0,
        conversions_limit=1  # Only 1 slot available
    )
    test_db.add(limit_row)
    test_db.commit()

    # Track results
    results = []
    errors = []

    def consume_slot():
        try:
            # Each thread gets its own session from the test engine
            from tests.conftest import TestingSessionLocal
            db = TestingSessionLocal()
            try:
                limit = consume_conversion_slot(db, user.id)
                results.append(limit.conversions_used)
            finally:
                db.close()
        except MonthlyLimitExceededError as e:
            errors.append(str(e))

    # Create barrier to synchronize thread start
    barrier = threading.Barrier(2)

    def thread_target():
        barrier.wait()  # Wait for both threads to be ready
        consume_slot()

    # Start two threads
    threads = [
        threading.Thread(target=thread_target),
        threading.Thread(target=thread_target)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly one should succeed, one should fail
    assert len(results) == 1
    assert len(errors) == 1
    assert results[0] == 1  # Only one slot consumed

    # Verify final state
    final_row = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        first()
    assert final_row.conversions_used == 1  # Did not exceed limit


def test_concurrent_creation_and_consumption(test_db: Session):
    # Create user WITHOUT existing limit (this is the key difference)
    user = User(
        id=uuid.uuid4(),
        email="concurrent_creation@example.com",
        display_name="Concurrent Creation User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Track results
    results = []

    def consume_slot():
        try:
            # Each thread gets its own session from the test engine
            from tests.conftest import TestingSessionLocal
            db = TestingSessionLocal()
            try:
                limit = consume_conversion_slot(db, user.id)
                results.append(limit.conversions_used)
            finally:
                db.close()
        except MonthlyLimitExceededError as e:
            results.append(f"error: {str(e)}")

    # Create barrier to synchronize thread start
    barrier = threading.Barrier(2)

    def thread_target():
        barrier.wait()  # Wait for both threads to be ready
        consume_slot()

    # Start two threads
    threads = [
        threading.Thread(target=thread_target),
        threading.Thread(target=thread_target)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Both should succeed (limit is 3, only consuming 2)
    assert len(results) == 2
    assert all(isinstance(r, int) for r in results)
    assert sum(results) == 3  # 1 + 2 = 3 total consumed

    # Verify only one row was created (no duplicate rows)
    limit_rows = test_db.query(UserMonthlyLimit).\
        filter(UserMonthlyLimit.user_id == user.id).\
        all()
    assert len(limit_rows) == 1
    assert limit_rows[0].conversions_used == 2  # Consistent final state