"""
Builds DPO chosen/rejected preference pairs from sampled candidates, using
the existing groundedness checker as the automated labeler (not an LLM judge).
Run as: python -m app.train_dpo.build_pairs --input data/preference/pilot_candidates.json
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from app.serving.groundedness import check_groundedness
from app.eval.eval_harness import try_parse

CURRENT_YEAR = datetime.now().year


def extract_cve_year(extraction: dict) -> int | None:
    for vuln in extraction.get("vulnerabilities", []):
        cve_id = vuln.get("cve_id")
        if cve_id:
            match = re.search(r"CVE-(\d{4})-", cve_id)
            if match:
                return int(match.group(1))
    return None


def score_candidate(raw_candidate: str, source_text: str) -> dict:
    """
    Returns a score dict: lower is better (more grounded).
    Adds a large penalty for impossible future-dated CVE IDs — a free,
    zero-cost groundedness signal independent of the main checker.
    """
    result, error = try_parse(raw_candidate)
    if result is None:
        return {"valid": False, "warning_count": 999, "raw": raw_candidate, "parsed": None}

    extraction = result.model_dump()
    checked, warnings = check_groundedness(extraction, source_text)

    cve_year = extract_cve_year(checked)
    future_cve_penalty = 100 if (cve_year and cve_year > CURRENT_YEAR) else 0

    return {
        "valid": True,
        "warning_count": len(warnings) + future_cve_penalty,
        "warnings": warnings,
        "raw": raw_candidate,
        "parsed": checked,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, default="data/preference/pairs.json")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))

    pairs = []
    skipped_no_signal = 0
    skipped_all_invalid = 0

    for item in data:
        scored = [score_candidate(c, item["input_text"]) for c in item["candidates"]]
        valid_scored = [s for s in scored if s["valid"]]

        if not valid_scored:
            skipped_all_invalid += 1
            continue

        valid_scored.sort(key=lambda s: s["warning_count"])
        best = valid_scored[0]
        worst = valid_scored[-1]

        if best["warning_count"] == worst["warning_count"]:
            skipped_no_signal += 1
            continue

        QUALITY_FLOOR = 2  # chosen candidate must have at most this many warnings
        if best["warning_count"] > QUALITY_FLOOR:
            skipped_no_signal += 1  # reusing this counter; could split out separately if useful
            continue

        pairs.append({
            "source_ghsa_id": item["source_ghsa_id"],
            "input_text": item["input_text"],
            "chosen": best["raw"],
            "chosen_warning_count": best["warning_count"],
            "rejected": worst["raw"],
            "rejected_warning_count": worst["warning_count"],
            "rejected_warnings": worst.get("warnings", []),
        })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(pairs, indent=2), encoding="utf-8")

    print(f"Total advisories processed: {len(data)}")
    print(f"Pairs built: {len(pairs)}")
    print(f"Skipped (all candidates invalid JSON): {skipped_all_invalid}")
    print(f"Skipped (no groundedness signal — all candidates equally grounded): {skipped_no_signal}")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()