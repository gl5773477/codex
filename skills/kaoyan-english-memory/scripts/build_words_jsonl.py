import argparse
from pathlib import Path

from common import (
    ACTION_CHAINS_PATH,
    BASIC_WORDS_PATH,
    CONTRAST_PAIRS_PATH,
    RAW_WORDS_PATH,
    SCENE_KEYWORDS_PATH,
    SCENES_PATH,
    WORDS_OUTPUT_PATH,
    estimate_difficulty,
    estimate_importance,
    get_contrast_partners,
    in_contrast_pair,
    infer_scene_tags,
    is_core_word,
    load_basic_words,
    load_json,
    load_raw_words,
    write_jsonl,
)


def infer_learning_mode(is_basic: bool, scene_tags: list[str], contrast_partners: list[str]) -> tuple[str, str]:
    if is_basic:
        return "basic", "listed in basic_words"
    if contrast_partners:
        return "contrast", "explicit contrast pair"
    if scene_tags:
        return "scene", "matched scene tags"
    return "standard", "fallback standard learning"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build kb/words.jsonl from the raw CSV.")
    parser.add_argument("--input", type=Path, default=RAW_WORDS_PATH, help="Path to the raw CSV file.")
    parser.add_argument("--scenes", type=Path, default=SCENES_PATH, help="Path to scenes.json.")
    parser.add_argument(
        "--scene-keywords",
        type=Path,
        default=SCENE_KEYWORDS_PATH,
        help="Path to scene_keywords.json.",
    )
    parser.add_argument(
        "--action-chains",
        type=Path,
        default=ACTION_CHAINS_PATH,
        help="Path to action_chains.json.",
    )
    parser.add_argument(
        "--contrast-pairs",
        type=Path,
        default=CONTRAST_PAIRS_PATH,
        help="Path to contrast_pairs.json.",
    )
    parser.add_argument(
        "--basic-words",
        type=Path,
        default=BASIC_WORDS_PATH,
        help="Path to basic_words.txt.",
    )
    parser.add_argument("--output", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenes = load_json(args.scenes)
    scene_keywords = load_json(args.scene_keywords)
    action_chains = load_json(args.action_chains)
    contrast_pairs = load_json(args.contrast_pairs)
    basic_words = load_basic_words(args.basic_words)
    words = load_raw_words(args.input)

    rows = []
    for item in words:
        word = item["word"]
        scene_tags = infer_scene_tags(word, item["meaning_zh"], scenes, action_chains, contrast_pairs, scene_keywords)
        is_basic = word in basic_words
        contrast_partners = get_contrast_partners(word, contrast_pairs)
        learning_mode, learning_reason = infer_learning_mode(is_basic, scene_tags, contrast_partners)
        row = {
            "word_id": word,
            "lemma": word,
            "headword": word,
            "pos_summary": item["pos_summary"],
            "meaning_zh": item["meaning_zh"],
            "example": item["example"],
            "frequency": int(item["frequency"]) if item.get("frequency") else None,
            "source_rank": int(item["source_rank"]) if item.get("source_rank") else None,
            "other_spellings": item.get("other_spellings") or "",
            "source_dataset": item.get("source_dataset") or "",
            "difficulty": estimate_difficulty(word, item["meaning_zh"]),
            "importance": estimate_importance(
                word,
                scene_tags,
                is_core_word(word, action_chains),
                in_contrast_pair(word, contrast_pairs),
            ),
            "scene_tags": scene_tags,
            "contrast_partners": contrast_partners,
            "is_basic": is_basic,
            "learning_enabled": not is_basic,
            "learning_mode": learning_mode,
            "learning_reason": learning_reason,
        }
        rows.append(row)

    write_jsonl(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
