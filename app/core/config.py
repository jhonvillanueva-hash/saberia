import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "Saberia API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT Configuration
    _jwt_secret_key: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")

    # Cloudflare R2 Configuration
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "")
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "")

    def __init__(self):
        if not self._jwt_secret_key or self._jwt_secret_key.strip() == "":
            raise ValueError(
                "JWT_SECRET_KEY environment variable is not set. "
                "Please set a secure secret key for JWT token signing."
            )
        self.JWT_SECRET_KEY = self._jwt_secret_key


settings = Settings()
