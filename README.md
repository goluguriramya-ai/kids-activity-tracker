# Kids Activity Tracker

A tiny command-line app that tracks kids' activities and daily routines —
soccer practice, piano lessons, reading time, chores, anything you want to log.

Built with **Python's standard library only** — nothing to install, runs anywhere
Python 3 is available.

## Quick start

```bash
# Add activities (date defaults to today)
python3 tracker.py add --kid Aarav --activity "Soccer practice" --minutes 60
python3 tracker.py add --kid Diya --activity "Piano lesson" --minutes 45 --notes "Bring sheet music"
python3 tracker.py add --kid Aarav --activity "Read a book" --date 2026-10-08 --minutes 30

# List everything, or filter by kid / date
python3 tracker.py list
python3 tracker.py list --kid Aarav
python3 tracker.py list --date 2026-10-08

# Mark complete / delete (use the [id] shown by `list`)
python3 tracker.py done 1
python3 tracker.py remove 2

# Daily summary: activities and total minutes per kid
python3 tracker.py summary
python3 tracker.py summary --date 2026-10-08
```

## Commands

| Command | Purpose |
|---|---|
| `add --kid NAME --activity TEXT [--date YYYY-MM-DD] [--minutes N] [--notes TEXT]` | Add an activity (date defaults to today) |
| `list [--kid NAME] [--date YYYY-MM-DD]` | List activities, optionally filtered |
| `done ID` | Mark an activity complete |
| `remove ID` | Delete an activity |
| `summary [--date YYYY-MM-DD]` | Daily summary: activities and total minutes per kid |

## Web app

The same tracker is also available as a friendly website — great for parents
who prefer clicking to typing commands. It reuses the CLI's data functions,
so both share the same `data/activities.json`.

```bash
pip install -r requirements.txt
python3 app.py
# open http://127.0.0.1:5000
```

Pages: **Home** (filter by kid/date, mark done, delete) · **Add** (form with an
optional "🔔 Remind me at" date/time) · **Reminders** (upcoming parent
reminders, soonest first) · **Summary** (daily totals per kid).

## Deploying to Render (free tier)

1. Push this repo to GitHub.
2. In Render, create a **Web Service** from the repo (or let it pick up
   `render.yaml`, which describes the free plan, the build command
   `pip install -r requirements.txt`, and the start command `gunicorn app:app`).
3. Render sets the `PORT` env var automatically; the app reads it (default 5000).

The app writes `data/activities.json` atomically (temp file + rename), so it
is safe for a small friends-and-family demo. For real multi-user scale you
would swap the JSON file for a database.

## Data

Activities are stored as JSON in `data/activities.json`, created automatically
on first use. The file is git-ignored, so your family's data never gets
committed. Each record holds: `id`, `kid`, `activity`, `date`, `minutes`,
`notes`, `done`.

## Tests

```bash
python3 -m unittest discover -s tests
```
