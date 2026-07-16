from datetime import datetime
from uuid import uuid4
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.database import get_db
from app.core.config import settings
from app.modules.users.models import User
from app.modules.auth.models import AuthProvider
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    TokenResponse,
    UserProfile
)
from app.modules.auth.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.modules.auth.dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user with email and password."""
    # Check if email already exists
    existing_provider = db.query(AuthProvider).\
        filter(AuthProvider.provider_email == register_data.email).\
        first()

    if existing_provider:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create user
    user = User(
        id=uuid4(),
        email=register_data.email,
        display_name=register_data.display_name,
        is_active=True,
        created_at=datetime.now()
    )
    db.add(user)

    # Create auth provider
    auth_provider = AuthProvider(
        id=uuid4(),
        user_id=user.id,
        provider="email",
        provider_email=register_data.email,
        password_hash=hash_password(register_data.password),
        is_verified=False
    )
    db.add(auth_provider)

    # Commit transaction
    db.commit()

    # Generate access token
    access_token = create_access_token(user.id)

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with email and password."""
    # Find auth provider
    auth_provider = db.query(AuthProvider).\
        filter(
            AuthProvider.provider == "email",
            AuthProvider.provider_email == login_data.email
        ).\
        first()

    # Check if provider exists and password is correct
    if not auth_provider or not verify_password(login_data.password, auth_provider.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate access token
    access_token = create_access_token(auth_provider.user_id)

    return TokenResponse(access_token=access_token)


@router.post("/login/google", response_model=TokenResponse)
def login_google(
    google_data: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    """Login with Google OAuth."""
    try:
        # Verify Google token
        id_info = id_token.verify_oauth2_token(
            google_data.id_token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        # Check if required fields are present
        if "sub" not in id_info or "email" not in id_info:
            raise ValueError("Invalid Google token payload")

        google_sub = id_info["sub"]
        google_email = id_info["email"]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )

    # Check if Google account already exists
    existing_google_provider = db.query(AuthProvider).\
        filter(
            AuthProvider.provider == "google",
            AuthProvider.provider_user_id == google_sub
        ).\
        first()

    if existing_google_provider:
        # User already exists, just login
        access_token = create_access_token(existing_google_provider.user_id)
        return TokenResponse(access_token=access_token)

    # Check if email is already in use by any provider
    existing_email_provider = db.query(AuthProvider).\
        filter(AuthProvider.provider_email == google_email).\
        first()

    if existing_email_provider:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered with another provider"
        )

    # Create new user
    user = User(
        id=uuid4(),
        email=google_email,
        display_name=id_info.get("name", google_email.split("@")[0]),
        is_active=True,
        created_at=datetime.now()
    )
    db.add(user)

    # Create Google auth provider
    auth_provider = AuthProvider(
        id=uuid4(),
        user_id=user.id,
        provider="google",
        provider_user_id=google_sub,
        provider_email=google_email,
        is_verified=True  # Google already verified the email
    )
    db.add(auth_provider)

    # Commit transaction
    db.commit()

    # Generate access token
    access_token = create_access_token(user.id)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get the current authenticated user's profile."""
    return current_user