from fastapi import FastAPI

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