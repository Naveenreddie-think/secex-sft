import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ReviewItem
from app.schema.review_schema import ReviewItemOut, ReviewSubmission, ReviewStats

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/stats", response_model=ReviewStats)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(ReviewItem.id)).scalar()
    verified = db.query(func.count(ReviewItem.id)).filter(ReviewItem.is_verified == True).scalar()
    return ReviewStats(total=total, verified=verified, remaining=total - verified)


@router.get("/next", response_model=ReviewItemOut | None)
def get_next_unverified(db: Session = Depends(get_db)):
    item = (
        db.query(ReviewItem)
        .filter(ReviewItem.is_verified == False)
        .order_by(ReviewItem.id)
        .first()
    )
    if not item:
        return None

    return ReviewItemOut(
        id=item.id,
        source_ghsa_id=item.source_ghsa_id,
        input_text=item.input_text,
        auto_label=json.loads(item.auto_label),
        is_verified=item.is_verified,
    )


@router.post("/{item_id}")
def submit_review(item_id: int, submission: ReviewSubmission, db: Session = Depends(get_db)):
    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    item.verified_label = submission.verified_label.model_dump_json()
    item.is_verified = True
    db.commit()

    return {"status": "ok", "id": item_id}