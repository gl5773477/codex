import argparse
from collections import Counter
from pathlib import Path

from common import (
    CURATED_MATERIALS_PATH,
    INBOX_DIR,
    MATERIAL_COVERAGE_PATH,
    PEOPLE_PATH,
    SEED_MATERIALS_PATH,
    load_json,
    load_material_records,
    normalize_material,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge seed and inbox reminder materials, then emit coverage.")
    parser.add_argument("--seed", type=Path, default=SEED_MATERIALS_PATH, help="Seed material file.")
    parser.add_argument("--inbox-dir", type=Path, default=INBOX_DIR, help="Directory of inbox material files.")
    parser.add_argument("--people", type=Path, default=PEOPLE_PATH, help="Tracked people config.")
    parser.add_argument(
        "--curated-output",
        type=Path,
        default=CURATED_MATERIALS_PATH,
        help="Output file for curated material list.",
    )
    parser.add_argument(
        "--coverage-output",
        type=Path,
        default=MATERIAL_COVERAGE_PATH,
        help="Output file for coverage report.",
    )
    return parser.parse_args()


def collect_materials(seed_path: Path, inbox_dir: Path) -> list[dict]:
    source_paths = [seed_path]
    if inbox_dir.exists():
        source_paths.extend(sorted(path for path in inbox_dir.glob("*.json") if path.is_file()))

    deduped: dict[str, dict] = {}
    for path in source_paths:
        for record in load_material_records(path):
            normalized = normalize_material(record)
            deduped[normalized["id"]] = normalized
    return sorted(deduped.values(), key=lambda item: (item["person_name"], item["title"], item["id"]))


def build_coverage(materials: list[dict], people: list[dict]) -> dict:
    counts_by_person = Counter(item["person_id"] for item in materials)
    counts_by_tag = Counter(tag for item in materials for tag in item["tags"])
    counts_by_type = Counter(item["material_type"] for item in materials)

    people_status = []
    for person in people:
        count = counts_by_person.get(person["person_id"], 0)
        target = int(person.get("target_material_count", 0))
        people_status.append(
            {
                "person_id": person["person_id"],
                "person_name": person["person_name"],
                "count": count,
                "target_material_count": target,
                "gap": max(target - count, 0),
                "themes": person.get("themes", []),
            }
        )

    return {
        "material_count": len(materials),
        "counts_by_person": dict(sorted(counts_by_person.items())),
        "counts_by_tag": dict(sorted(counts_by_tag.items())),
        "counts_by_type": dict(sorted(counts_by_type.items())),
        "people_status": people_status,
    }


def main() -> None:
    args = parse_args()
    people = load_json(args.people)
    materials = collect_materials(args.seed, args.inbox_dir)
    coverage = build_coverage(materials, people)

    write_json(args.curated_output, materials)
    write_json(args.coverage_output, coverage)

    print(f"Curated {len(materials)} materials")
    print(f"Wrote curated materials to {args.curated_output}")
    print(f"Wrote coverage report to {args.coverage_output}")


if __name__ == "__main__":
    main()
