from pydantic import BaseModel

from app.schema.extraction_schema import ExtractionResult


class ReviewItemOut(BaseModel):
    id: int
    source_ghsa_id: str
    input_text: str
    auto_label: ExtractionResult
    is_verified: bool

    model_config = {"from_attributes": True}


class ReviewSubmission(BaseModel):
    verified_label: ExtractionResult


class ReviewStats(BaseModel):
    total: int
    verified: int
    remaining: int