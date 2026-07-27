"""
Shows mapped examples alongside their original description for manual review.
Run as: python -m app.data_pipeline.review_sample --start 0 --count 5
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    mapped = json.loads(Path("data/clean/ghsa_mapped.json").read_text(encoding="utf-8"))
    subset = mapped[args.start : args.start + args.count]

    for i, item in enumerate(subset, start=args.start):
        vuln = item["gold_label"]["vulnerabilities"][0]
        print(f"\n{'='*80}")
        print(f"[{i}] {item['source_ghsa_id']}")
        print(f"{'='*80}")
        print(f"\n--- ORIGINAL DESCRIPTION ---\n{item['input_text'][:1000]}")
        print(f"\n--- MAPPED LABEL ---")
        print(json.dumps(vuln, indent=2))


if __name__ == "__main__":
    main()