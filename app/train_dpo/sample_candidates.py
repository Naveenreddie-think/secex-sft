"""
Pilot run: samples multiple candidate extractions per advisory from the
SFT model (base + adapter, not merged) at temperature > 0, to check
whether enough diversity emerges to build DPO preference pairs from.
Run as: python -m app.train_dpo.sample_candidates --limit 15
"""

import argparse
import json
from pathlib import Path

from unsloth import FastLanguageModel

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
MAX_SEQ_LENGTH = 2048
NUM_CANDIDATES = 6
TEMPERATURE = 0.8

SYSTEM_INSTRUCTION = """Extract structured vulnerability information from the security advisory text into JSON matching this exact schema:
{"vulnerabilities": [{"cve_id": string or null, "affected_products": [{"vendor": string, "product": string, "version_range": string or null}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}]}

Return ONLY valid JSON, no markdown fences, no preamble."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    print("Loading base model + SFT adapter...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    data = json.loads(Path("data/splits/train.json").read_text(encoding="utf-8"))[: args.limit]

    results = []
    for i, item in enumerate(data, start=1):
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": item["input_text"][:4000]},
        ]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to("cuda")

        outputs = model.generate(
            **inputs,
            max_new_tokens=500,
            temperature=TEMPERATURE,
            do_sample=True,
            num_return_sequences=NUM_CANDIDATES,
        )

        candidates = [
            tokenizer.decode(out[inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            for out in outputs
        ]

        results.append({
            "source_ghsa_id": item["source_ghsa_id"],
            "input_text": item["input_text"],
            "gold_label": item["label"],
            "candidates": candidates,
        })

        print(f"  [{i}/{len(data)}] {item['source_ghsa_id']}: generated {len(candidates)} candidates")

    out_path = Path("data/preference/pilot_candidates.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()