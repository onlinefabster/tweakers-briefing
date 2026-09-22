"""Tweakers briefing rating dashboard — FastAPI app.

Serves:
  GET  /api/topics            flat list of all topics (frontend groups by day)
  GET  /api/topics?day=YYYY-MM-DD   topics for one day
  PUT  /api/topics/{id}/rating  {"rating": "interesting|neutral|not_interested"}
  GET  /                       single-page dashboard
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db

app = FastAPI(title="Tweakers Briefing Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"


class RatingIn(BaseModel):
    rating: str = Field(pattern="^(interesting|neutral|not_interested)$")


@app.on_event("startup")
def _init() -> None:
    db.connect()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": os.environ.get("DATABASE_PATH", "/data/topics.db")}


@app.get("/api/topics")
def topics(day: str | None = None) -> dict:
    con = db.connect()
    try:
        items = db.list_topics(con, day)
        return {"topics": items}
    finally:
        con.close()


@app.get("/api/profile")
def profile() -> dict:
    con = db.connect()
    try:
        return db.interest_profile(con)
    finally:
        con.close()


@app.put("/api/topics/{topic_id}/rating")
def rate(topic_id: int, body: RatingIn) -> dict:
    con = db.connect()
    try:
        ok = db.set_rating(con, topic_id, body.rating)
    finally:
        con.close()
    if not ok:
        raise HTTPException(status_code=404, detail="topic not found")
    return {"id": topic_id, "rating": body.rating}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")