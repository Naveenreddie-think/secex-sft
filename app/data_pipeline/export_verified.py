"""
Exports hand-verified labels from Postgres into a clean dataset file.
Run as: python -m app.data_pipeline.export_verified
"""

import json
from pathlib import Path

from app.db import SessionLocal
from app.models import ReviewItem


def main():
    db = SessionLocal()
    try:
        verified_items = (
            db.query(ReviewItem)
            .filter(ReviewItem.is_verified == True)
            .order_by(ReviewItem.id)
            .all()
        )

        dataset = []
        for item in verified_items:
            dataset.append({
                "source_ghsa_id": item.source_ghsa_id,
                "input_text": item.input_text,
                "label": json.loads(item.verified_label),
            })

        out_path = Path("data/clean/verified_dataset.json")
        out_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")

        print(f"Exported {len(dataset)} verified examples -> {out_path}")

    finally:
        db.close()


if __name__ == "__main__":
    main()