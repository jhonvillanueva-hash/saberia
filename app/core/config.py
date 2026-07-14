import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "Saberia API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")


settings = Settings()
