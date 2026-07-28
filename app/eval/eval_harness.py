import difflib
import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.schema.extraction_schema import ExtractionResult

CATEGORICAL_FIELDS = ["severity", "attack_vector"]  # exact-match fields only
FUZZY_MATCH_THRESHOLD = 0.5


@dataclass
class ItemScore:
    source_ghsa_id: str
    schema_valid: bool
    field_matches: dict = field(default_factory=dict)
    parse_error: str | None = None


def try_parse(raw_output: str) -> tuple[ExtractionResult | None, str | None]:
    cleaned = raw_output.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {e}"

    try:
        result = ExtractionResult.model_validate(data)
        return result, None
    except ValidationError as e:
        return None, f"ValidationError: {e}"


def fuzzy_match(pred: str | None, gold: str | None) -> bool:
    if not pred or not gold:
        return pred == gold
    ratio = difflib.SequenceMatcher(None, pred.lower().strip(), gold.lower().strip()).ratio()
    return ratio >= FUZZY_MATCH_THRESHOLD


def score_item(source_ghsa_id: str, raw_output: str, gold: dict) -> ItemScore:
    result, error = try_parse(raw_output)

    if result is None:
        return ItemScore(source_ghsa_id=source_ghsa_id, schema_valid=False, parse_error=error)

    if not result.vulnerabilities:
        return ItemScore(source_ghsa_id=source_ghsa_id, schema_valid=True, parse_error="empty vulnerabilities list")

    predicted = result.vulnerabilities[0]
    gold_vuln = gold["vulnerabilities"][0]

    field_matches = {}
    for field_name in CATEGORICAL_FIELDS:
        pred_val = getattr(predicted, field_name)
        gold_val = gold_vuln.get(field_name)
        # enums need .value, not str() — str() on a custom (str, Enum) mixin
        # returns "ClassName.member", not the actual string value
        pred_str = pred_val.value.strip().lower() if pred_val else None
        gold_str = str(gold_val).strip().lower() if gold_val else None
        field_matches[field_name] = pred_str == gold_str

    field_matches["cwe_category"] = fuzzy_match(predicted.cwe_category, gold_vuln.get("cwe_category"))
    field_matches["cve_id"] = predicted.cve_id == gold_vuln.get("cve_id")

    return ItemScore(
        source_ghsa_id=source_ghsa_id,
        schema_valid=True,
        field_matches=field_matches,
    )

def aggregate_scores(scores: list) -> dict:
    total = len(scores)
    schema_valid_count = sum(1 for s in scores if s.schema_valid)

    field_accuracy = {}
    valid_scores = [s for s in scores if s.schema_valid and s.field_matches]
    if valid_scores:
        for field_name in CATEGORICAL_FIELDS + ["cwe_category", "cve_id"]:
            matches = sum(1 for s in valid_scores if s.field_matches.get(field_name))
            field_accuracy[field_name] = matches / len(valid_scores)

    return {
        "total_items": total,
        "schema_valid_rate": schema_valid_count / total if total else 0,
        "field_accuracy": field_accuracy,
        "parse_errors": [
            {"id": s.source_ghsa_id, "error": s.parse_error}
            for s in scores if not s.schema_valid
        ],
    }