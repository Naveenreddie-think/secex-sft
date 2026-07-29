from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
import json

from app.db import get_db
from app.models import Extraction
from app.schema.extract_schema import ExtractRequest, ExtractResponse
from app.serving.extract import extract

router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=ExtractResponse)
def run_extraction(request: ExtractRequest, db: Session = Depends(get_db)):
    result = extract(request.input_text)

    # Log every extraction to Postgres, same pattern as the review tool
    row = Extraction(
        input_text=request.input_text,
        extracted_json=json.dumps(result.get("extraction")) if result.get("extraction") else None,
        is_schema_valid=result.get("success", False),
        model_version="secex_lora_v1_merged",
    )
    db.add(row)
    db.commit()

    return ExtractResponse(
        success=result["success"],
        extraction=result.get("extraction"),
        groundedness_warnings=result.get("groundedness_warnings", []),
        error=result.get("error"),
    )