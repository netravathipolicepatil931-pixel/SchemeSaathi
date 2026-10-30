from typing import Annotated
from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from backend.models.auth import AuthenticatedUser
from backend.models.document import DocumentMetadata
from backend.routers.auth import require_user
from backend.services import document_service

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
    dependencies=[Depends(require_user)],
)


@router.get("/status")
def get_document_status() -> dict[str, bool]:
    return document_service.configuration_status()


@router.get("", response_model=list[DocumentMetadata])
def get_documents(
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> list[dict]:
    return document_service.list_documents(current_user.id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/pdf": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "image/jpeg": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
        }
    },
)
async def upload_document(
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    request: Request,
) -> dict:
    """Classify a raw PDF or JPEG body and store it encrypted for its owner."""
    document_service.ensure_storage_configured()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > document_service.MAX_DOCUMENT_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Each document must be 2 MB or smaller.",
                )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header.",
            ) from error

    content = bytearray()
    try:
        async for chunk in request.stream():
            if len(content) + len(chunk) > document_service.MAX_DOCUMENT_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Each document must be 2 MB or smaller.",
                )
            content.extend(chunk)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )
        media_type = document_service.detect_media_type(content)
        original_filename = document_service.sanitize_original_filename(
            request.headers.get("x-filename", ""), media_type
        )
        analysis = await document_service.classify_document(content, media_type)
        if (
            not analysis.is_supported_document
            or analysis.document_type == "other"
            or analysis.confidence
            < document_service.MIN_CLASSIFICATION_CONFIDENCE
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "AI could not confidently identify this as an Aadhaar, "
                    "PAN, bank passbook, 10th marksheet, or disability "
                    "certificate. The file was not saved."
                ),
            )

        saved = document_service.save_document(
            current_user.id,
            analysis.document_type,
            media_type,
            original_filename,
            content,
        )
        return {
            **saved,
            "confidence": analysis.confidence,
            "message": "Document identified and encrypted for your account.",
        }
    finally:
        content[:] = b"\x00" * len(content)


@router.get("/{document_id}/file")
def download_document(
    document_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> Response:
    document = document_service.get_document(
        current_user.id, str(document_id)
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    content, media_type, original_filename = document
    ascii_filename = "".join(
        character
        if character.isascii()
        and (character.isalnum() or character in "._-")
        else "_"
        for character in original_filename
    ).strip("._-")
    if not ascii_filename:
        ascii_filename = "document.pdf" if media_type == "application/pdf" else "document.jpg"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{quote(original_filename, safe='')}"
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    document_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> Response:
    removed = document_service.delete_document(
        current_user.id, str(document_id)
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
