from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.include_router(health_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": "Saberia API funcionando"}
