# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints import auth, needs, volunteers


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI application starting up. Database migrations are managed by Alembic.")
    yield
    print("FastAPI application shutting down.")


app = FastAPI(
    title="getVolunteer Backend API",
    description="API for connecting volunteers with needs.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(volunteers.router, prefix="/api/v1")
app.include_router(needs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
