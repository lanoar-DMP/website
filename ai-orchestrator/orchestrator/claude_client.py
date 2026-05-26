"""Claude 3.5 Sonnet API client for the HolyTerminal AI Orchestrator.

Wraps the direct Anthropic REST API (``/v1/messages``) with ``httpx`` for
async HTTP, handles JSON parsing (including markdown-wrapped JSON blocks),
and returns structured analysis dicts.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Async HTTP client for the Anthropic Claude Messages API.

    Args:
        api_key: Anthropic API key (``sk-ant-…``).
        model: Claude model identifier (defaults to
            ``claude-3-5-sonnet-20241022``).
        base_url: Anthropic API base URL.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1/messages",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0,
        )

    async def analyze(
        self,
        system_prompt: str,
        context: str,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Send context to Claude and get structured analysis back.

        Args:
            system_prompt: The system-level instruction (e.g.
                ``SYSTEM_PROMPT`` from ``prompts.py``).
            context: The assembled market data context (from
                ``build_context_prompt()``).
            max_tokens: Maximum output tokens.
            temperature: Model temperature (0.0-1.0).

        Returns:
            A dict with keys ``analysis`` (str), ``signals`` (list),
            ``market_regime`` (str), ``confidence`` (float), and
            ``usage`` (dict with ``input_tokens`` and ``output_tokens``).
            On parse failure, returns a minimal fallback dict with an
            error note in ``analysis``.

        Raises:
            httpx.HTTPError: If the API call itself fails.
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": context},
            ],
        }

        logger.info(
            "Calling Claude %s (max_tokens=%d, temperature=%.2f) …",
            self.model,
            max_tokens,
            temperature,
        )

        response = await self.client.post("", json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract usage stats
        usage = {
            "input_tokens": data.get("usage", {}).get("input_tokens", 0),
            "output_tokens": data.get("usage", {}).get("output_tokens", 0),
        }

        logger.info(
            "Claude responded — input_tokens=%d output_tokens=%d",
            usage["input_tokens"],
            usage["output_tokens"],
        )

        # Extract the text content from Claude's response
        content_blocks = data.get("content", [])
        response_text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                response_text = block.get("text", "")
                break

        if not response_text:
            logger.warning("Claude returned empty text content block.")
            return self._fallback(
                "Claude returned an empty response. No analysis available.",
                usage,
            )

        # Parse JSON from the response — Claude sometimes wraps JSON in
        # ```json … ``` markdown blocks.
        parsed = self._parse_json_response(response_text)
        if parsed is None:
            logger.warning(
                "Could not parse JSON from Claude response. "
                "Raw text: %.200s…",
                response_text,
            )
            return self._fallback(
                "Failed to parse Claude's structured output. "
                "Raw response logged for audit.",
                usage,
            )

        # Merge usage into the returned dict
        parsed["usage"] = usage
        return parsed

    async def close(self) -> None:
        """Close the underlying ``httpx.AsyncClient`` session."""
        await self.client.aclose()
        logger.debug("ClaudeClient HTTP session closed.")

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON dict from Claude's response text.

        Handles:
        - Raw JSON: ``{"analysis": …}``
        - Markdown-wrapped JSON: `````json … `````
        - Markdown-wrapped without lang: `````{…}`````
        """
        # Try to find a ```json … ``` block first
        match = re.search(
            r"```(?:json)?\s*\n?(.*?)```",
            text,
            re.DOTALL,
        )
        if match:
            json_str = match.group(1).strip()
        else:
            # Fall back to treating the entire response as JSON
            json_str = text.strip()

        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return parsed
            logger.warning("Parsed JSON is not a dict (type=%s).", type(parsed).__name__)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("JSON decode error: %s", exc)
            return None

    @staticmethod
    def _fallback(
        message: str,
        usage: Dict[str, int],
    ) -> Dict[str, Any]:
        """Return a minimal fallback dict when Claude output cannot be parsed."""
        return {
            "analysis": message,
            "signals": [],
            "market_regime": "neutral",
            "confidence": 0.0,
            "usage": usage,
        }
