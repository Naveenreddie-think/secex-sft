from app.serving.groundedness import check_groundedness


def make_extraction(cve_id=None, product=None, version_range=None,
                     impact_summary="Some impact.", remediation_action=None):
    return {
        "vulnerabilities": [{
            "cve_id": cve_id,
            "affected_products": [{"vendor": "NPM", "product": product, "version_range": version_range}] if product else [],
            "cwe_category": "Test Category",
            "severity": "high",
            "attack_vector": "network",
            "impact_summary": impact_summary,
            "remediation_action": remediation_action,
        }]
    }


def test_grounded_cve_id_passes_through():
    source = "This is described in CVE-2026-12345 and affects the login flow."
    extraction = make_extraction(cve_id="CVE-2026-12345")
    result, warnings = check_groundedness(extraction, source)
    assert result["vulnerabilities"][0]["cve_id"] == "CVE-2026-12345"
    assert warnings == []


def test_hallucinated_cve_id_is_nulled():
    source = "A network attacker can bypass authentication via an empty header."
    extraction = make_extraction(cve_id="CVE-2026-99999")
    result, warnings = check_groundedness(extraction, source)
    assert result["vulnerabilities"][0]["cve_id"] is None
    assert len(warnings) == 1
    assert "CVE-2026-99999" in warnings[0]


def test_plausible_variant_product_name_is_dropped():
    """
    Regression test for a live-testing finding: the model can invent a
    plausible-sounding *variant* of a real product name mentioned in the
    source (e.g. 'BlogEngine.Core' when the source says 'BlogEngine CMS'),
    not just wholesale fabrication. This must still be caught.
    """
    source = "A stored XSS vulnerability exists in BlogEngine CMS comment rendering."
    extraction = make_extraction(product="BlogEngine.Core", version_range=None)
    result, warnings = check_groundedness(extraction, source)
    assert result["vulnerabilities"][0]["affected_products"] == []
    assert any("BlogEngine.Core" in w for w in warnings)


def test_grounded_product_name_passes_through():
    source = "A stored XSS vulnerability exists in BlogEngine CMS comment rendering."
    extraction = make_extraction(product="BlogEngine CMS", version_range=None)
    result, warnings = check_groundedness(extraction, source)
    assert len(result["vulnerabilities"][0]["affected_products"]) == 1
    assert warnings == []


def test_hallucinated_version_range_is_nulled():
    source = "Affects the sanitize-html package. Upgrade to the latest release."
    extraction = make_extraction(product="sanitize-html", version_range="<= 4.1.0")
    result, warnings = check_groundedness(extraction, source)
    product = result["vulnerabilities"][0]["affected_products"][0]
    assert product["version_range"] is None
    assert any("4.1.0" in w for w in warnings)


def test_grounded_version_range_passes_through():
    source = "Affects sanitize-html versions <= 4.1.0. Upgrade to 4.1.1."
    extraction = make_extraction(product="sanitize-html", version_range="<= 4.1.0")
    result, warnings = check_groundedness(extraction, source)
    product = result["vulnerabilities"][0]["affected_products"][0]
    assert product["version_range"] == "<= 4.1.0"


def test_leaked_entity_in_remediation_text_is_flagged():
    """
    Regression test for the free-text leakage bug found during live testing:
    a fabricated product name correctly dropped from affected_products but
    still present in remediation_action must be flagged, not silently missed.
    """
    source = "A network attacker can bypass authentication via an empty header."
    extraction = make_extraction(
        product="@microsoft/fast-api-authentication",
        remediation_action="Upgrade to the latest version of @microsoft/fast-api-authentication.",
    )
    result, warnings = check_groundedness(extraction, source)
    assert result["vulnerabilities"][0]["affected_products"] == []
    leakage_warnings = [w for w in warnings if "remediation_action" in w and "still references" in w]
    assert len(leakage_warnings) == 1


def test_no_products_no_cve_produces_no_warnings():
    source = "A vague description with no specific identifiers."
    extraction = make_extraction()
    result, warnings = check_groundedness(extraction, source)
    assert warnings == []