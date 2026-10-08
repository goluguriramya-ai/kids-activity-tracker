#!/usr/bin/env python3
"""
Kids Activity Tracker — web UI.

A small Flask app on top of the same JSON storage the CLI uses
(see tracker.py — all data functions are reused from there).

Run locally:
    pip install -r requirements.txt
    python3 app.py            # http://127.0.0.1:5000

Production (e.g. Render free tier):
    gunicorn app:app          # honors the PORT env var
"""

import os
from datetime import datetime, date

from flask import Flask, request, redirect, url_for, render_template_string

import tracker  # reuse the CLI's data layer (no duplicated storage logic)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Templates (inline, self-contained — no external CSS/JS needed)
# ---------------------------------------------------------------------------

LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} · Kids Activity Tracker</title>
<style>
  :root { --green: #2f8f5b; --green-dark: #247245; --amber: #b97f1f;
          --red: #c0392b; --ink: #2d2a26; --bg: #faf7f1; --card: #ffffff; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--bg); color: var(--ink); margin: 0; }
  header { background: var(--green); color: #fff; padding: 14px 0; }
  header .wrap { display: flex; align-items: center; justify-content: space-between;
                 flex-wrap: wrap; gap: 8px; }
  header h1 { font-size: 1.25rem; margin: 0; }
  nav a { color: #fff; text-decoration: none; margin-left: 14px; opacity: .85; }
  nav a.active, nav a:hover { opacity: 1; text-decoration: underline; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 16px; }
  main .wrap { padding-top: 20px; padding-bottom: 40px; }
  .card { background: var(--card); border-radius: 12px; padding: 16px;
          margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .grow { flex: 1; min-width: 180px; }
  .title { font-weight: 600; font-size: 1.05rem; }
  .meta { color: #6b6259; font-size: .9rem; margin-top: 4px; }
  .badge { display: inline-block; font-size: .78rem; font-weight: 600;
           padding: 2px 10px; border-radius: 999px; }
  .badge.todo { background: #fdf0d5; color: var(--amber); }
  .badge.done { background: #dff3e6; color: var(--green-dark); }
  .badge.bell { background: #e8eefc; color: #2f5fb3; }
  .btn { border: none; border-radius: 8px; padding: 8px 14px; font-size: .95rem;
         cursor: pointer; text-decoration: none; display: inline-block; }
  .btn.primary { background: var(--green); color: #fff; }
  .btn.primary:hover { background: var(--green-dark); }
  .btn.small { padding: 5px 10px; font-size: .85rem; }
  .btn.done { background: #e7f4ec; color: var(--green-dark); }
  .btn.delete { background: #fbe9e6; color: var(--red); }
  label { display: block; font-weight: 600; margin: 12px 0 4px; }
  input, textarea { width: 100%; padding: 9px 10px; font-size: 1rem;
                    border: 1px solid #d8d2c6; border-radius: 8px; background: #fff; }
  input:focus, textarea:focus { outline: 2px solid var(--green); border-color: var(--green); }
  .two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; }
  .filters .field { flex: 1; min-width: 150px; }
  .empty { text-align: center; color: #6b6259; padding: 32px 0; }
  .kid { font-size: 1.15rem; font-weight: 700; margin-bottom: 6px; }
  footer { text-align: center; color: #8a8178; font-size: .85rem; padding: 24px 0; }
</style>
</head>
<body>
<header><div class="wrap">
  <h1>🧒 Kids Activity Tracker</h1>
  <nav>
    <a href="{{ url_for('home') }}" class="{{ 'active' if active=='home' }}">Home</a>
    <a href="{{ url_for('add') }}" class="{{ 'active' if active=='add' }}">Add</a>
    <a href="{{ url_for('reminders') }}" class="{{ 'active' if active=='reminders' }}">Reminders</a>
    <a href="{{ url_for('summary') }}" class="{{ 'active' if active=='summary' }}">Summary</a>
  </nav>
</div></header>
<main><div class="wrap">
{{ content|safe }}
</div></main>
<footer>Family demo · data lives in a tiny JSON file</footer>
</body>
</html>
"""

HOME_TEMPLATE = """
<div class="card">
  <form class="filters" method="get" action="{{ url_for('home') }}">
    <div class="field">
      <label for="kid">Kid</label>
      <input id="kid" name="kid" list="kids" value="{{ kid }}" placeholder="All kids">
      <datalist id="kids">
        {% for k in all_kids %}<option value="{{ k }}">{% endfor %}
      </datalist>
    </div>
    <div class="field">
      <label for="date">Date</label>
      <input id="date" type="date" name="date" value="{{ date }}">
    </div>
    <div><button class="btn primary" type="submit">Filter</button></div>
    <div><a class="btn" href="{{ url_for('home') }}">Clear</a></div>
  </form>
</div>
{% if activities %}
  {% for a in activities %}
  <div class="card"><div class="row">
    <div class="grow">
      <span class="badge {{ 'done' if a.done else 'todo' }}">{{ 'Done' if a.done else 'To do' }}</span>
      {% if a.remind_at %}<span class="badge bell">🔔 {{ a.remind_at_display }}</span>{% endif %}
      <div class="title">{{ a.activity }}</div>
      <div class="meta">{{ a.kid }} · {{ a.date }}{% if a.time %} at {{ a.time }}{% endif %}{% if a.minutes %} · {{ a.minutes }} min{% endif %}{% if a.notes %} · {{ a.notes }}{% endif %}</div>
    </div>
    <div class="row">
      {% if not a.done %}
      <form method="post" action="{{ url_for('mark_done', activity_id=a.id) }}">
        <input type="hidden" name="next" value="{{ next_url }}">
        <button class="btn small done" type="submit">✓ Done</button>
      </form>
      {% endif %}
      <form method="post" action="{{ url_for('delete', activity_id=a.id) }}"
            onsubmit="return confirm('Delete this activity?');">
        <input type="hidden" name="next" value="{{ next_url }}">
        <button class="btn small delete" type="submit">Delete</button>
      </form>
    </div>
  </div></div>
  {% endfor %}
{% else %}
  <div class="empty">No activities yet — <a href="{{ url_for('add') }}">add the first one</a> 🎉</div>
{% endif %}
"""

ADD_TEMPLATE = """
<div class="card">
  <h2 style="margin-top:0">Add an activity</h2>
  {% if error %}<p style="color: var(--red); font-weight:600;">{{ error }}</p>{% endif %}
  <form method="post" action="{{ url_for('add') }}">
    <label for="kid">Kid's name</label>
    <input id="kid" name="kid" list="kids" required placeholder="e.g. Aarav">
    <datalist id="kids">{% for k in all_kids %}<option value="{{ k }}">{% endfor %}</datalist>

    <label for="activity">Activity</label>
    <input id="activity" name="activity" required placeholder="e.g. Soccer practice">

    <div class="two">
      <div><label for="date">Date</label>
        <input id="date" type="date" name="date" value="{{ today }}"></div>
      <div><label for="time">Time (optional)</label>
        <input id="time" type="time" name="time"></div>
    </div>

    <div class="two">
      <div><label for="minutes">Minutes (optional)</label>
        <input id="minutes" type="number" name="minutes" min="0" value="0"></div>
      <div><label for="remind_at">🔔 Remind me at (optional)</label>
        <input id="remind_at" type="datetime-local" name="remind_at"></div>
    </div>

    <label for="notes">Notes (optional)</label>
    <input id="notes" name="notes" placeholder="e.g. Bring water bottle">

    <div style="margin-top:16px">
      <button class="btn primary" type="submit">Save activity</button>
    </div>
  </form>
</div>
"""

REMINDERS_TEMPLATE = """
<div class="card">
  <h2 style="margin-top:0">🔔 Upcoming reminders</h2>
  <p class="meta" style="margin-top:0">Reminders for parents — check back here; nothing is sent automatically.</p>
</div>
{% if reminders %}
  {% for r in reminders %}
  <div class="card"><div class="row">
    <div class="grow">
      <div class="title">{{ r.activity }}</div>
      <div class="meta">{{ r.kid }} · {{ r.when_display }}</div>
    </div>
    <span class="badge bell">{{ r.relative }}</span>
  </div></div>
  {% endfor %}
{% else %}
  <div class="empty">No upcoming reminders. Add one from the <a href="{{ url_for('add') }}">Add</a> page 🎉</div>
{% endif %}
"""

SUMMARY_TEMPLATE = """
<div class="card">
  <form class="filters" method="get" action="{{ url_for('summary') }}">
    <div class="field">
      <label for="date">Date</label>
      <input id="date" type="date" name="date" value="{{ date }}">
    </div>
    <div><button class="btn primary" type="submit">Show</button></div>
  </form>
</div>
{% if per_kid %}
  {% for kid, stats in per_kid|dictsort %}
  <div class="card">
    <div class="kid">{{ kid }}</div>
    <div class="meta">{{ stats.total }} {{ 'activity' if stats.total == 1 else 'activities' }}
      · {{ stats.done }} done · {{ stats.minutes }} min total</div>
  </div>
  {% endfor %}
  <div class="card"><strong>Total: {{ total_activities }}
    {{ 'activity' if total_activities == 1 else 'activities' }}, {{ total_minutes }} min</strong></div>
{% else %}
  <div class="empty">Nothing recorded for {{ date }}.</div>
{% endif %}
"""


def render_page(title, active, template, **context):
    """Render a content template inside the shared layout."""
    content = render_template_string(template, **context)
    return render_template_string(
        LAYOUT, title=title, active=active, content=content
    )


def parse_date(text, default):
    """Return a valid YYYY-MM-DD date, or `default` when the input is bad."""
    try:
        return tracker.valid_date(text)
    except Exception:
        return default


def all_kid_names():
    """Sorted unique kid names already in the data (for the datalist)."""
    return sorted({a["kid"] for a in tracker.load_activities(tracker.data_path())})


def remind_display(remind_at):
    """'2026-10-08T15:30' -> 'Oct 8, 3:30 PM' (falls back to raw text)."""
    try:
        return datetime.fromisoformat(remind_at).strftime("%b %-d, %-I:%M %p")
    except (ValueError, TypeError):
        return remind_at or ""


def relative_time(remind_at):
    """'in 2h 15m' / 'in 3 days' / 'now' style label for a reminder."""
    try:
        delta = datetime.fromisoformat(remind_at) - datetime.now()
    except (ValueError, TypeError):
        return ""
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "due now"
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return "in %d day%s" % (days, "s" if days != 1 else "")
    if hours:
        return "in %dh %dm" % (hours, minutes)
    return "in %dm" % minutes


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    kid = request.args.get("kid", "").strip() or None
    when = request.args.get("date", "").strip() or None
    if when:
        when = parse_date(when, None)
    activities = tracker.list_activities(tracker.data_path(), kid=kid, when=when)
    for a in activities:
        a["remind_at_display"] = remind_display(a.get("remind_at"))
    return render_page(
        "Home", "home", HOME_TEMPLATE,
        activities=activities, kid=request.args.get("kid", ""),
        date=request.args.get("date", ""),
        all_kids=all_kid_names(), next_url=request.full_path,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        kid = request.form.get("kid", "").strip()
        activity = request.form.get("activity", "").strip()
        when = parse_date(request.form.get("date", "").strip(), tracker.today_str())
        time = request.form.get("time", "").strip()
        notes = request.form.get("notes", "").strip()
        remind_at = request.form.get("remind_at", "").strip()
        try:
            minutes = max(0, int(request.form.get("minutes", 0) or 0))
        except ValueError:
            minutes = 0
        if not kid or not activity:
            return render_page(
                "Add", "add", ADD_TEMPLATE, error="Kid and activity are required.",
                all_kids=all_kid_names(), today=tracker.today_str(),
            ), 400
        record = tracker.add_activity(
            tracker.data_path(), kid, activity, when, minutes, notes,
            remind_at=remind_at or None,
        )
        if time:
            # store the optional time alongside the record
            activities = tracker.load_activities(tracker.data_path())
            rec = tracker.find_by_id(activities, record["id"])
            rec["time"] = time
            tracker.save_activities(tracker.data_path(), activities)
        return redirect(url_for("home"))
    return render_page(
        "Add", "add", ADD_TEMPLATE, error=None,
        all_kids=all_kid_names(), today=tracker.today_str(),
    )


@app.route("/done/<int:activity_id>", methods=["POST"])
def mark_done(activity_id):
    tracker.mark_done(tracker.data_path(), activity_id)
    return redirect(request.form.get("next") or url_for("home"))


@app.route("/delete/<int:activity_id>", methods=["POST"])
def delete(activity_id):
    tracker.remove_activity(tracker.data_path(), activity_id)
    return redirect(request.form.get("next") or url_for("home"))


@app.route("/reminders")
def reminders():
    now = datetime.now()
    upcoming = []
    for a in tracker.load_activities(tracker.data_path()):
        raw = a.get("remind_at")
        if not raw:
            continue
        try:
            when = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if when >= now:
            upcoming.append({
                "kid": a["kid"],
                "activity": a["activity"],
                "when_display": remind_display(raw),
                "relative": relative_time(raw),
                "sort_key": when,
            })
    upcoming.sort(key=lambda r: r["sort_key"])
    return render_page("Reminders", "reminders", REMINDERS_TEMPLATE, reminders=upcoming)


@app.route("/summary")
def summary():
    when = parse_date(request.args.get("date", "").strip(), tracker.today_str())
    activities = tracker.load_activities(tracker.data_path())
    per_kid = tracker.summarize(activities, when)
    total_activities = sum(s["total"] for s in per_kid.values())
    total_minutes = sum(s["minutes"] for s in per_kid.values())
    return render_page(
        "Summary", "summary", SUMMARY_TEMPLATE, date=when, per_kid=per_kid,
        total_activities=total_activities, total_minutes=total_minutes,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
