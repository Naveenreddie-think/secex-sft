"""
Random spot-check of verified dataset quality before committing to training use.
Run as: python -m app.data_pipeline.spot_check
"""

import json
import random
from pathlib import Path


def main():
    data = json.loads(Path("data/clean/verified_dataset.json").read_text(encoding="utf-8"))

    sample = random.sample(data, k=min(5, len(data)))

    for item in sample:
        vuln = item["label"]["vulnerabilities"][0]
        print(f"\n{'='*80}")
        print(f"{item['source_ghsa_id']}")
        print(f"{'='*80}")
        print(f"Impact Summary: {vuln['impact_summary']}")
        print(f"Remediation:    {vuln['remediation_action']}")
        print(f"Severity:       {vuln['severity']}  |  Attack Vector: {vuln['attack_vector']}")
        print(f"CWE:            {vuln['cwe_category']}")

    # Flag likely-unreviewed entries (still showing placeholder-style summaries)
    suspect = [
        item for item in data
        if item["label"]["vulnerabilities"][0]["remediation_action"] is None
        or len(item["label"]["vulnerabilities"][0]["impact_summary"]) < 30
    ]
    print(f"\n--- Suspect entries (null remediation or very short impact_summary): {len(suspect)}/{len(data)} ---")
    for s in suspect[:10]:
        print(f"  {s['source_ghsa_id']}")


if __name__ == "__main__":
    main()