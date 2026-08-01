"""
Checks how much the sampled candidates actually diverge per advisory —
if all 6 candidates are near-identical, temperature/sampling needs adjusting
before committing to the full 146-advisory run.
Run as: python -m app.train_dpo.inspect_diversity
"""

import json
from pathlib import Path


def main():
    data = json.loads(Path("data/preference/pilot_candidates.json").read_text(encoding="utf-8"))

    for item in data[:3]:  # deep-dive on first 3 advisories
        print(f"\n{'='*80}")
        print(f"{item['source_ghsa_id']}")
        print(f"{'='*80}")
        for i, cand in enumerate(item["candidates"], start=1):
            print(f"\n--- Candidate {i} ---")
            print(cand[:400])

    # Aggregate: how many advisories have candidates that are all identical?
    identical_count = 0
    for item in data:
        unique_candidates = set(item["candidates"])
        if len(unique_candidates) == 1:
            identical_count += 1

    print(f"\n\n--- Diversity summary ---")
    print(f"Advisories where all {len(data[0]['candidates'])} candidates were identical: {identical_count}/{len(data)}")

    avg_unique = sum(len(set(item["candidates"])) for item in data) / len(data)
    print(f"Average unique candidates per advisory: {avg_unique:.2f} / {len(data[0]['candidates'])}")


if __name__ == "__main__":
    main()