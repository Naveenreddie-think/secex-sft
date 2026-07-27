"""
Maps raw GHSA advisories to the extraction schema, produces noisy-gold labels
for hand verification. Run as: python -m app.data_pipeline.map_to_schema
"""
import json
import re
from pathlib import Path

SEVERITY_MAP = {
    "LOW": "low",
    "MODERATE": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}

AV_MAP = {
    "N": "network",
    "A": "adjacent",
    "L": "local",
    "P": "physical",
}


def parse_attack_vector(vector_string: str | None) -> str:
    if not vector_string:
        return "unknown"
    match = re.search(r"AV:([NALP])", vector_string)
    if not match:
        return "unknown"
    return AV_MAP.get(match.group(1), "unknown")


def extract_cve_id(identifiers: list[dict]) -> str | None:
    for ident in identifiers:
        if ident["type"] == "CVE":
            return ident["value"]
    return None


def summarize_impact(description: str, summary: str) -> str:
    # Placeholder heuristic: use the summary field, truncated to schema limit.
    # This is intentionally naive — real impact_summary quality depends on
    # hand-verification, not automatic derivation from noisy text.
    text = summary.strip()
    return text[:400]


def map_advisory(adv: dict) -> dict:
    vuln_nodes = adv.get("vulnerabilities", {}).get("nodes", [])
    cwe_nodes = adv.get("cwes", {}).get("nodes", [])

    affected_products = [
        {
            "vendor": v["package"]["ecosystem"],
            "product": v["package"]["name"],
            "version_range": v.get("vulnerableVersionRange"),
        }
        for v in vuln_nodes
    ]

    return {
        "source_ghsa_id": adv["ghsaId"],  # kept for traceability, not part of model schema
        "input_text": adv["description"],
        "gold_label": {
            "vulnerabilities": [
                {
                    "cve_id": extract_cve_id(adv.get("identifiers", [])),
                    "affected_products": affected_products,
                    "cwe_category": cwe_nodes[0]["name"] if cwe_nodes else None,
                    "severity": SEVERITY_MAP.get(adv.get("severity"), "medium"),
                    "attack_vector": parse_attack_vector(
                        adv.get("cvss", {}).get("vectorString")
                    ),
                    "impact_summary": summarize_impact(
                        adv["description"], adv["summary"]
                    ),
                    "remediation_action": None,  # needs hand verification — not reliably structured in raw data
                }
            ]
        },
    }


def main():
    raw_path = Path("data/raw/ghsa_advisories.json")
    out_path = Path("data/clean/ghsa_mapped.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    advisories = json.loads(raw_path.read_text(encoding="utf-8"))
    mapped = [map_advisory(a) for a in advisories]

    out_path.write_text(json.dumps(mapped, indent=2), encoding="utf-8")

    unknown_av = sum(
        1 for m in mapped
        if m["gold_label"]["vulnerabilities"][0]["attack_vector"] == "unknown"
    )
    no_cwe = sum(
        1 for m in mapped
        if m["gold_label"]["vulnerabilities"][0]["cwe_category"] is None
    )

    print(f"Mapped {len(mapped)} advisories -> {out_path}")
    print(f"attack_vector = 'unknown' fallback used: {unknown_av}/{len(mapped)}")
    print(f"cwe_category missing: {no_cwe}/{len(mapped)}")


if __name__ == "__main__":
    main()