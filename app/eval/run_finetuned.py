"""
Runs the fine-tuned model (base + LoRA adapter) against a test split,
scored with the same harness used for the baseline.
Run as: python -m app.eval.run_finetuned --split id_test
"""

import argparse
import json
from pathlib import Path

from unsloth import FastLanguageModel

from app.eval.eval_harness import score_item, aggregate_scores

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
MAX_SEQ_LENGTH = 2048

SYSTEM_INSTRUCTION = """Extract structured vulnerability information from the security advisory text into JSON matching this exact schema:
{"vulnerabilities": [{"cve_id": string or null, "affected_products": [{"vendor": string, "product": string, "version_range": string or null}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}]}

Return ONLY valid JSON, no markdown fences, no preamble."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["id_test", "ood_test"], required=True)
    args = parser.parse_args()

    print("Loading fine-tuned model (base + LoRA adapter)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    data = json.loads(Path(f"data/splits/{args.split}.json").read_text(encoding="utf-8"))

    scores = []
    for i, item in enumerate(data, start=1):
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": item["input_text"][:4000]},
        ]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to("cuda")

        outputs = model.generate(inputs, max_new_tokens=500, temperature=0.0, do_sample=False)
        raw_output = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

        score = score_item(item["source_ghsa_id"], raw_output, item["label"])
        scores.append(score)
        status = "OK" if score.schema_valid else f"INVALID ({score.parse_error})"
        print(f"  [{i}/{len(data)}] {item['source_ghsa_id']}: {status}")

    results = aggregate_scores(scores)

    out_path = Path(f"data/eval_results/finetuned_{args.split}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\n--- Fine-tuned results on {args.split} ---")
    print(json.dumps(results, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()