import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import jwt

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.users.models import User
from app.modules.auth.models import AuthProvider
from app.modules.auth.security import hash_password, create_access_token, TokenExpiredError
from app.modules.auth.schemas import TokenResponse


def test_register_successful(client: Session, test_db: Session):
    """Test successful user registration."""
    register_data = {
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User"
    }

    response = client.post("/auth/register", json=register_data)

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

    # Verify user and auth provider were created
    user = test_db.query(User).filter(User.email == register_data["email"]).first()
    assert user is not None
    assert user.display_name == register_data["display_name"]

    auth_provider = test_db.query(AuthProvider).filter(
        AuthProvider.user_id == user.id,
        AuthProvider.provider == "email"
    ).first()
    assert auth_provider is not None
    assert auth_provider.provider_email == register_data["email"]

    # Verify password hash is not plain text
    assert auth_provider.password_hash != register_data["password"]
    assert auth_provider.password_hash.startswith("$2b$")  # bcrypt hash format


def test_register_duplicate_email(client: Session, test_db: Session):
    """Test registration with duplicate email."""
    # Create existing user
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        display_name="Existing User",
        is_active=True
    )
    test_db.add(existing_user)

    existing_auth = AuthProvider(
        id=uuid.uuid4(),
        user_id=existing_user.id,
        provider="email",
        provider_email="existing@example.com",
        password_hash=hash_password("password"),
        is_verified=False
    )
    test_db.add(existing_auth)
    test_db.commit()

    # Try to register with same email
    register_data = {
        "email": "existing@example.com",
        "password": "password123",
        "display_name": "New User"
    }

    response = client.post("/auth/register", json=register_data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"]


def test_login_successful(client: Session, test_db: Session):
    """Test successful login."""
    # Create user
    password = "password123"
    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        display_name="Login User",
        is_active=True
    )
    test_db.add(user)

    auth_provider = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="email",
        provider_email="login@example.com",
        password_hash=hash_password(password),
        is_verified=False
    )
    test_db.add(auth_provider)
    test_db.commit()

    # Login
    login_data = {
        "email": "login@example.com",
        "password": password
    }

    response = client.post("/auth/login", json=login_data)

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

    # Verify token is valid
    token = response.json()["access_token"]
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == str(user.id)


def test_login_invalid_credentials(client: Session, test_db: Session):
    """Test login with invalid credentials."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        display_name="Login User",
        is_active=True
    )
    test_db.add(user)

    auth_provider = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="email",
        provider_email="login@example.com",
        password_hash=hash_password("correctpassword"),
        is_verified=False
    )
    test_db.add(auth_provider)
    test_db.commit()

    # Try login with wrong password
    login_data = {
        "email": "login@example.com",
        "password": "wrongpassword"
    }

    response = client.post("/auth/login", json=login_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]

    # Try login with non-existent email
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password"
    }

    response = client.post("/auth/login", json=login_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me_unauthorized(client):
    """Test /me endpoint without authentication."""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_with_valid_token(client: Session, test_db: Session):
    """Test /me endpoint with valid token."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="me@example.com",
        display_name="Me User",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    test_db.commit()

    # Generate token
    access_token = create_access_token(user.id)

    # Call /me with token
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert response.json()["display_name"] == user.display_name


def test_get_me_with_expired_token(client: Session, test_db: Session):
    """Test /me endpoint with expired token."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="expired@example.com",
        display_name="Expired User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Generate expired token
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Call /me with expired token
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in response.json()["detail"]


def test_get_me_with_invalid_token(client: Session):
    """Test /me endpoint with invalid token."""
    # Call /me with invalid token
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token" in response.json()["detail"]


def test_google_login_new_user(client: Session, test_db: Session):
    """Test Google login for new user."""
    google_token_data = {
        "sub": "123456789",
        "email": "google@example.com",
        "name": "Google User"
    }

    with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = google_token_data

        response = client.post(
            "/auth/login/google",
            json={"id_token": "fake-google-token"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

    # Verify user and auth provider were created
    user = test_db.query(User).filter(User.email == google_token_data["email"]).first()
    assert user is not None
    assert user.display_name == google_token_data["name"]

    auth_provider = test_db.query(AuthProvider).filter(
        AuthProvider.user_id == user.id,
        AuthProvider.provider == "google"
    ).first()
    assert auth_provider is not None
    assert auth_provider.provider_user_id == google_token_data["sub"]
    assert auth_provider.is_verified is True


def test_google_login_existing_user(client: Session, test_db: Session):
    """Test Google login for existing user."""
    # Create existing Google user
    user = User(
        id=uuid.uuid4(),
        email="google@example.com",
        display_name="Google User",
        is_active=True
    )
    test_db.add(user)

    auth_provider = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="google",
        provider_user_id="123456789",
        provider_email="google@example.com",
        is_verified=True
    )
    test_db.add(auth_provider)
    test_db.commit()

    google_token_data = {
        "sub": "123456789",
        "email": "google@example.com",
        "name": "Google User"
    }

    with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = google_token_data

        response = client.post(
            "/auth/login/google",
            json={"id_token": "fake-google-token"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

    # Verify token is for the existing user
    token = response.json()["access_token"]
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == str(user.id)


def test_google_login_email_in_use(client: Session, test_db: Session):
    """Test Google login with email already in use by another provider."""
    # Create existing email user
    user = User(
        id=uuid.uuid4(),
        email="google@example.com",
        display_name="Email User",
        is_active=True
    )
    test_db.add(user)

    auth_provider = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="email",
        provider_email="google@example.com",
        password_hash=hash_password("password"),
        is_verified=False
    )
    test_db.add(auth_provider)
    test_db.commit()

    google_token_data = {
        "sub": "123456789",
        "email": "google@example.com",
        "name": "Google User"
    }

    with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = google_token_data

        response = client.post(
            "/auth/login/google",
            json={"id_token": "fake-google-token"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "another provider" in response.json()["detail"]

    # Verify no new user was created
    google_user = test_db.query(User).filter(
        User.email == google_token_data["email"],
        User.id != user.id
    ).first()
    assert google_user is None