from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.groups import router as groups_router
from app.api.journeys import router as journeys_router
from app.api.users import router as users_router


app = FastAPI(
    title="TRESA API",
    description="Travel Together. Travel Safer.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TRESA API",
    }


# Authentication and user management
app.include_router(auth_router)
app.include_router(users_router)

# Journey management and the existing Matching API
app.include_router(journeys_router)

# Persistent travel group management
app.include_router(groups_router)