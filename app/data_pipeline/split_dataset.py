"""
Creates stratified train/val/test splits, holding out an entire CWE category
for a separate out-of-distribution (OOD) test set.
Run as: python -m app.data_pipeline.split_dataset
"""

import json
import random
from collections import defaultdict
from pathlib import Path

OOD_HELDOUT_CWE = "Uncontrolled Resource Consumption"
RANDOM_SEED = 42
VAL_FRACTION = 0.10
TEST_FRACTION = 0.10


def main():
    random.seed(RANDOM_SEED)

    data = json.loads(Path("data/clean/verified_dataset.json").read_text(encoding="utf-8"))

    ood_test = []
    remaining = []

    for item in data:
        cwe = item["label"]["vulnerabilities"][0].get("cwe_category")
        if cwe == OOD_HELDOUT_CWE:
            ood_test.append(item)
        else:
            remaining.append(item)

    # Stratify remaining by severity
    by_severity = defaultdict(list)
    for item in remaining:
        sev = item["label"]["vulnerabilities"][0]["severity"]
        by_severity[sev].append(item)

    train, val, id_test = [], [], []

    for sev, items in by_severity.items():
        random.shuffle(items)
        n = len(items)
        n_val = max(1, round(n * VAL_FRACTION))
        n_test = max(1, round(n * TEST_FRACTION))

        val.extend(items[:n_val])
        id_test.extend(items[n_val:n_val + n_test])
        train.extend(items[n_val + n_test:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(id_test)

    out_dir = Path("data/splits")
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "train.json").write_text(json.dumps(train, indent=2), encoding="utf-8")
    (out_dir / "val.json").write_text(json.dumps(val, indent=2), encoding="utf-8")
    (out_dir / "id_test.json").write_text(json.dumps(id_test, indent=2), encoding="utf-8")
    (out_dir / "ood_test.json").write_text(json.dumps(ood_test, indent=2), encoding="utf-8")

    print(f"Train:            {len(train)}")
    print(f"Val:              {len(val)}")
    print(f"In-distribution test: {len(id_test)}")
    print(f"OOD test ('{OOD_HELDOUT_CWE}'): {len(ood_test)}")
    print(f"Total: {len(train) + len(val) + len(id_test) + len(ood_test)} (should equal {len(data)})")

    # Sanity check: confirm OOD category never leaked into train
    train_cwes = {item["label"]["vulnerabilities"][0].get("cwe_category") for item in train}
    print(f"\nOOD category present in train set: {OOD_HELDOUT_CWE in train_cwes} (should be False)")


if __name__ == "__main__":
    main()