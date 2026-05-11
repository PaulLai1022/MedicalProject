"""LLM client — thin wrapper around the OpenAI SDK with timeout, retry, and json_schema strict support."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import openai

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LLMCallResult:
    """Outcome of an LLM call."""

    raw_response: str
    duration_ms: int
    status: str  # "ok" | "error"
    model: str
    repair_count: int = 0  # number of self-repair attempts (enabled in Stage 7)


class LLMClient:
    """OpenAI-compatible LLM client."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.llm_model
        self._use_strict_schema = settings.llm_use_strict_schema
        self._client: openai.OpenAI | None = None

        if settings.llm_base_url and settings.llm_api_key:
            self._client = openai.OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def chat(
        self,
        system: str,
        user: str,
        *,
        timeout: float = 60.0,
        max_retries: int = 2,
        schema: dict | None = None,
        schema_name: str = "response",
    ) -> LLMCallResult:
        """Call the LLM with retry logic.

        Args:
            system: system prompt
            user: user prompt
            timeout: per-call timeout in seconds
            max_retries: number of retries on API errors (not including the first attempt)
            schema: if provided, constrain output with json_schema strict mode
            schema_name: name for the json_schema (required in strict mode)
        """
        if not self._client:
            return LLMCallResult(
                raw_response="LLM not configured (missing LLM_BASE_URL or LLM_API_KEY)",
                duration_ms=0,
                status="error",
                model=self._model,
            )

        response_format = self._build_response_format(schema, schema_name)

        last_err: Exception | None = None
        t0 = time.monotonic()
        for attempt in range(max_retries + 1):
            t0 = time.monotonic()
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=response_format,
                    timeout=timeout,
                )
                content = resp.choices[0].message.content or ""
                duration = int((time.monotonic() - t0) * 1000)
                return LLMCallResult(
                    raw_response=content,
                    duration_ms=duration,
                    status="ok",
                    model=self._model,
                )
            except openai.BadRequestError as e:
                # The endpoint may not support json_schema; fall back once to json_object and retry.
                if response_format.get("type") == "json_schema" and self._is_schema_unsupported(e):
                    logger.warning(
                        "endpoint does not support json_schema strict mode, falling back to json_object: %s",
                        str(e)[:200],
                    )
                    response_format = {"type": "json_object"}
                    continue
                last_err = e
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s",
                    attempt + 1, max_retries + 1, str(e),
                )
                continue
            except (openai.APITimeoutError, openai.APIError) as e:
                last_err = e
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s",
                    attempt + 1, max_retries + 1, str(e),
                )
                continue

        return LLMCallResult(
            raw_response=str(last_err),
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="error",
            model=self._model,
        )

    def chat_with_repair(
        self,
        system: str,
        user: str,
        *,
        validate: "callable[[str], object | None]",
        timeout: float = 60.0,
        max_retries: int = 2,
        schema: dict | None = None,
        schema_name: str = "response",
        repair_timeout: float = 30.0,
    ) -> "tuple[object | None, LLMCallResult]":
        """Call the LLM with a self-repair pass on validation failure.

        Args:
            validate: parser/validator. Returns a non-None object on success, None on failure.
            Other args: same as `chat()`.

        Trigger: the first call returns status "ok" but `validate` returns None.
        At most one repair attempt; if it also fails, the first response is kept.

        Returns:
            (validated_obj_or_None, final_call_result)
            final_call_result.repair_count = 0 (no repair) or 1 (repair attempted)
        """
        first = self.chat(
            system, user,
            timeout=timeout, max_retries=max_retries,
            schema=schema, schema_name=schema_name,
        )
        if first.status != "ok":
            return (None, first)

        parsed = validate(first.raw_response)
        if parsed is not None:
            return (parsed, first)

        # Trigger self-repair: feed the failed response back to the LLM to fix.
        logger.warning("first response failed to parse; triggering self-repair")
        repair_user = _build_repair_prompt(user, first.raw_response)
        repair = self.chat(
            system, repair_user,
            timeout=repair_timeout, max_retries=0,
            schema=schema, schema_name=schema_name,
        )

        # Merge timings; mark repair_count=1
        merged = LLMCallResult(
            raw_response=repair.raw_response if repair.status == "ok" else first.raw_response,
            duration_ms=first.duration_ms + repair.duration_ms,
            status=repair.status if repair.status == "ok" else first.status,
            model=self._model,
            repair_count=1,
        )

        if repair.status != "ok":
            return (None, merged)

        parsed = validate(repair.raw_response)
        return (parsed, merged)

    def _build_response_format(self, schema: dict | None, schema_name: str) -> dict:
        """Build the response_format value. If a schema is provided and strict mode is enabled,
        return a json_schema wrapper; otherwise return json_object.
        """
        if schema and self._use_strict_schema:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            }
        return {"type": "json_object"}

    @staticmethod
    def _is_schema_unsupported(err: openai.BadRequestError) -> bool:
        """Heuristic: is this BadRequestError caused by the endpoint not supporting json_schema?"""
        msg = str(err).lower()
        return any(
            keyword in msg
            for keyword in ("json_schema", "response_format", "schema", "strict")
        )


def _build_repair_prompt(original_user: str, bad_response: str) -> str:
    """Build the user prompt for a self-repair pass."""
    snippet = bad_response if len(bad_response) <= 4000 else bad_response[:4000] + "\n...[truncated]"
    return f"""Your previous response could not be parsed as valid JSON matching the required schema. Re-output the JSON object strictly following the schema. Do not include explanations, code fences, or comments — only the JSON object.

## ORIGINAL TASK
{original_user}

## YOUR PREVIOUS RESPONSE (failed to parse)
{snippet}

Output the corrected JSON now.
"""
