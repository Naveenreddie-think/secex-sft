from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import engine, Base, get_db
from app.config import settings
from app.routers import review, extract


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SecEx-SFT API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://secex-frontend.onrender.com",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(review.router)
app.include_router(extract.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}