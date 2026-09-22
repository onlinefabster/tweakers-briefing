"""SQLite persistence layer for the Tweakers rating dashboard.

The database file lives at the path in env DATABASE_PATH (default /data/topics.db).
Hermes helper scripts point it at the host path; the container points it at /data/topics.db
(read-only in the sense that only ratings are written here by the API).
"""
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB = os.environ.get("DATABASE_PATH", "/data/topics.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  day              TEXT NOT NULL,
  title            TEXT NOT NULL,
  description      TEXT NOT NULL DEFAULT '',
  url              TEXT NOT NULL DEFAULT '',
  category         TEXT NOT NULL DEFAULT '',
  rating           TEXT NOT NULL DEFAULT 'neutral',
  rating_updated_at TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topics_day_title ON topics(day, title);
"""

# Ratings the user may assign
VALID_RATINGS = {"not_interested", "neutral", "interesting"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.executescript(SCHEMA)
    con.commit()
    return con


# --- write hooks -------------------------------------------------------------
def upsert_topics(con: sqlite3.Connection, topics: list[dict]) -> int:
    """Insert topics keyed by (day, title). Returns number of rows newly inserted.

    Existing rows (same day+title) are left untouched apart from filling in blank
    description/category/url if the new payload has richer data. Rating is NEVER
    overwritten by ingestion.
    """
    inserted = 0
    for t in topics:
        day = t.get("day")
        title = t.get("title")
        if not day or not title:
            continue
        desc = t.get("description", "")
        url = t.get("url", "")
        cat = t.get("category", "")
        cur = con.execute(
            "INSERT OR IGNORE INTO topics(day, title, description, url, category) VALUES(?,?,?,?,?)",
            (day, title, desc, url, cat),
        )
        if cur.rowcount:
            inserted += 1
        else:
            # enrich blank fields without touching rating
            con.execute(
                """UPDATE topics SET
                     description = CASE WHEN trim(description)='' THEN ? ELSE description END,
                     url          = CASE WHEN trim(url)=''          THEN ? ELSE url END,
                     category     = CASE WHEN trim(category)=''     THEN ? ELSE category END
                   WHERE day=? AND title=?""",
                (desc, url, cat, day, title),
            )
    con.commit()
    return inserted


def set_rating(con: sqlite3.Connection, topic_id: int, rating: str) -> bool:
    if rating not in VALID_RATINGS:
        raise ValueError(f"invalid rating {rating!r}; must be one of {sorted(VALID_RATINGS)}")
    cur = con.execute(
        "UPDATE topics SET rating=?, rating_updated_at=? WHERE id=?",
        (rating, now_iso(), topic_id),
    )
    con.commit()
    return cur.rowcount > 0


# --- read hooks --------------------------------------------------------------
def list_topics(con: sqlite3.Connection, day: str | None = None) -> list[dict]:
    if day:
        rows = con.execute(
            "SELECT * FROM topics WHERE day=? ORDER BY id", (day,)
        ).fetchall()
    else:
        rows = con.execute("SELECT * FROM topics ORDER BY day DESC, id").fetchall()
    return [dict(r) for r in rows]


def ratings_for_titles(con: sqlite3.Connection, titles: list[str]) -> list[dict]:
    """Historical ratings for the given titles (any day) — used to let yesterday's
    rating influence today's brief re same-titled or category-similar topics."""
    if not titles:
        return []
    marks = ",".join("?" for _ in titles)
    rows = con.execute(
        f"SELECT title, category, rating FROM topics WHERE title IN ({marks})",
        titles,
    ).fetchall()
    return [dict(r) for r in rows]


def interest_profile(con: sqlite3.Connection) -> dict:
    """Per-category + overall rating counts, so the agent can generalize interest."""
    prof: dict = {"by_category": {}, "overall": {"interesting": 0, "neutral": 0, "not_interested": 0}}
    for r in con.execute("SELECT category, rating, COUNT(*) n FROM topics GROUP BY category, rating"):
        cat = r["category"] or "_uncategorized"
        prof["by_category"].setdefault(cat, {"interesting": 0, "neutral": 0, "not_interested": 0})
        prof["by_category"][cat][r["rating"]] += r["n"]
        prof["overall"][r["rating"]] += r["n"]
    return prof