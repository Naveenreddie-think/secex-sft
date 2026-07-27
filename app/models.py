from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from app.db import Base


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, index=True)
    input_text = Column(Text, nullable=False)
    extracted_json = Column(Text, nullable=True)
    is_schema_valid = Column(Boolean, default=False)
    model_version = Column(String, nullable=True)  # "baseline" or adapter tag
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(Integer, primary_key=True, index=True)
    source_ghsa_id = Column(String, unique=True, nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    auto_label = Column(Text, nullable=False)       # JSON string, from map_to_schema.py
    verified_label = Column(Text, nullable=True)    # JSON string, filled in during review
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))