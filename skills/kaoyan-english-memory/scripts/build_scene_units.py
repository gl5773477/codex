import argparse
from pathlib import Path

from common import (
    ACTION_CHAINS_PATH,
    CONTRAST_PAIRS_PATH,
    SCENES_PATH,
    SCENE_UNITS_OUTPUT_PATH,
    WORDS_OUTPUT_PATH,
    clean_word,
    load_json,
    read_jsonl,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build kb/scene_units.jsonl from word and config data.")
    parser.add_argument("--words", type=Path, default=WORDS_OUTPUT_PATH, help="Path to words.jsonl.")
    parser.add_argument("--scenes", type=Path, default=SCENES_PATH, help="Path to scenes.json.")
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
        "--output",
        type=Path,
        default=SCENE_UNITS_OUTPUT_PATH,
        help="Path to scene_units.jsonl.",
    )
    return parser.parse_args()


def _normalize_pair(pair):
    if len(pair) != 2:
        return None
    return [clean_word(pair[0]), clean_word(pair[1])]


def main() -> None:
    args = parse_args()
    words = read_jsonl(args.words)
    scenes = load_json(args.scenes)
    action_chains = load_json(args.action_chains)
    contrast_pairs = load_json(args.contrast_pairs)

    valid_scene_ids = {scene["scene_id"] for scene in scenes}
    available_words = {row["word_id"] for row in words if row.get("learning_enabled", True)}
    normalized_pairs = []
    for pair in contrast_pairs:
        normalized = _normalize_pair(pair)
        if normalized and all(item in available_words for item in normalized):
            normalized_pairs.append(normalized)

    rows = []
    counter = 1
    for chain in action_chains:
        scene_id = chain["scene_id"]
        if scene_id not in valid_scene_ids:
            continue

        core_words = []
        for word in chain.get("core_words", []):
            cleaned = clean_word(word)
            if cleaned in available_words and cleaned not in core_words:
                core_words.append(cleaned)

        if len(core_words) < 4:
            continue

        support_words = []
        for word in chain.get("support_words", []):
            cleaned = clean_word(word)
            if cleaned in available_words and cleaned not in core_words and cleaned not in support_words:
                support_words.append(cleaned)
            if len(support_words) >= 5:
                break

        unit_words = set(core_words) | set(support_words)
        relevant_pairs = []
        for pair in normalized_pairs:
            if pair[0] in unit_words or pair[1] in unit_words:
                relevant_pairs.append(pair)
            if len(relevant_pairs) >= 2:
                break

        rows.append(
            {
                "unit_id": f"u{counter:03d}",
                "scene_id": scene_id,
                "title": chain["title"],
                "core_words": core_words[:5],
                "support_words": support_words[:5],
                "contrast_pairs": relevant_pairs,
                "memory_chain": chain["memory_chain"],
                "difficulty": chain.get("difficulty", 3),
            }
        )
        counter += 1

    write_jsonl(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
