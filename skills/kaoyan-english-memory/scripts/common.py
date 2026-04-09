import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]

RAW_WORDS_PATH = ROOT / "data" / "raw" / "kaoyan_words.csv"
STATE_DIR = ROOT / "data" / "state"
LEARNING_PROGRESS_PATH = STATE_DIR / "learning_progress.json"
SCENES_PATH = ROOT / "config" / "scenes.json"
ACTION_CHAINS_PATH = ROOT / "config" / "action_chains.json"
CONTRAST_PAIRS_PATH = ROOT / "config" / "contrast_pairs.json"
BASIC_WORDS_PATH = ROOT / "config" / "basic_words.txt"
SCENE_KEYWORDS_PATH = ROOT / "config" / "scene_keywords.json"
DAILY_PLAN_CONFIG_PATH = ROOT / "config" / "daily_plan.json"
WORDS_OUTPUT_PATH = ROOT / "kb" / "words.jsonl"
SCENE_UNITS_OUTPUT_PATH = ROOT / "kb" / "scene_units.jsonl"
STUDY_WORDS_OUTPUT_PATH = ROOT / "kb" / "study_words.jsonl"
BASIC_WORDS_OUTPUT_PATH = ROOT / "kb" / "basic_words.jsonl"
SCENE_WORDS_OUTPUT_PATH = ROOT / "kb" / "scene_words.jsonl"
CONTRAST_WORDS_OUTPUT_PATH = ROOT / "kb" / "contrast_words.jsonl"
STANDARD_WORDS_OUTPUT_PATH = ROOT / "kb" / "standard_words.jsonl"
LEARNING_ROUTE_REPORT_OUTPUT_PATH = ROOT / "kb" / "learning_route_report.json"
DAILY_PLAN_SAMPLE_JSON_PATH = ROOT / "kb" / "daily_plan_sample.json"
DAILY_PLAN_SAMPLE_MD_PATH = ROOT / "kb" / "daily_plan_sample.md"

MEANING_SPLIT_RE = re.compile(r"[;；]+")
POS_TOKEN_RE = re.compile(r"[A-Za-z]+\.")

WORD_SCORE_OVERRIDES = {
    "attempt": {"difficulty": 2, "importance": 4},
    "pursue": {"difficulty": 3, "importance": 4},
    "obstacle": {"difficulty": 3, "importance": 4},
    "suspend": {"difficulty": 4, "importance": 4},
    "abandon": {"difficulty": 3, "importance": 5},
    "adapt": {"difficulty": 3, "importance": 5},
    "adopt": {"difficulty": 3, "importance": 5},
}

CORE_HIGH_FREQUENCY_MIN_FREQUENCY = 40


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_basic_words(path: Path) -> set:
    words = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            words.add(clean_word(text))
    return words


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def clean_word(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _meaning_contains_keyword(meanings: List[str], keywords: List[str]) -> bool:
    for meaning in meanings:
        for keyword in keywords:
            if keyword and keyword in meaning:
                return True
    return False


def _word_matches_keyword(word: str, keywords: List[str]) -> bool:
    for keyword in keywords:
        cleaned = clean_word(keyword)
        if not cleaned:
            continue
        if word == cleaned:
            return True
        if " " not in cleaned and "-" not in cleaned and word.startswith(cleaned):
            return True
    return False


def split_meanings(value: str) -> List[str]:
    text = (value or "").strip()
    if not text:
        return []
    parts = [part.strip() for part in MEANING_SPLIT_RE.split(text)]
    return [part for part in parts if part]


def split_pos(value: str) -> List[str]:
    text = (value or "").strip()
    if not text:
        return []
    tokens = POS_TOKEN_RE.findall(text)
    return tokens or [text]


def _merge_entries(existing: dict, incoming: dict) -> dict:
    if not existing["pos"] and incoming["pos"]:
        existing["pos"] = incoming["pos"]
        existing["pos_summary"] = incoming["pos_summary"]
    if not existing["example"] and incoming["example"]:
        existing["example"] = incoming["example"]
    for meaning in incoming["meaning_zh"]:
        if meaning not in existing["meaning_zh"]:
            existing["meaning_zh"].append(meaning)
    if not existing["meaning"] and incoming["meaning"]:
        existing["meaning"] = incoming["meaning"]
    return existing


def load_raw_words(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")
        required = {"word", "meaning"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV file is missing required columns: {sorted(missing)}")

        deduped: Dict[str, dict] = {}
        for row in reader:
            word = clean_word(row.get("word", ""))
            if not word:
                continue
            normalized = {
                "word": word,
                "pos": (row.get("pos") or "").strip(),
                "meaning": (row.get("meaning") or "").strip(),
                "example": (row.get("example") or "").strip(),
                "frequency": (row.get("frequency") or "").strip(),
                "source_rank": (row.get("source_rank") or "").strip(),
                "other_spellings": (row.get("other_spellings") or "").strip(),
                "source_dataset": (row.get("source_dataset") or "").strip(),
            }
            normalized["meaning_zh"] = split_meanings(normalized["meaning"])
            normalized["pos_summary"] = split_pos(normalized["pos"])
            if not normalized["meaning_zh"]:
                continue
            if word in deduped:
                deduped[word] = _merge_entries(deduped[word], normalized)
            else:
                deduped[word] = normalized
        return list(deduped.values())


def estimate_difficulty(word: str, meanings: List[str]) -> int:
    if word in WORD_SCORE_OVERRIDES:
        return WORD_SCORE_OVERRIDES[word]["difficulty"]

    score = 2
    if len(word) >= 8:
        score += 1
    if len(word) >= 10:
        score += 1
    if any(len(item) >= 6 for item in meanings):
        score += 1
    return min(score, 5)


def estimate_importance(word: str, scene_tags: List[str], is_core_word: bool, in_contrast_pair: bool) -> int:
    if word in WORD_SCORE_OVERRIDES:
        return WORD_SCORE_OVERRIDES[word]["importance"]

    score = 3
    if scene_tags:
        score += 1
    if is_core_word or in_contrast_pair:
        score += 1
    return min(score, 5)


def build_scene_membership(action_chains: List[dict]) -> Dict[str, List[str]]:
    membership: Dict[str, List[str]] = {}
    for chain in action_chains:
        scene_id = chain["scene_id"]
        for bucket in ("core_words", "support_words"):
            for word in chain.get(bucket, []):
                membership.setdefault(clean_word(word), [])
                if scene_id not in membership[clean_word(word)]:
                    membership[clean_word(word)].append(scene_id)
    return membership


def infer_scene_tags(
    word: str,
    meanings: List[str],
    scenes: List[dict],
    action_chains: List[dict],
    contrast_pairs: List[List[str]],
    scene_keywords: Dict[str, dict],
) -> List[str]:
    tags: List[str] = []
    chain_membership = build_scene_membership(action_chains)
    for scene in scenes:
        scene_id = scene["scene_id"]
        anchor_words = [clean_word(item) for item in scene.get("anchor_words", [])]
        if word in anchor_words or scene_id in chain_membership.get(word, []):
            if scene_id not in tags:
                tags.append(scene_id)
            continue

        keyword_config = scene_keywords.get(scene_id, {})
        word_keywords = keyword_config.get("word_keywords", [])
        meaning_keywords = keyword_config.get("meaning_keywords", [])
        if _word_matches_keyword(word, word_keywords) or _meaning_contains_keyword(meanings, meaning_keywords):
            if scene_id not in tags:
                tags.append(scene_id)

    if not tags:
        in_pair = any(word in [clean_word(item) for item in pair] for pair in contrast_pairs if len(pair) == 2)
        if in_pair:
            tags.append("comparison_choice_evaluation")
    return tags


def is_core_word(word: str, action_chains: List[dict]) -> bool:
    for chain in action_chains:
        if word in [clean_word(item) for item in chain.get("core_words", [])]:
            return True
    return False


def in_contrast_pair(word: str, contrast_pairs: List[List[str]]) -> bool:
    for pair in contrast_pairs:
        if word in [clean_word(item) for item in pair]:
            return True
    return False


def get_contrast_partners(word: str, contrast_pairs: List[List[str]]) -> List[str]:
    partners = []
    for pair in contrast_pairs:
        cleaned = [clean_word(item) for item in pair if item]
        if len(cleaned) != 2:
            continue
        if cleaned[0] == word and cleaned[1] not in partners:
            partners.append(cleaned[1])
        elif cleaned[1] == word and cleaned[0] not in partners:
            partners.append(cleaned[0])
    return partners
