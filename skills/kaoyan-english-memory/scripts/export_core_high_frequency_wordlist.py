import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from common import CORE_HIGH_FREQUENCY_MIN_FREQUENCY, RAW_WORDS_PATH, ROOT, ensure_parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a core high-frequency kaoyan wordlist from the full ranked list.")
    parser.add_argument("--input", type=Path, default=RAW_WORDS_PATH, help="Path to the full kaoyan CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "raw" / "kaoyan_core_high_frequency_words.csv",
        help="Where to store the high-frequency subset CSV.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=ROOT / "data" / "raw" / "kaoyan_core_high_frequency_words.metadata.json",
        help="Where to store the subset metadata.",
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=CORE_HIGH_FREQUENCY_MIN_FREQUENCY,
        help="Minimum frequency threshold for inclusion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    if not fieldnames:
        raise ValueError("Input CSV is missing a header row.")

    filtered = []
    for row in rows:
        value = (row.get("frequency") or "").strip()
        if not value:
            continue
        frequency = int(value)
        if frequency >= args.min_frequency:
            filtered.append(row)

    ensure_parent(args.output)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)

    metadata = {
        "source_file": str(args.input),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "min_frequency": args.min_frequency,
        "row_count": len(filtered),
        "notes": [
            "Derived from exam-data/NETEMVocabulary ranked CSV already stored in data/raw/kaoyan_words.csv.",
            "The upstream README says the first 2444 words appear at least 40 times in the aggregated exam corpus and are the true high-frequency vocabulary.",
        ],
    }
    ensure_parent(args.metadata_output)
    args.metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(filtered)} rows with frequency >= {args.min_frequency}")
    print(f"Wrote high-frequency CSV to {args.output}")
    print(f"Wrote metadata to {args.metadata_output}")


if __name__ == "__main__":
    main()
