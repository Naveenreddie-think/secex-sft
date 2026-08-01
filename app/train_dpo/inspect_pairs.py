"""
Eyeball a few built pairs to sanity-check that "chosen" is genuinely better
than "rejected", not just an artifact of the scoring logic.
Run as: python -m app.train_dpo.inspect_pairs --input data/preference/pilot_pairs.json
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    pairs = json.loads(Path(args.input).read_text(encoding="utf-8"))

    for p in pairs[: args.count]:
        print("=" * 80)
        print(p["source_ghsa_id"])
        print(f"\nCHOSEN (warnings={p['chosen_warning_count']}):")
        print(p["chosen"][:400])
        print(f"\nREJECTED (warnings={p['rejected_warning_count']}):")
        print(p["rejected"][:400])
        print(f"\nRejected warnings: {p['rejected_warnings']}")
        print()


if __name__ == "__main__":
    main()