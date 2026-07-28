"""
Shows current auto_label state directly from Postgres (not the static mapping file).
Run as: python -m app.data_pipeline.review_sample_db --start 0 --count 5
"""

import argparse
import json

from app.db import SessionLocal
from app.models import ReviewItem


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        items = (
            db.query(ReviewItem)
            .order_by(ReviewItem.id)
            .offset(args.start)
            .limit(args.count)
            .all()
        )

        for item in items:
            label = json.loads(item.auto_label)
            vuln = label["vulnerabilities"][0]
            print(f"\n{'='*80}")
            print(f"[{item.id}] {item.source_ghsa_id}  (verified={item.is_verified})")
            print(f"{'='*80}")
            print(f"Impact Summary: {vuln['impact_summary']}")
            print(f"Remediation:    {vuln['remediation_action']}")
            print(f"Attack Vector:  {vuln['attack_vector']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()