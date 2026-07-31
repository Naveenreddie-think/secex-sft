"""
Investigates the CVE ID accuracy regression after fine-tuning.
Categorizes every prediction: correct, missed (gold has a real CVE, model said null),
hallucinated (gold is null, model invented one), or wrong (both non-null but different).
Run as: python -m app.eval.debug_cve_id --split id_test
"""

import argparse
import json
from pathlib import Path

from unsloth import FastLanguageModel

from app.eval.eval_harness import try_parse

ADAPTER_PATH = "checkpoints/secex_lora_v1/final_adapter"
MAX_SEQ_LENGTH = 2048

SYSTEM_INSTRUCTION = """Extract structured vulnerability information from the security advisory text into JSON matching this exact schema:
{"vulnerabilities": [{"cve_id": string or null, "affected_products": [{"vendor": string, "product": string, "version_range": string or null}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}]}

Return ONLY valid JSON, no markdown fences, no preamble."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["id_test", "ood_test"], required=True)
    args = parser.parse_args()

    print("Loading fine-tuned model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=ADAPTER_PATH, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    data = json.loads(Path(f"data/splits/{args.split}.json").read_text(encoding="utf-8"))

    categories = {"correct": [], "missed": [], "hallucinated": [], "wrong": []}

    for item in data:
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": item["input_text"][:4000]},
        ]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to("cuda")
        outputs = model.generate(**inputs, max_new_tokens=500, temperature=0.0, do_sample=False)
        raw_output = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        result, error = try_parse(raw_output)
        if result is None or not result.vulnerabilities:
            continue

        pred_cve = result.vulnerabilities[0].cve_id
        gold_cve = item["label"]["vulnerabilities"][0].get("cve_id")

        record = {"id": item["source_ghsa_id"], "pred": pred_cve, "gold": gold_cve}

        if pred_cve == gold_cve:
            categories["correct"].append(record)
        elif gold_cve and not pred_cve:
            categories["missed"].append(record)
        elif not gold_cve and pred_cve:
            categories["hallucinated"].append(record)
        else:
            categories["wrong"].append(record)

    print(f"\n--- CVE ID breakdown on {args.split} (n={len(data)}) ---")
    for cat, records in categories.items():
        print(f"\n{cat.upper()}: {len(records)}")
        for r in records:
            print(f"  {r['id']}: pred={r['pred']!r}  gold={r['gold']!r}")


if __name__ == "__main__":
    main()