"""
Uses a local Qwen2.5-3B-Instruct (via Ollama) to draft impact_summary and
remediation_action for each review item, overwrites the placeholder auto_label,
and resets is_verified so the review UI surfaces these for human confirmation.
Run as: python -m app.data_pipeline.draft_summaries
"""

import json
import time

import requests

from app.db import SessionLocal
from app.models import ReviewItem

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b-instruct"

PROMPT_TEMPLATE = """You are drafting two fields for a security vulnerability dataset, based ONLY on the advisory text below. Do not invent facts not present in the text.

Advisory text:
---
{input_text}
---

Return ONLY valid JSON, no preamble, no markdown fences, in this exact shape:
{{"impact_summary": "1-2 sentence plain-text summary of the actual impact/risk described in the Impact section, under 400 characters", "remediation_action": "1 sentence describing the actual remediation/patch/workaround described in the text, or null if none is stated"}}
"""


def draft_fields(input_text: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(input_text=input_text[:4000])

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # ask Ollama to constrain output to valid JSON
        },
        timeout=60,
    )
    response.raise_for_status()
    raw = response.json()["response"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def main():
    db = SessionLocal()
    try:
        items = db.query(ReviewItem).order_by(ReviewItem.id).all()
        print(f"Drafting summaries for {len(items)} items using {MODEL_NAME}...")

        failures = []
        for i, item in enumerate(items, start=1):
            label = json.loads(item.auto_label)
            vuln = label["vulnerabilities"][0]

            try:
                draft = draft_fields(item.input_text)
                vuln["impact_summary"] = draft["impact_summary"][:400]
                vuln["remediation_action"] = draft.get("remediation_action")
            except Exception as e:
                failures.append((item.source_ghsa_id, str(e)))
                print(f"  [{i}/{len(items)}] FAILED on {item.source_ghsa_id}: {e}")
                continue

            item.auto_label = json.dumps(label)
            item.is_verified = False  # reset so review UI surfaces it again
            db.commit()

            if i % 20 == 0:
                print(f"  [{i}/{len(items)}] done...")

        print(f"\nCompleted. Failures: {len(failures)}/{len(items)}")
        for ghsa_id, err in failures:
            print(f"  {ghsa_id}: {err}")

    finally:
        db.close()


if __name__ == "__main__":
    main()