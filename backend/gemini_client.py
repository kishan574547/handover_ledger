import os
import re
import json
import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel
from google import genai
from google.genai import types

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

try:
    from backend.sanitizer import sanitize_text, sanitize_obj, SECRET_PATTERNS, POSTGRES_URL_PATTERN
except ImportError:
    from sanitizer import sanitize_text, sanitize_obj, SECRET_PATTERNS, POSTGRES_URL_PATTERN

class GeminiServiceError(Exception):
    """Structured, sanitized Gemini exception that never leaks keys."""
    def __init__(self, friendly_message: str, error_type: str, sanitized_details: str):
        super().__init__(friendly_message)
        self.friendly_message = friendly_message
        self.error_type = error_type
        self.sanitized_details = sanitized_details

def map_gemini_error(exc: Exception | str) -> Tuple[str, str, str]:
    """
    Maps raw provider errors into friendly product messages, an error category,
    and sanitized, truncated technical details.
    """
    raw_str = str(exc)
    sanitized = sanitize_text(raw_str)[:300]
    raw_lower = raw_str.lower()

    if "missing_api_key" in raw_lower or "api_key is not configured" in raw_lower:
        return (
            "AI API key is not configured. Live AI extraction is unavailable.",
            "missing_api_key",
            sanitized
        )
    elif "404" in raw_str or "not_found" in raw_lower or "model not found" in raw_lower:
        return (
            "The AI service is unavailable or its model name is outdated",
            "not_found",
            sanitized
        )
    elif "429" in raw_str or "resource_exhausted" in raw_lower or "quota" in raw_lower or "rate limit" in raw_lower:
        return (
            "AI usage limit reached, please try again in a minute",
            "rate_limit",
            sanitized
        )
    elif "401" in raw_str or "403" in raw_str or "permission_denied" in raw_lower or "invalid api key" in raw_lower or "api key not valid" in raw_lower:
        return (
            "Invalid or unauthorized AI credentials",
            "auth_error",
            sanitized
        )
    elif "500" in raw_str or "503" in raw_str or "unavailable" in raw_lower or "timeout" in raw_lower or "connection" in raw_lower:
        return (
            "The AI service is temporarily unavailable. Please try again.",
            "transient_error",
            sanitized
        )
    else:
        return (
            "The AI service encountered an error while processing your request.",
            "unknown",
            sanitized
        )

class GeminiClient:
    """
    Central Gemini client module for HandoverLedger.
    Handles:
    - Dynamic primary model and fallback model rotation on 404 / 429
    - Transient exponential backoff retries
    - Strict JSON output with Pydantic validation
    - Low thinking level where supported
    - Strict credential scrubbing
    - Result caching
    - Circuit breaker cooldown for failing models
    """
    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._cache: Dict[str, Any] = {}
        self._failed_models: Dict[str, float] = {}
        self._cooldown_seconds: float = 60.0

    def get_client(self) -> genai.Client:
        if not settings.GEMINI_API_KEY:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not configured in backend/.env",
                "missing_api_key",
                "GEMINI_API_KEY is null or empty"
            )
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def mark_model_failed(self, model: str):
        self._failed_models[model] = time.time()

    def mark_model_recovered(self, model: str):
        self._failed_models.pop(model, None)

    def get_candidate_models(self) -> List[str]:
        """Returns ordered list of candidate models: primary first, followed by fallbacks, deprioritizing recently failed models."""
        primary = (settings.GEMINI_MODEL or "gemini-3.5-flash-lite").strip()
        all_models = [primary]
        for m in settings.fallback_models_list:
            if m and m not in all_models:
                all_models.append(m)

        now = time.time()
        healthy = [m for m in all_models if (now - self._failed_models.get(m, 0.0)) > self._cooldown_seconds]
        failed = [m for m in all_models if m not in healthy]
        return healthy + failed

    def check_health(self) -> Dict[str, Any]:
        """
        Runs one tiny test call.
        Returns {ok, model_in_use, fallback_used, error_type}.
        Never leaks the key or raw provider payload.
        """
        if not settings.GEMINI_API_KEY:
            return {
                "ok": False,
                "model_in_use": None,
                "fallback_used": False,
                "error_type": "missing_api_key"
            }

        client = self.get_client()
        candidates = self.get_candidate_models()
        last_error_type = "unknown"

        for idx, model in enumerate(candidates):
            try:
                # Tiny ping test
                response = client.models.generate_content(
                    model=model,
                    contents="Ping",
                    config=types.GenerateContentConfig(
                        max_output_tokens=5,
                        temperature=0.0
                    )
                )
                if response and (response.text is not None or response.candidates):
                    self.mark_model_recovered(model)
                    fallback_used = (idx > 0)
                    logger.info(f"AI health check PASSED using model '{model}' (fallback_used={fallback_used})")
                    return {
                        "ok": True,
                        "model_in_use": model,
                        "fallback_used": fallback_used,
                        "error_type": None
                    }
            except Exception as exc:
                self.mark_model_failed(model)
                _, err_type, _ = map_gemini_error(exc)
                last_error_type = err_type
                logger.warning(
                    f"AI health check model '{model}' failed ({err_type}). "
                    f"{'Trying fallback...' if idx < len(candidates) - 1 else 'No more models.'}"
                )
                if err_type in ("not_found", "rate_limit", "transient_error"):
                    continue
                # For auth error, no need to cycle further
                if err_type == "auth_error":
                    break

        return {
            "ok": False,
            "model_in_use": None,
            "fallback_used": False,
            "error_type": last_error_type
        }

    def generate_json(
        self,
        contents: Any,
        system_instruction: Optional[str] = None,
        schema_cls: Optional[Type[T]] = None,
        temperature: float = 0.1,
        low_thinking: bool = False,
        cache_key: Optional[str] = None,
        max_transient_retries: int = 2,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Central method for generating strictly structured JSON output.
        - Checks in-memory cache if cache_key is provided
        - Iterates over candidate models on 404 or 429
        - Retries transient errors with exponential backoff
        - Sets low thinking level where supported
        - Validates parsed JSON with Pydantic if schema_cls is provided
        - Logs model used (never the key)
        """
        if cache_key and cache_key in self._cache:
            logger.debug(f"Returning cached AI result for key '{cache_key}'")
            return self._cache[cache_key]

        client = self.get_client()
        candidates = self.get_candidate_models()

        # If all candidate models are currently marked failed within cooldown, fail fast
        healthy_candidates = [m for m in candidates if (time.time() - self._failed_models.get(m, 0.0)) > self._cooldown_seconds]
        if not healthy_candidates and candidates:
            friendly_msg, err_type, sanitized_detail = map_gemini_error("429 RESOURCE_EXHAUSTED: All models currently in rate limit cooldown")
            raise GeminiServiceError(friendly_msg, err_type, sanitized_detail)

        last_exception: Optional[Exception] = None

        for model_idx, model_name in enumerate(candidates):
            delay = 1.0
            fallback_used = (model_idx > 0)

            for attempt in range(max_transient_retries):
                try:
                    # Construct GenerateContentConfig
                    config_kwargs: Dict[str, Any] = {
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                    }
                    if hasattr(types, "AutomaticFunctionCallingConfig"):
                        try:
                            config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
                        except Exception:
                            pass
                    if system_instruction:
                        config_kwargs["system_instruction"] = system_instruction

                    # Set low thinking level for extraction / verification where supported
                    if low_thinking:
                        try:
                            if hasattr(types, "ThinkingConfig"):
                                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")
                        except Exception:
                            # SDK does not support ThinkingConfig; skip safely
                            pass

                    config = types.GenerateContentConfig(**config_kwargs)

                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config
                    )

                    raw_text = (response.text or "").strip()
                    # Strip any potential markdown json code fences
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    elif raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    raw_text = raw_text.strip()

                    parsed_json = json.loads(raw_text or "{}")

                    # Pydantic validation if schema provided
                    if schema_cls is not None:
                        validated_data = schema_cls.model_validate(parsed_json)
                    else:
                        validated_data = parsed_json

                    meta = {
                        "model_used": model_name,
                        "fallback_used": fallback_used,
                    }

                    # Log which model answered (never log the API key)
                    logger.info(
                        f"AI call succeeded using model '{model_name}' "
                        f"(fallback_used={fallback_used}, attempt={attempt+1})"
                    )

                    if cache_key:
                        self._cache[cache_key] = (validated_data, meta)

                    self.mark_model_recovered(model_name)
                    return validated_data, meta

                except Exception as exc:
                    last_exception = exc
                    friendly_msg, err_type, sanitized_detail = map_gemini_error(exc)

                    # Check if error is due to thinking_config rejection
                    if low_thinking and "thinking" in str(exc).lower():
                        logger.warning(f"ThinkingConfig rejected on model '{model_name}': {sanitized_detail}. Retrying without thinking_config.")
                        low_thinking = False
                        continue

                    # If model not found (404) or quota/rate limit (429), fall back to next model
                    if err_type in ("not_found", "rate_limit"):
                        self.mark_model_failed(model_name)
                        logger.warning(
                            f"Model '{model_name}' failed with {err_type}: {sanitized_detail}. "
                            f"{'Falling back to next candidate model...' if model_idx < len(candidates) - 1 else 'All models exhausted.'}"
                        )
                        break  # Break inner attempt loop to try next model

                    # If authentication error, no need to retry or cycle models
                    if err_type == "auth_error" or err_type == "missing_api_key":
                        raise GeminiServiceError(friendly_msg, err_type, sanitized_detail) from exc

                    # If transient error, retry with exponential backoff
                    if attempt < max_transient_retries - 1:
                        logger.warning(f"Transient AI error on model '{model_name}' (attempt {attempt+1}): {sanitized_detail}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                    else:
                        # Retries for this model exhausted, fall back to next candidate model
                        self.mark_model_failed(model_name)
                        logger.warning(
                            f"Model '{model_name}' transient errors exhausted ({err_type}): {sanitized_detail}. "
                            f"{'Falling back to next candidate model...' if model_idx < len(candidates) - 1 else 'All models exhausted.'}"
                        )
                        break

        # If all models and attempts exhausted
        friendly_msg, err_type, sanitized_detail = map_gemini_error(last_exception or "Unknown AI error")
        raise GeminiServiceError(friendly_msg, err_type, sanitized_detail)

# Singleton client instance
gemini_client = GeminiClient()

