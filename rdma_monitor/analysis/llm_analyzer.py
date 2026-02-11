"""LLM-powered analysis of RDMA monitoring data via OpenAI-compatible API."""

import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Send RDMA monitoring snapshots to an OpenAI-compatible LLM for analysis."""

    def __init__(
        self,
        api_url: str = "https://api.openai.com/v1/chat/completions",
        api_key: str = "",
        model: str = "gpt-4",
        max_tokens: int = 2048,
        system_prompt: str = "",
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "You are an expert RDMA network engineer. Analyze the monitoring "
            "data and report anomalies, congestion, and recommendations."
        )

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Send snapshot data to the LLM and return structured analysis.

        Returns:
            dict with keys: analysis (str), timestamp, model, success (bool),
            and optionally error.
        """
        result: dict[str, Any] = {
            "timestamp": time.time(),
            "model": self.model,
            "success": False,
        }

        if not self.api_key:
            result["error"] = "LLM API key not configured"
            logger.warning("LLM analysis skipped: no API key configured")
            return result

        # Truncate large snapshots to stay within token limits
        snapshot_str = json.dumps(snapshot, indent=1, default=str)
        if len(snapshot_str) > 30000:
            snapshot_str = snapshot_str[:30000] + "\n... [truncated]"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Here is the latest RDMA monitoring snapshot. "
                    "Please analyze it and provide actionable insights.\n\n"
                    f"```json\n{snapshot_str}\n```"
                ),
            },
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        try:
            resp = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
            analysis_text = body["choices"][0]["message"]["content"]
            result["analysis"] = analysis_text
            result["success"] = True
            result["usage"] = body.get("usage", {})
            logger.info("LLM analysis completed (%d chars)", len(analysis_text))
        except requests.exceptions.RequestException as exc:
            result["error"] = str(exc)
            logger.error("LLM API request failed: %s", exc)
        except (KeyError, IndexError) as exc:
            result["error"] = f"Unexpected API response format: {exc}"
            logger.error("LLM API response parse error: %s", exc)

        return result
