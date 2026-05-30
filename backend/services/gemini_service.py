from __future__ import annotations

import logging
import os
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import get_settings

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"

# HTTP status codes that are safe to retry (transient/overloaded/rate-limited).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0


class GeminiServiceError(RuntimeError):
    """Raised when the Gemini service fails to produce a response."""


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, genai_errors.APIError):
        return getattr(exc, "code", None) in _RETRYABLE_STATUS
    return False


class GeminiService:
    """Thin wrapper around the Gemini 2.5 Flash model."""

    def __init__(self, api_key: str | None = None, model: str = MODEL_NAME) -> None:
        key = api_key or os.getenv("GEMINI_API_KEY") or get_settings().gemini_api_key
        if not key:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not set. Add it to your environment or .env file."
            )

        self.model = model
        try:
            self._client = genai.Client(api_key=key)
            # print("KEY PREFIX:", get_settings().GEMINI_API_KEY[:10])
        except Exception as exc:  # noqa: BLE001 - surface init failures uniformly
            raise GeminiServiceError(f"Failed to initialize Gemini client: {exc}") from exc

    def _generate(self, prompt: str, config: types.GenerateContentConfig) -> str:
        if not prompt or not prompt.strip():
            raise GeminiServiceError("Prompt must be a non-empty string.")

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as exc:  # noqa: BLE001 - normalize SDK/network errors
                last_exc = exc
                if _is_retryable(exc) and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini request failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt,
                        _MAX_RETRIES,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.exception("Gemini API request failed")
                raise GeminiServiceError(f"Gemini API request failed: {exc}") from exc
        else:  # pragma: no cover - loop always breaks or raises
            raise GeminiServiceError(f"Gemini API request failed: {last_exc}")

        text = getattr(response, "text", None)
        if not text:
            raise GeminiServiceError("Gemini returned an empty response.")

        return text.strip()

    def generate_response(self, prompt: str) -> str:
        """Generate a text response for the given prompt.

        Raises:
            GeminiServiceError: if the prompt is empty, the API call fails
                (after retries), or the model returns no usable text.
        """
        return self._generate(prompt, types.GenerateContentConfig())

    def generate_json(self, prompt: str, response_schema: type | None = None) -> str:
        """Generate a response constrained to valid JSON.

        Args:
            prompt: The instruction/content sent to the model.
            response_schema: Optional Pydantic model (or schema) used to
                constrain the structure of the model's JSON output.

        Returns:
            A JSON-formatted string.

        Raises:
            GeminiServiceError: if the prompt is empty, the API call fails
                (after retries), or the model returns no usable text.
        """
        return self._generate(
            prompt,
            types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
