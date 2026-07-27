"""
Loads mapped GHSA data into Postgres for hand-verification.
Run as: python -m app.data_pipeline.load_to_db
"""

import json
from pathlib import Path

from app.db import SessionLocal, engine, Base
from app.models import ReviewItem


def main():
    Base.metadata.create_all(bind=engine)

    mapped = json.loads(Path("data/clean/ghsa_mapped.json").read_text(encoding="utf-8"))
    db = SessionLocal()

    inserted, skipped = 0, 0
    try:
        for item in mapped:
            exists = (
                db.query(ReviewItem)
                .filter(ReviewItem.source_ghsa_id == item["source_ghsa_id"])
                .first()
            )
            if exists:
                skipped += 1
                continue

            row = ReviewItem(
                source_ghsa_id=item["source_ghsa_id"],
                input_text=item["input_text"],
                auto_label=json.dumps(item["gold_label"]),
                is_verified=False,
            )
            db.add(row)
            inserted += 1

        db.commit()
    finally:
        db.close()

    print(f"Inserted: {inserted}, Skipped (already existed): {skipped}")


if __name__ == "__main__":
    main()