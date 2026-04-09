import argparse
import json
from datetime import date
from pathlib import Path

from common import SCENE_UNITS_OUTPUT_PATH, WORDS_OUTPUT_PATH, ensure_parent, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an AI-ready payload from scene units and words.")
    parser.add_argument("--words", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    parser.add_argument(
        "--scene-units",
        type=Path,
        default=SCENE_UNITS_OUTPUT_PATH,
        help="Path to scene_units.jsonl.",
    )
    parser.add_argument("--unit-id", type=str, default="", help="Unit ID to export. Defaults to the first unit.")
    parser.add_argument(
        "--date",
        dest="payload_date",
        type=str,
        default=str(date.today()),
        help="Date to embed in the payload. Defaults to today.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("kb") / "sample_ai_payload.json",
        help="Path to the output JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    words = read_jsonl(args.words)
    units = read_jsonl(args.scene_units)
    if not units:
        raise ValueError("No scene units found. Run scripts/build_scene_units.py first.")

    selected_unit = None
    if args.unit_id:
        for unit in units:
            if unit["unit_id"] == args.unit_id:
                selected_unit = unit
                break
        if selected_unit is None:
            raise ValueError(f"Unit ID not found: {args.unit_id}")
    else:
        selected_unit = units[0]

    words_by_id = {row["word_id"]: row for row in words}
    payload_words = []
    for word_id in selected_unit["core_words"]:
        word = words_by_id.get(word_id)
        if word is None:
            continue
        payload_words.append(
            {
                "word": word["word_id"],
                "meaning": "；".join(word.get("meaning_zh", [])),
            }
        )

    payload = {
        "date": args.payload_date,
        "unit": {
            "scene_id": selected_unit["scene_id"],
            "title": selected_unit["title"],
            "core_words": selected_unit["core_words"],
            "contrast_pairs": selected_unit["contrast_pairs"],
            "memory_chain": selected_unit["memory_chain"],
        },
        "words": payload_words,
    }

    ensure_parent(args.output)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote AI payload to {args.output}")


if __name__ == "__main__":
    main()
