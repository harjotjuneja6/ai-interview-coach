from __future__ import annotations

import io
import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
PDF_MAGIC_BYTES = b"%PDF-"


class PdfServiceError(ValueError):
    """Raised when a PDF cannot be accepted or parsed."""


class PdfService:
    """Validates and extracts text from uploaded PDF files."""

    def __init__(self, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
        self.max_size_bytes = max_size_bytes

    def validate(self, *, filename: str | None, content_type: str | None, data: bytes) -> None:
        """Validate that the upload is a non-empty, properly sized PDF.

        Raises:
            PdfServiceError: if any validation rule fails.
        """
        if not data:
            raise PdfServiceError("Uploaded file is empty.")

        if len(data) > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            raise PdfServiceError(f"File exceeds the maximum size of {max_mb:.0f} MB.")

        has_pdf_extension = bool(filename) and filename.lower().endswith(".pdf")
        has_pdf_content_type = content_type in PDF_CONTENT_TYPES if content_type else False
        if not (has_pdf_extension or has_pdf_content_type):
            raise PdfServiceError("Only PDF files are allowed.")

        # Verify the actual file signature, not just the declared type.
        if not data.startswith(PDF_MAGIC_BYTES):
            raise PdfServiceError("File content is not a valid PDF.")

    def extract_text(self, data: bytes) -> str:
        """Extract and return all text from PDF bytes.

        Raises:
            PdfServiceError: if the PDF is encrypted, corrupt, or has no text.
        """
        try:
            reader = PdfReader(io.BytesIO(data))
        except PdfReadError as exc:
            raise PdfServiceError(f"Could not read PDF: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize unexpected parser errors
            logger.exception("Unexpected error reading PDF")
            raise PdfServiceError(f"Could not read PDF: {exc}") from exc

        if reader.is_encrypted:
            # Attempt to open with an empty password; fail clearly if it won't.
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise PdfServiceError("Encrypted PDFs are not supported.") from exc

        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 - skip pages that fail individually
                logger.warning("Failed to extract text from a page; skipping it.")

        text = "\n".join(part.strip() for part in parts if part.strip()).strip()
        if not text:
            raise PdfServiceError(
                "No extractable text found. The PDF may be scanned or image-only."
            )

        return text

    def extract_from_upload(
        self, *, filename: str | None, content_type: str | None, data: bytes
    ) -> str:
        """Validate the upload then extract its text."""
        self.validate(filename=filename, content_type=content_type, data=data)
        return self.extract_text(data)
