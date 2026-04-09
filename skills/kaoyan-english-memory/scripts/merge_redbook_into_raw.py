import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from common import RAW_WORDS_PATH, ROOT, clean_word, ensure_parent

REDBOOK_PATH = ROOT / "data" / "raw" / "kaoyan_redbook_words.json"
MERGE_METADATA_PATH = ROOT / "data" / "raw" / "kaoyan_words.merge_redbook.metadata.json"
REDBOOK_SOURCE = "3056810551/2027-kaoyan-english-redbook-json"
POS_RE = re.compile(r"\b(?:modal|adj|adv|n|v|vt|vi|aux|prep|pron|num|conj|int|art)\.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge redbook-only words into the main raw kaoyan CSV.")
    parser.add_argument("--main-input", type=Path, default=RAW_WORDS_PATH, help="Path to the main raw CSV.")
    parser.add_argument(
        "--redbook-input",
        type=Path,
        default=REDBOOK_PATH,
        help="Path to the downloaded redbook JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RAW_WORDS_PATH,
        help="Where to write the merged raw CSV.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=MERGE_METADATA_PATH,
        help="Where to write merge metadata.",
    )
    return parser.parse_args()


def extract_pos_and_meaning(text: str) -> tuple[str, str]:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    pos_tokens = []
    for token in POS_RE.findall(raw):
        if token not in pos_tokens:
            pos_tokens.append(token)
    meaning = POS_RE.sub("", raw)
    meaning = re.sub(r"\s+", " ", meaning).strip(" ;；,.，")
    return " ".join(pos_tokens), meaning


def main() -> None:
    args = parse_args()

    with args.main_input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        existing_rows = list(reader)
        existing_fieldnames = list(reader.fieldnames or [])

    if not existing_fieldnames:
        raise ValueError("Main raw CSV is missing a header row.")

    redbook_payload = json.loads(args.redbook_input.read_text(encoding="utf-8"))
    if not isinstance(redbook_payload, list):
        raise ValueError("Redbook JSON must be a top-level list.")

    required_extra_fields = ["redbook_page", "redbook_index"]
    fieldnames = existing_fieldnames[:]
    for name in required_extra_fields:
        if name not in fieldnames:
            fieldnames.append(name)

    existing_words = {clean_word(row.get("word", "")) for row in existing_rows if clean_word(row.get("word", ""))}
    appended_rows = []
    seen_redbook_only = set()

    for item in redbook_payload:
        word = clean_word(item.get("word", ""))
        if not word or word in existing_words or word in seen_redbook_only:
            continue

        pos, meaning = extract_pos_and_meaning(str(item.get("meaning", "")))
        if not meaning:
            continue

        row = {
            "word": word,
            "pos": pos,
            "meaning": meaning,
            "example": "",
            "frequency": "",
            "source_rank": "",
            "other_spellings": "",
            "source_dataset": REDBOOK_SOURCE,
            "redbook_page": item.get("page", ""),
            "redbook_index": item.get("index", ""),
        }

        normalized_row = {}
        for field in fieldnames:
            normalized_row[field] = row.get(field, "")

        appended_rows.append(normalized_row)
        seen_redbook_only.add(word)

    ensure_parent(args.output)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing_rows:
            normalized = {field: row.get(field, "") for field in fieldnames}
            writer.writerow(normalized)
        writer.writerows(appended_rows)

    metadata = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "main_input": str(args.main_input),
        "redbook_input": str(args.redbook_input),
        "output": str(args.output),
        "existing_row_count": len(existing_rows),
        "appended_redbook_only_count": len(appended_rows),
        "output_row_count": len(existing_rows) + len(appended_rows),
        "redbook_source_dataset": REDBOOK_SOURCE,
    }
    ensure_parent(args.metadata_output)
    args.metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Appended {len(appended_rows)} redbook-only rows into {args.output}")
    print(f"Wrote merge metadata to {args.metadata_output}")


if __name__ == "__main__":
    main()
