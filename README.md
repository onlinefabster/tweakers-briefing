# Tweakers Briefing — rating dashboard

Stores every Tweakers news topic that Hermes collects (title + short description, per day)
in SQLite, shows them in a small web dashboard grouped by day, and lets Fabian rate each
topic **not interested / neutral / interesting**. Those ratings feed back into the daily
morning podcast: Hermes writes little about disliked topics (~2 sentences) and more about
interesting ones.

- **Backend:** FastAPI + SQLite
- **Frontend:** single-page static HTML/JS (no build step)
- **Deploy:** Docker container on geekom, image published to GHCR
- **Data file:** `/docker/tweakers-briefing/data/topics.db` (bind-mounted as `/data`)

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | health + DB path |
| GET  | `/api/topics` | all topics (flat; frontend groups by `day`) |
| GET  | `/api/topics?day=YYYY-MM-DD` | one day |
| GET  | `/api/profile` | rating counts per category + overall |
| PUT  | `/api/topics/{id}/rating` | body `{"rating":"interesting\|neutral\|not_interested"}` |
| GET  | `/` | the dashboard |

## Local run

```bash
pip install -r requirements.txt
cd app && DATABASE_PATH=/tmp/topics.db uvicorn main:app --port 8000
```

## Docker

```bash
docker compose up -d   # serves http://<host>:13400
```

The container reads/writes the same `topics.db` file Hermes uses on the host, so ratings
made in the dashboard are immediately visible to the next morning's brief generation.

## Hermes integration

The 05:00 cron job runs (from `~/.hermes/scripts/`):

- `topics_ingest.py`  — upsert collected topics (day + title, idempotent) into the DB
- `topics_ratings.py` — read ratings/profile so the narration budget can react

See `.hermes/plans/2026-09-22_185324-tweakers-rating-dashboard.md` for the full design.