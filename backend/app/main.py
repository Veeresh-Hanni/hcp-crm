from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - registers all models with Base.metadata
from app.routers import hcps_router, interactions_router, chat_router

app = FastAPI(title="AI-First CRM — HCP Module", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hcps_router)
app.include_router(interactions_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup():
    # For assignment/demo purposes: create tables if they don't exist.
    # In a real deployment, use Alembic migrations instead (see alembic/ dir).
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
