from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db


# Use lifespan for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(
        "FastAPI application starting up. Database migrations are managed by Alembic."
    )
    yield
    print("FastAPI application shutting down.")


app = FastAPI(
    title="getVolunteer Backend API",
    description="API for connecting volunteers with needs.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def read_root():
    return {"message": "Welcome to getVolunteer Backend API!"}


@app.get("/health")
async def health_check():
    try:
        db: Session = next(get_db())
        db.execute("SELECT 1")
        return {"status": "ok", "database_connection": "successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {e}",
        )
