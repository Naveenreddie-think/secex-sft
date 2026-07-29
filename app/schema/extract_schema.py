from pydantic import BaseModel


class ExtractRequest(BaseModel):
    input_text: str


class ExtractResponse(BaseModel):
    success: bool
    extraction: dict | None = None
    groundedness_warnings: list[str] = []
    error: str | None = None