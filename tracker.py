#!/usr/bin/env python3
"""
kids-activity-tracker — a tiny CLI for tracking kids' activities and daily routines.

Examples:
    python3 tracker.py add --kid Aarav --activity "Soccer practice" --minutes 60
    python3 tracker.py list --kid Aarav
    python3 tracker.py done 1
    python3 tracker.py remove 2
    python3 tracker.py summary

Data is stored as JSON in data/activities.json next to this file.
Standard library only — nothing to install.
"""

import argparse
import json
import os
import sys
from datetime import date

# Default data file: <project>/data/activities.json (next to this script,
# so it works no matter which folder you run the command from).
# Tests can point at a throwaway file with the KIDS_TRACKER_DATA env var.
DEFAULT_DATA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "activities.json"
)


def data_path():
    """Return the JSON file we read/write. Overridable for tests."""
    return os.environ.get("KIDS_TRACKER_DATA", DEFAULT_DATA_FILE)


def load_activities(path):
    """Load the activity list; return [] when the file doesn't exist yet."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_activities(path, activities):
    """Save the activity list, creating the data folder if needed.

    Writes go to a temp file first, then atomically replace the real file,
    so a crash mid-write (or two writers at once) never leaves half a file.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2)
    os.replace(tmp_path, path)


def today_str():
    """Today as YYYY-MM-DD."""
    return date.today().isoformat()


def valid_date(text):
    """argparse type helper: only accept real YYYY-MM-DD dates."""
    try:
        year, month, day = (int(part) for part in text.split("-"))
        return date(year, month, day).isoformat()
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            "date must look like YYYY-MM-DD, got %r" % (text,)
        )


def next_id(activities):
    """Next free id: one more than the biggest id used so far (starts at 1)."""
    return max((a["id"] for a in activities), default=0) + 1


def find_by_id(activities, activity_id):
    """Return the record with this id, or None if there isn't one."""
    for record in activities:
        if record["id"] == activity_id:
            return record
    return None


def format_activity(record):
    """Render one activity as a readable single line."""
    line = "[%d] %s | %s — %s" % (
        record["id"], record["date"], record["kid"], record["activity"]
    )
    if record.get("minutes"):
        line += " (%d min)" % record["minutes"]
    if record.get("notes"):
        line += " — %s" % record["notes"]
    status = "done" if record["done"] else "todo"
    return line + " <%s>" % status


# ---------------------------------------------------------------------------
# Business logic (kept separate from argparse so tests can call it directly)
# ---------------------------------------------------------------------------

def add_activity(path, kid, activity, when, minutes, notes, remind_at=None):
    """Add an activity record and return it.

    `remind_at` is an optional ISO datetime string ("YYYY-MM-DDTHH:MM")
    used by the web UI for parent reminders; the CLI simply never passes it.
    """
    activities = load_activities(path)
    record = {
        "id": next_id(activities),
        "kid": kid,
        "activity": activity,
        "date": when,
        "minutes": minutes,
        "notes": notes,
        "done": False,
    }
    if remind_at:
        record["remind_at"] = remind_at
    activities.append(record)
    save_activities(path, activities)
    return record


def list_activities(path, kid=None, when=None):
    """Return activities, optionally filtered by kid and/or date."""
    activities = load_activities(path)
    if kid is not None:
        activities = [a for a in activities if a["kid"] == kid]
    if when is not None:
        activities = [a for a in activities if a["date"] == when]
    return activities


def mark_done(path, activity_id):
    """Mark an activity done. Returns the record, or None if id is unknown."""
    activities = load_activities(path)
    record = find_by_id(activities, activity_id)
    if record is None:
        return None
    record["done"] = True
    save_activities(path, activities)
    return record


def remove_activity(path, activity_id):
    """Delete an activity. Returns the removed record, or None if unknown."""
    activities = load_activities(path)
    record = find_by_id(activities, activity_id)
    if record is None:
        return None
    activities = [a for a in activities if a["id"] != activity_id]
    save_activities(path, activities)
    return record


def summarize(activities, when):
    """Group one day's activities per kid: counts and total minutes."""
    per_kid = {}
    for record in activities:
        if record["date"] != when:
            continue
        stats = per_kid.setdefault(
            record["kid"], {"total": 0, "done": 0, "minutes": 0}
        )
        stats["total"] += 1
        stats["done"] += 1 if record["done"] else 0
        stats["minutes"] += record.get("minutes", 0)
    return per_kid


# ---------------------------------------------------------------------------
# CLI commands (thin wrappers around the logic above)
# ---------------------------------------------------------------------------

def cmd_add(args):
    if args.minutes < 0:
        print("error: --minutes can't be negative", file=sys.stderr)
        return 1
    record = add_activity(
        data_path(), args.kid, args.activity, args.date, args.minutes, args.notes
    )
    print("Added activity #%d for %s: %s" % (record["id"], record["kid"], record["activity"]))
    return 0


def cmd_list(args):
    matches = list_activities(data_path(), kid=args.kid, when=args.date)
    if not matches:
        print("No activities found.")
        return 0
    for record in matches:
        print(format_activity(record))
    return 0


def cmd_done(args):
    record = mark_done(data_path(), args.id)
    if record is None:
        print("error: no activity with id %d" % args.id, file=sys.stderr)
        return 1
    print("Marked #%d as done: %s" % (record["id"], record["activity"]))
    return 0


def cmd_remove(args):
    record = remove_activity(data_path(), args.id)
    if record is None:
        print("error: no activity with id %d" % args.id, file=sys.stderr)
        return 1
    print("Removed #%d: %s" % (record["id"], record["activity"]))
    return 0


def cmd_summary(args):
    activities = load_activities(data_path())
    per_kid = summarize(activities, args.date)
    print("Summary for %s" % args.date)
    print("-" * 30)
    if not per_kid:
        print("No activities recorded.")
        return 0
    total_activities = 0
    total_minutes = 0
    for kid in sorted(per_kid):
        stats = per_kid[kid]
        total_activities += stats["total"]
        total_minutes += stats["minutes"]
        noun = "activity" if stats["total"] == 1 else "activities"
        print("%s: %d %s (%d done), %d min total"
              % (kid, stats["total"], noun, stats["done"], stats["minutes"]))
    print("-" * 30)
    total_noun = "activity" if total_activities == 1 else "activities"
    print("Total: %d %s, %d min" % (total_activities, total_noun, total_minutes))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tracker.py",
        description="Track kids' activities and daily routines.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add an activity")
    p_add.add_argument("--kid", required=True, help="Kid's name")
    p_add.add_argument("--activity", required=True, help="What they did / will do")
    p_add.add_argument("--date", type=valid_date, default=today_str(),
                       help="Date as YYYY-MM-DD (default: today)")
    p_add.add_argument("--minutes", type=int, default=0,
                       help="How long it took / will take, in minutes")
    p_add.add_argument("--notes", default="", help="Optional notes")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List activities")
    p_list.add_argument("--kid", help="Only show this kid's activities")
    p_list.add_argument("--date", type=valid_date, help="Only show this date (YYYY-MM-DD)")
    p_list.set_defaults(func=cmd_list)

    p_done = sub.add_parser("done", help="Mark an activity complete")
    p_done.add_argument("id", type=int, help="Activity id")
    p_done.set_defaults(func=cmd_done)

    p_remove = sub.add_parser("remove", help="Delete an activity")
    p_remove.add_argument("id", type=int, help="Activity id")
    p_remove.set_defaults(func=cmd_remove)

    p_summary = sub.add_parser("summary", help="Daily summary per kid")
    p_summary.add_argument("--date", type=valid_date, default=today_str(),
                           help="Date as YYYY-MM-DD (default: today)")
    p_summary.set_defaults(func=cmd_summary)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
