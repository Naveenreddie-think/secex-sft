"""
Core extraction logic: calls the Modal-hosted model endpoint and applies
the groundedness check. Shared by the FastAPI endpoint and any future
CLI/batch tooling.
"""

import json

import requests

from app.serving.groundedness import check_groundedness

MODAL_ENDPOINT = "https://naveenreddie-think--secex-extraction-generate.modal.run"


def extract(input_text: str) -> dict:
    try:
        response = requests.post(
            MODAL_ENDPOINT,
            json={"input_text": input_text},
            timeout=90,  # cold starts can take a while
        )
        response.raise_for_status()
        raw_output = response.json()["raw_output"]
    except requests.RequestException as e:
        return {"success": False, "error": f"Model endpoint request failed: {e}"}

    cleaned = raw_output.strip().replace("```json", "").replace("```", "")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Model output was not valid JSON: {e}", "raw_output": raw_output}

    checked, warnings = check_groundedness(parsed, input_text)

    return {
        "success": True,
        "extraction": checked,
        "groundedness_warnings": warnings,
    }