"""
Measures actual token lengths of prompt/chosen/rejected across all 124 pairs,
so max_length settings are based on real data, not guesses.
Run as: python -m app.train_dpo.inspect_lengths
"""

import json
from pathlib import Path

from unsloth import FastLanguageModel

from app.train_dpo.format_dpo_dataset import build_prompt_text

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"


def main():
    print("Loading tokenizer...")
    _, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH, max_seq_length=2048, dtype=None, load_in_4bit=True,
    )

    pairs = json.loads(Path("data/preference/pairs.json").read_text(encoding="utf-8"))

    prompt_lens, chosen_lens, rejected_lens, total_lens = [], [], [], []

    for p in pairs:
        prompt = build_prompt_text(tokenizer, p["input_text"])
        prompt_len = len(tokenizer(prompt)["input_ids"])
        chosen_len = len(tokenizer(p["chosen"])["input_ids"])
        rejected_len = len(tokenizer(p["rejected"])["input_ids"])

        prompt_lens.append(prompt_len)
        chosen_lens.append(chosen_len)
        rejected_lens.append(rejected_len)
        total_lens.append(prompt_len + max(chosen_len, rejected_len))

    def stats(name, values):
        values_sorted = sorted(values)
        n = len(values_sorted)
        print(f"{name}: min={values_sorted[0]}, max={values_sorted[-1]}, "
              f"median={values_sorted[n//2]}, p90={values_sorted[int(n*0.9)]}, p99={values_sorted[min(int(n*0.99), n-1)]}")

    print(f"\nTotal pairs: {len(pairs)}\n")
    stats("Prompt length", prompt_lens)
    stats("Chosen length", chosen_lens)
    stats("Rejected length", rejected_lens)
    stats("Total (prompt + max(chosen,rejected))", total_lens)

    # Flag the actual worst offenders by name
    worst = sorted(zip(pairs, total_lens), key=lambda x: -x[1])[:5]
    print("\nTop 5 longest examples:")
    for p, length in worst:
        print(f"  {p['source_ghsa_id']}: {length} tokens")


if __name__ == "__main__":
    main()