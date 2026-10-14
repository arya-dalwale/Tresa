from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.users import router as users_router


app = FastAPI(
    title="TRESA API",
    description="Travel Together. Travel Safer.",
    version="0.1.0",
)


app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TRESA API",
    }