"""
Quick look at fetched advisories — run before deciding how to map fields to the schema.
Run as: python -m app.data_pipeline.inspect_raw
"""

import json
from pathlib import Path


def main():
    path = Path("data/raw/ghsa_advisories.json")
    advisories = json.loads(path.read_text(encoding="utf-8"))

    print(f"Total advisories: {len(advisories)}\n")

    for i, adv in enumerate(advisories[:2]):
        print(f"--- Example {i+1}: {adv['ghsaId']} ---")
        print(json.dumps(adv, indent=2)[:1500])
        print()

    severities = [a.get("severity") for a in advisories]
    no_cwe = sum(1 for a in advisories if not a.get("cwes", {}).get("nodes"))
    multi_vuln = sum(1 for a in advisories if len(a.get("vulnerabilities", {}).get("nodes", [])) > 1)
    no_description = sum(1 for a in advisories if not a.get("description"))

    # New: CVE + CVSS coverage checks
    has_cve = sum(
        1 for a in advisories
        if any(ident["type"] == "CVE" for ident in a.get("identifiers", []))
    )
    has_vector_string = sum(
        1 for a in advisories
        if a.get("cvss", {}).get("vectorString")
    )
    has_score_only = sum(
        1 for a in advisories
        if a.get("cvss", {}).get("score") and not a.get("cvss", {}).get("vectorString")
    )

    print("--- Aggregate stats ---")
    print(f"Severity distribution: {json.dumps({s: severities.count(s) for s in set(severities)}, indent=2)}")
    print(f"Advisories with no CWE listed: {no_cwe}/{len(advisories)}")
    print(f"Advisories affecting multiple packages: {multi_vuln}/{len(advisories)}")
    print(f"Advisories with empty description: {no_description}/{len(advisories)}")
    print(f"Advisories with a CVE identifier: {has_cve}/{len(advisories)}")
    print(f"Advisories with a CVSS vector string: {has_vector_string}/{len(advisories)}")
    print(f"Advisories with score but no vector string: {has_score_only}/{len(advisories)}")


if __name__ == "__main__":
    main()