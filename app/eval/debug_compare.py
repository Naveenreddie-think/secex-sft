"""
Shows predicted vs gold values side-by-side for the schema-valid items,
to distinguish real baseline weakness from a scoring/normalization bug.
Run as: python -m app.eval.debug_compare --split id_test
"""

import argparse
import json
from pathlib import Path

import requests

from app.eval.eval_harness import try_parse
from app.eval.run_baseline import run_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["id_test", "ood_test"], required=True)
    args = parser.parse_args()

    data = json.loads(Path(f"data/splits/{args.split}.json").read_text(encoding="utf-8"))

    for item in data:
        raw_output = run_model(item["input_text"])
        result, error = try_parse(raw_output)

        if result is None:
            continue  # skip invalid ones, we already know why those fail

        predicted = result.vulnerabilities[0]
        gold = item["label"]["vulnerabilities"][0]

        print(f"\n{item['source_ghsa_id']}")
        print(f"  severity:      pred={predicted.severity!r:20} gold={gold['severity']!r}")
        print(f"  attack_vector: pred={predicted.attack_vector!r:20} gold={gold['attack_vector']!r}")
        print(f"  cwe_category:  pred={predicted.cwe_category!r}")
        print(f"                 gold={gold['cwe_category']!r}")


if __name__ == "__main__":
    main()