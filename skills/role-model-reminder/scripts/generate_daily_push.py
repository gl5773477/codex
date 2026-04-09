import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from common import PUSH_HISTORY_PATH, REMINDER_CANDIDATES_PATH, read_jsonl, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render one role-model reminder for a target date.")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=REMINDER_CANDIDATES_PATH,
        help="Reminder candidate JSONL file.",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=PUSH_HISTORY_PATH,
        help="Push history JSON file.",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        type=str,
        default=str(date.today()),
        help="Date to render, in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=21,
        help="Avoid reminders that appeared in the most recent N history entries.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional markdown output file.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--update-history",
        action="store_true",
        help="Write the selected reminder back into the history file.",
    )
    return parser.parse_args()


def load_history(path: Path) -> dict:
    if not path.exists():
        return {"entries": []}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError(f"Invalid history file: {path}")
    return payload


def choose_candidate(candidates: list[dict], history: dict, target_date: str, window: int) -> dict:
    by_id = {item["reminder_id"]: item for item in candidates}
    recent_entries = sorted(history["entries"], key=lambda item: item["date"])
    recent_ids = [item["reminder_id"] for item in recent_entries if item["date"] != target_date][-window:]
    eligible = [item for item in candidates if item["reminder_id"] not in set(recent_ids)]
    pool = eligible or candidates
    digest = hashlib.sha1(target_date.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(pool)
    selected = pool[index]
    return by_id[selected["reminder_id"]]


def render_markdown(candidate: dict, target_date: str) -> str:
    story_case = candidate.get("story_vignette") or candidate.get("story_case") or candidate["origin_summary"]
    return "\n".join(
        [
            candidate["reminder"],
            f"-- {candidate['person_name']}",
            "",
            story_case,
        ]
    )


def update_history(history: dict, candidate: dict, target_date: str) -> dict:
    entries = [item for item in history["entries"] if item.get("date") != target_date]
    entries.append({"date": target_date, "reminder_id": candidate["reminder_id"]})
    entries = sorted(entries, key=lambda item: item["date"])[-365:]
    return {"entries": entries}


def main() -> None:
    args = parse_args()
    candidates = read_jsonl(args.candidates)
    if not candidates:
        raise ValueError("No reminder candidates found. Run refresh_materials.py and build_reminders.py first.")

    history = load_history(args.history)
    candidate = choose_candidate(candidates, history, args.target_date, args.window)

    if args.update_history:
        history = update_history(history, candidate, args.target_date)
        write_json(args.history, history)

    if args.format == "json":
        payload = {
            "date": args.target_date,
            "person_name": candidate["person_name"],
            "reminder": candidate["reminder"],
            "origin_summary": candidate["origin_summary"],
            "story_case": candidate.get("story_case", ""),
            "story_vignette": candidate.get("story_vignette", ""),
            "reflection_question": candidate["reflection_question"],
            "tags": candidate["tags"],
            "reminder_id": candidate["reminder_id"]
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = render_markdown(candidate, args.target_date) + "\n"

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote daily push to {args.output}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
