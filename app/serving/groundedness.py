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
    warnings = []
    vulns = extraction.get("vulnerabilities", [])

    for i, vuln in enumerate(vulns):
        ungrounded_entities = []

        cve_id = vuln.get("cve_id")
        if cve_id and not _appears_in_source(cve_id, source_text):
            warnings.append(
                f"vulnerabilities[{i}].cve_id ('{cve_id}') not found in source text — nulled out"
            )
            ungrounded_entities.append(cve_id)
            vuln["cve_id"] = None

        grounded_products = []
        for product in vuln.get("affected_products", []):
            product_name = product.get("product", "")
            if not _appears_in_source(product_name, source_text):
                warnings.append(
                    f"vulnerabilities[{i}].affected_products entry ('{product_name}') "
                    f"not found in source text — dropped"
                )
                ungrounded_entities.append(product_name)
                continue

            version_range = product.get("version_range")
            if version_range and not _appears_in_source(version_range, source_text):
                warnings.append(
                    f"vulnerabilities[{i}].affected_products['{product_name}'].version_range "
                    f"('{version_range}') not found in source text — nulled out"
                )
                ungrounded_entities.append(version_range)
                product["version_range"] = None

            grounded_products.append(product)

        vuln["affected_products"] = grounded_products

        # Check free-text fields for leakage of the same ungrounded entities
        for field_name in ("impact_summary", "remediation_action"):
            field_value = vuln.get(field_name)
            if not field_value:
                continue
            for entity in ungrounded_entities:
                if entity and entity.lower() in field_value.lower():
                    warnings.append(
                        f"vulnerabilities[{i}].{field_name} still references the "
                        f"unverified value '{entity}' — flagged, not auto-edited"
                    )

    return extraction, warnings