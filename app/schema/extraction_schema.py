from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AttackVector(str, Enum):
    network = "network"
    adjacent = "adjacent"
    local = "local"
    physical = "physical"
    unknown = "unknown"


class AffectedProduct(BaseModel):
    vendor: str
    product: str
    version_range: Optional[str] = None


class VulnerabilityExtraction(BaseModel):
    cve_id: Optional[str] = Field(
        default=None, description="e.g. CVE-2024-12345, null if not present in text"
    )
    affected_products: list[AffectedProduct] = Field(default_factory=list)
    cwe_category: Optional[str] = Field(
        default=None, description="e.g. 'Cross-Site Scripting', 'SQL Injection'"
    )
    severity: Severity
    attack_vector: AttackVector
    impact_summary: str = Field(
        ..., max_length=400, description="1-2 sentence summary, plain text"
    )
    remediation_action: Optional[str] = None


class ExtractionResult(BaseModel):
    """Top-level container — advisories can describe multiple CVEs."""

    vulnerabilities: list[VulnerabilityExtraction]