"""
Analyzes CWE category and ecosystem distribution across the verified dataset,
to decide what to hold out for the stratified test split.
Run as: python -m app.data_pipeline.analyze_distribution
"""

import json
from collections import Counter
from pathlib import Path


def main():
    data = json.loads(Path("data/clean/verified_dataset.json").read_text(encoding="utf-8"))

    cwe_counter = Counter()
    ecosystem_counter = Counter()

    for item in data:
        vuln = item["label"]["vulnerabilities"][0]
        cwe = vuln.get("cwe_category") or "MISSING"
        cwe_counter[cwe] += 1

        for product in vuln.get("affected_products", []):
            ecosystem_counter[product.get("vendor", "MISSING")] += 1

    print(f"Total examples: {len(data)}\n")

    print("--- CWE category distribution ---")
    for cwe, count in cwe_counter.most_common():
        print(f"  {count:4d}  {cwe}")

    print(f"\n--- Ecosystem distribution (affected_products.vendor) ---")
    for eco, count in ecosystem_counter.most_common():
        print(f"  {count:4d}  {eco}")

    print(f"\nUnique CWE categories: {len(cwe_counter)}")
    print(f"Unique ecosystems: {len(ecosystem_counter)}")


if __name__ == "__main__":
    main()