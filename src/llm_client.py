"""Gemini API client wrapper with model fallback, structured output validation, retry, and token tracking.

When a model hits a rate limit (429), the client automatically tries the next model
in the fallback chain configured via GEMINI_FALLBACK_MODELS in .env.
"""

import json
import logging
from typing import Any, Type, TypeVar
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""


class LLMClient:
    """Wrapper around Google Gemini client with automatic model fallback on rate limits."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.google_api_key
        self.model = model or settings.gemini_model
        self._client: genai.Client | None = None
        self.total_prompt_tokens = 0
        self.total_candidate_tokens = 0
        # Track which models are exhausted this session to skip them immediately
        self._exhausted_models: set[str] = set()

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of genai.Client."""
        if self._client is None:
            if not self.api_key:
                raise LLMClientError(
                    "GOOGLE_API_KEY is not configured. Set it in .env or pass api_key."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _get_model_chain(self) -> list[str]:
        """Get ordered list of models to try: primary + fallbacks, minus exhausted ones."""
        all_models = settings.all_models
        available = [m for m in all_models if m not in self._exhausted_models]
        if not available:
            # All exhausted — reset and try again (quota may have reset)
            self._exhausted_models.clear()
            return all_models
        return available

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        temperature: float = 0.2,
    ) -> T:
        """Generate structured output validated against a Pydantic model with fallback + retry."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        formatted_prompt = prompt.replace("{schema}", schema_json)

        # First attempt
        raw_text, error = self._call_model_with_fallback(formatted_prompt, temperature)
        if raw_text is not None:
            try:
                return self._parse_and_validate(raw_text, response_model)
            except (ValidationError, json.JSONDecodeError) as e:
                logger.debug(
                    "Validation failed on first attempt for %s: %s. Retrying...",
                    response_model.__name__, e,
                )
                error_msg = str(e)
        else:
            raise LLMClientError(f"LLM API call failed: {error}")

        # Retry once with corrective prompt
        corrective_prompt = (
            f"{formatted_prompt}\n\n"
            f"PREVIOUS ATTEMPT FAILED WITH VALIDATION ERROR:\n{error_msg}\n\n"
            f"Fix the error and return ONLY valid JSON matching the exact schema."
        )

        retry_text, retry_error = self._call_model_with_fallback(corrective_prompt, temperature=0.0)
        if retry_text is None:
            raise LLMClientError(f"LLM call failed after retry: {retry_error}")

        try:
            return self._parse_and_validate(retry_text, response_model)
        except (ValidationError, json.JSONDecodeError) as e:
            raise LLMClientError(
                f"Failed to validate response against {response_model.__name__} after retry: {e}"
            ) from e

    def generate_structured_list(
        self,
        prompt: str,
        item_model: Type[T],
        temperature: float = 0.2,
    ) -> list[T]:
        """Generate a list of structured items validated against a Pydantic model."""
        raw_text, error = self._call_model_with_fallback(prompt, temperature)
        if raw_text is not None:
            try:
                data = self._clean_and_decode_json(raw_text)
                if isinstance(data, list):
                    return [item_model.model_validate(item) for item in data]
                elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                    return [item_model.model_validate(item) for item in data["items"]]
                else:
                    raise ValidationError.from_exception_data(
                        "Expected list", [{"type": "list_type", "loc": (), "msg": "Expected list"}]
                    )
            except Exception as e:
                logger.debug("First attempt failed for list of %s: %s", item_model.__name__, e)
                error_msg = str(e)
        else:
            raise LLMClientError(f"LLM API call failed: {error}")

        corrective_prompt = (
            f"{prompt}\n\n"
            f"PREVIOUS ATTEMPT FAILED WITH ERROR:\n{error_msg}\n\n"
            f"Return ONLY a JSON array containing valid objects matching the requirements."
        )

        retry_text, retry_error = self._call_model_with_fallback(corrective_prompt, temperature=0.0)
        if retry_text is None:
            raise LLMClientError(f"LLM call failed after retry: {retry_error}")

        data = self._clean_and_decode_json(retry_text)
        if isinstance(data, list):
            return [item_model.model_validate(item) for item in data]
        elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return [item_model.model_validate(item) for item in data["items"]]
        raise LLMClientError(f"Expected JSON list of {item_model.__name__}, got {type(data)}")

    def generate_text(self, prompt: str, temperature: float = 0.3) -> str:
        """Generate open-ended text response using Gemini with fallback chain."""
        raw_text, error = self._call_model_with_fallback(
            prompt, temperature=temperature, response_mime_type="text/plain"
        )
        if raw_text is not None:
            return raw_text.strip()
        raise LLMClientError(f"LLM text generation failed: {error}")

    def _call_model_with_fallback(
        self, prompt: str, temperature: float, response_mime_type: str = "application/json"
    ) -> tuple[str | None, Exception | None]:
        """Try the primary model, then fallbacks on rate limit (429) or resource exhaustion."""
        models = self._get_model_chain()
        last_error: Exception | None = None

        for model_name in models:
            raw_text, error = self._call_model(
                prompt, temperature, model=model_name, response_mime_type=response_mime_type
            )

            if raw_text is not None:
                return raw_text, None

            if error and self._is_rate_limit(error):
                self._exhausted_models.add(model_name)
                logger.debug("Model %s rate-limited. Trying next fallback...", model_name)
                last_error = error
                continue
            else:
                # Non-rate-limit error — don't try other models
                return None, error

        return None, last_error

    def _call_model(
        self,
        prompt: str,
        temperature: float,
        model: str | None = None,
        response_mime_type: str = "application/json",
    ) -> tuple[str | None, Exception | None]:
        """Low-level model call with usage tracking and error handling."""
        target_model = model or self.model
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type=response_mime_type,
            )
            response = self.client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )

            if response.usage_metadata:
                p_tokens = response.usage_metadata.prompt_token_count or 0
                c_tokens = response.usage_metadata.candidates_token_count or 0
                self.total_prompt_tokens += p_tokens
                self.total_candidate_tokens += c_tokens
                logger.info(
                    "LLM [%s] token usage: +%d prompt, +%d candidate. Session total: %d in, %d out",
                    target_model, p_tokens, c_tokens,
                    self.total_prompt_tokens, self.total_candidate_tokens,
                )

            return response.text, None
        except Exception as e:
            logger.debug("Error calling Gemini API (model=%s): %s", target_model, e)
            return None, e

    @staticmethod
    def _is_rate_limit(error: Exception) -> bool:
        """Check if an error is a rate limit / quota exhaustion error."""
        err_str = str(error).lower()
        return any(signal in err_str for signal in [
            "429",
            "resource_exhausted",
            "rate limit",
            "quota exceeded",
            "too many requests",
        ])

    def _clean_and_decode_json(self, raw_text: str) -> Any:
        """Strip markdown fences and parse JSON."""
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)

    def _parse_and_validate(self, raw_text: str, model_cls: Type[T]) -> T:
        """Parse raw text as JSON and validate against model_cls."""
        data = self._clean_and_decode_json(raw_text)
        return model_cls.model_validate(data)


# Global instance
llm_client = LLMClient()
