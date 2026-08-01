"""
Checks the distribution of rejection reasons across the built pairs —
worth knowing whether rejections are dominated by one failure type
(e.g. always CVE ID) versus a healthy mix, before training DPO on this data.
Run as: python -m app.train_dpo.inspect_distribution
"""

import json
from collections import Counter
from pathlib import Path


def main():
    pairs = json.loads(Path("data/preference/pairs.json").read_text(encoding="utf-8"))

    reason_counter = Counter()
    for p in pairs:
        for w in p["rejected_warnings"]:
            if "cve_id" in w:
                reason_counter["cve_id"] += 1
            elif "version_range" in w:
                reason_counter["version_range"] += 1
            elif "affected_products" in w:
                reason_counter["product_name"] += 1
            elif "still references" in w:
                reason_counter["free_text_leakage"] += 1
            else:
                reason_counter["other"] += 1

    print(f"Total pairs: {len(pairs)}")
    print(f"\nRejection reason distribution (a rejected candidate can have multiple):")
    for reason, count in reason_counter.most_common():
        print(f"  {reason}: {count}")

    chosen_warning_counts = Counter(p["chosen_warning_count"] for p in pairs)
    print(f"\nChosen-candidate warning count distribution:")
    for count, n in sorted(chosen_warning_counts.items()):
        print(f"  {count} warnings: {n} pairs")


if __name__ == "__main__":
    main()