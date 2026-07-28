"""
Runs the unmodified base model (prompting-only, one-shot) against a test split
and scores it with the shared eval harness.
Run as: python -m app.eval.run_baseline --split id_test
"""

import argparse
import json
from pathlib import Path

import requests

from app.eval.eval_harness import score_item, aggregate_scores

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b-instruct"

ONE_SHOT_EXAMPLE_INPUT = """### Impact
A network attacker who can reach an etcd TLS listener can open many TCP connections and never send a ClientHello, exhausting server memory.

### Patches
Patched in etcd 3.7.1, 3.6.14, 3.5.33."""

ONE_SHOT_EXAMPLE_OUTPUT = json.dumps({
    "vulnerabilities": [{
        "cve_id": None,
        "affected_products": [{"vendor": "GO", "product": "go.etcd.io/etcd/v3", "version_range": "< 3.5.33"}],
        "cwe_category": "Allocation of Resources Without Limits or Throttling",
        "severity": "high",
        "attack_vector": "network",
        "impact_summary": "A network attacker can exhaust etcd server memory by opening many TCP connections without completing the TLS handshake, causing loss of availability.",
        "remediation_action": "Upgrade to etcd 3.7.1, 3.6.14, or 3.5.33."
    }]
})

PROMPT_TEMPLATE = """Extract structured vulnerability information from the security advisory text below into JSON matching this exact schema:
{{"vulnerabilities": [{{"cve_id": string or null, "affected_products": [{{"vendor": string, "product": string, "version_range": string or null}}], "cwe_category": string or null, "severity": "low"|"medium"|"high"|"critical", "attack_vector": "network"|"adjacent"|"local"|"physical"|"unknown", "impact_summary": string (max 400 chars), "remediation_action": string or null}}]}}

Example:
Input: {example_input}
Output: {example_output}

Now extract from this advisory:
Input: {input_text}
Output (JSON only, no markdown fences, no preamble):"""


def run_model(input_text: str) -> str:
    prompt = PROMPT_TEMPLATE.format(
        example_input=ONE_SHOT_EXAMPLE_INPUT,
        example_output=ONE_SHOT_EXAMPLE_OUTPUT,
        input_text=input_text[:4000],
    )
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["id_test", "ood_test"], required=True)
    args = parser.parse_args()

    data = json.loads(Path(f"data/splits/{args.split}.json").read_text(encoding="utf-8"))

    scores = []
    for i, item in enumerate(data, start=1):
        raw_output = run_model(item["input_text"])
        score = score_item(item["source_ghsa_id"], raw_output, item["label"])
        scores.append(score)
        status = "OK" if score.schema_valid else f"INVALID ({score.parse_error})"
        print(f"  [{i}/{len(data)}] {item['source_ghsa_id']}: {status}")

    results = aggregate_scores(scores)

    out_path = Path(f"data/eval_results/baseline_{args.split}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\n--- Baseline results on {args.split} ---")
    print(json.dumps(results, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()