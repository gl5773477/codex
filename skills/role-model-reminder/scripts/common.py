import json
import re
from hashlib import sha1
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]

PEOPLE_PATH = ROOT / "config" / "people.json"
SEED_MATERIALS_PATH = ROOT / "data" / "seed" / "materials.json"
INBOX_DIR = ROOT / "data" / "inbox"
CURATED_MATERIALS_PATH = ROOT / "data" / "curated" / "materials.json"
PUSH_HISTORY_PATH = ROOT / "data" / "state" / "push_history.json"
MATERIAL_COVERAGE_PATH = ROOT / "kb" / "material_coverage.json"
REMINDER_CANDIDATES_PATH = ROOT / "kb" / "reminder_candidates.jsonl"

REQUIRED_FIELDS = {
    "person_id",
    "person_name",
    "material_type",
    "title",
    "summary",
    "principle",
    "reminder",
    "reflection_question",
    "tags",
    "source_hint",
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "item"


def make_material_id(record: dict) -> str:
    if record.get("id"):
        return str(record["id"]).strip()
    base = f"{record['person_id']}::{record['title']}::{record['reminder']}"
    digest = sha1(base.encode("utf-8")).hexdigest()[:10]
    title_slug = slugify(record["title"])
    return f"{record['person_id']}-{title_slug}-{digest}"


def normalize_material(record: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"Material is missing required fields: {missing}")

    material_type = str(record["material_type"]).strip().lower()
    if material_type not in {"story", "thought"}:
        raise ValueError(f"material_type must be 'story' or 'thought', got {record['material_type']!r}")

    tags = record["tags"]
    if not isinstance(tags, list) or not all(str(item).strip() for item in tags):
        raise ValueError("tags must be a non-empty list of strings")

    normalized = {
        "id": "",
        "person_id": str(record["person_id"]).strip(),
        "person_name": str(record["person_name"]).strip(),
        "material_type": material_type,
        "title": str(record["title"]).strip(),
        "summary": str(record["summary"]).strip(),
        "principle": str(record["principle"]).strip(),
        "reminder": str(record["reminder"]).strip(),
        "reflection_question": str(record["reflection_question"]).strip(),
        "tags": sorted({str(item).strip() for item in tags if str(item).strip()}),
        "source_hint": str(record["source_hint"]).strip(),
    }
    story_case = str(record.get("story_case", "")).strip()
    if story_case:
        normalized["story_case"] = story_case
    story_vignette = str(record.get("story_vignette", "")).strip()
    if story_vignette:
        normalized["story_vignette"] = story_vignette
    if not all(normalized[key] for key in normalized if key not in {"id", "tags"}):
        raise ValueError(f"Material contains blank fields: {normalized}")
    normalized["id"] = make_material_id({**normalized, "id": record.get("id")})
    return normalized


def load_material_records(path: Path) -> List[dict]:
    payload = load_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("materials"), list):
        return payload["materials"]
    raise ValueError(f"Unsupported material file format: {path}")
