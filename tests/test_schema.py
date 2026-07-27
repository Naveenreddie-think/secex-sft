from app.schema.extraction_schema import ExtractionResult

def test_valid_single_cve():
    payload = {
        "vulnerabilities": [
            {
                "cve_id": "CVE-2024-12345",
                "affected_products": [
                    {"vendor": "ExampleCorp", "product": "ExampleCMS", "version_range": "2.0-2.4"}
                ],
                "cwe_category": "Cross-Site Scripting",
                "severity": "low",
                "attack_vector": "network",
                "impact_summary": "Allows remote attackers to inject arbitrary web scripts via the search parameter.",
                "remediation_action": "Upgrade to version 2.5 or later.",
            }
        ]
    }
    result = ExtractionResult.model_validate(payload)
    assert len(result.vulnerabilities) == 1
    assert result.vulnerabilities[0].severity == "low"


def test_invalid_severity_rejected():
    payload = {
        "vulnerabilities": [
            {
                "severity": "super-critical",  # not in enum, should fail
                "attack_vector": "network",
                "impact_summary": "test",
            }
        ]
    }
    try:
        ExtractionResult.model_validate(payload)
        assert False, "should have raised a validation error"
    except Exception:
        pass  # expected