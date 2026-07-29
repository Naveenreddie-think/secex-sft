"""
Post-processing safety layer: verifies that specific claims in a model's
extraction (CVE ID, product names) actually appear in the source text.
Ungrounded specifics are nulled out rather than trusted, and flagged.
"""

import re


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _appears_in_source(value: str | None, source_text: str) -> bool:
    if not value:
        return True  # nothing to check
    normalized_value = _normalize(value)
    normalized_source = _normalize(source_text)
    if len(normalized_value) < 3:
        return True  # too short to meaningfully check, don't penalize
    return normalized_value in normalized_source


def check_groundedness(extraction: dict, source_text: str) -> tuple[dict, list[str]]:
    """
    Checks each vulnerability entry's specific claims against the source text.
    Returns a (possibly modified) extraction dict and a list of warning strings.
    Ungrounded cve_id and affected_products entries are nulled/dropped.
    """
    warnings = []
    vulns = extraction.get("vulnerabilities", [])

    for i, vuln in enumerate(vulns):
        cve_id = vuln.get("cve_id")
        if cve_id and not _appears_in_source(cve_id, source_text):
            warnings.append(
                f"vulnerabilities[{i}].cve_id ('{cve_id}') not found in source text — nulled out"
            )
            vuln["cve_id"] = None

        grounded_products = []
        for product in vuln.get("affected_products", []):
            product_name = product.get("product", "")
            if _appears_in_source(product_name, source_text):
                grounded_products.append(product)
            else:
                warnings.append(
                    f"vulnerabilities[{i}].affected_products entry ('{product_name}') "
                    f"not found in source text — dropped"
                )

        vuln["affected_products"] = grounded_products

    return extraction, warnings