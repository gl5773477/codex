import argparse
from pathlib import Path

from common import CURATED_MATERIALS_PATH, REMINDER_CANDIDATES_PATH, load_json, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reminder candidates from curated role-model materials.")
    parser.add_argument(
        "--materials",
        type=Path,
        default=CURATED_MATERIALS_PATH,
        help="Curated material JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REMINDER_CANDIDATES_PATH,
        help="Reminder candidate JSONL output.",
    )
    return parser.parse_args()


def build_candidates(materials: list[dict]) -> list[dict]:
    candidates = []
    for item in materials:
        candidates.append(
            {
                "reminder_id": item["id"],
                "person_id": item["person_id"],
                "person_name": item["person_name"],
                "title": item["title"],
                "material_type": item["material_type"],
                "origin_label": "故事" if item["material_type"] == "story" else "思想",
                "origin_summary": item["summary"],
                "principle": item["principle"],
                "reminder": item["reminder"],
                "reflection_question": item["reflection_question"],
                "tags": item["tags"],
                "source_hint": item["source_hint"],
                "story_case": item.get("story_case", ""),
                "story_vignette": item.get("story_vignette", ""),
            }
        )
    return sorted(candidates, key=lambda item: (item["person_name"], item["title"], item["reminder_id"]))


def main() -> None:
    args = parse_args()
    materials = load_json(args.materials)
    candidates = build_candidates(materials)
    write_jsonl(args.output, candidates)
    print(f"Built {len(candidates)} reminder candidates")
    print(f"Wrote candidates to {args.output}")


if __name__ == "__main__":
    main()
