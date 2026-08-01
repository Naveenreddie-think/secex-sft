"""
Excludes pairs whose combined prompt+completion length exceeds a data-driven
threshold (p90 of the real distribution), rather than guessing a global
truncation length that would cut off most examples' actual content.
Run as: python -m app.train_dpo.filter_by_length
"""

import json
from pathlib import Path

from unsloth import FastLanguageModel

from app.train_dpo.format_dpo_dataset import build_prompt_text

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
LENGTH_THRESHOLD = 1024  # just above p90 (1415), excludes the true long-tail outliers


def main():
    print("Loading tokenizer...")
    _, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH, max_seq_length=2048, dtype=None, load_in_4bit=True,
    )

    pairs = json.loads(Path("data/preference/pairs.json").read_text(encoding="utf-8"))

    kept, excluded = [], []
    for p in pairs:
        prompt = build_prompt_text(tokenizer, p["input_text"])
        prompt_len = len(tokenizer(prompt)["input_ids"])
        chosen_len = len(tokenizer(p["chosen"])["input_ids"])
        rejected_len = len(tokenizer(p["rejected"])["input_ids"])
        total = prompt_len + max(chosen_len, rejected_len)

        if total <= LENGTH_THRESHOLD:
            kept.append(p)
        else:
            excluded.append((p["source_ghsa_id"], total))

    out_path = Path("data/preference/pairs_filtered.json")
    out_path.write_text(json.dumps(kept, indent=2), encoding="utf-8")

    print(f"Kept: {len(kept)}/{len(pairs)} pairs (threshold={LENGTH_THRESHOLD} tokens)")
    print(f"Excluded ({len(excluded)}):")
    for ghsa_id, length in sorted(excluded, key=lambda x: -x[1]):
        print(f"  {ghsa_id}: {length} tokens")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()