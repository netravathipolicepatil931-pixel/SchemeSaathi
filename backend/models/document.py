from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DocumentType = Literal[
    "aadhaar",
    "pan_card",
    "bank_passbook",
    "class_10_marksheet",
    "disability_certificate",
]


class DocumentMetadata(BaseModel):
    id: UUID
    original_filename: str
    document_type: DocumentType
    media_type: Literal["application/pdf", "image/jpeg"]
    size_bytes: int
    created_at: datetime


class DocumentAnalysis(BaseModel):
    is_supported_document: bool
    document_type: DocumentType | Literal["other"]
    confidence: float = Field(ge=0, le=1)
