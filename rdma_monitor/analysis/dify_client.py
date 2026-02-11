"""Dify AI workflow integration for RDMA monitoring data.

Pushes monitoring snapshots to a Dify workflow so users can build
custom AI-driven automation pipelines.
"""

import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class DifyClient:
    """Client for pushing RDMA data to Dify AI workflows."""

    def __init__(
        self,
        api_url: str = "http://localhost/v1",
        api_key: str = "",
        workflow_id: str = "",
        input_mapping: dict[str, str] | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.input_mapping = input_mapping or {"monitoring_data": "rdma_stats"}

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def push_to_workflow(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Trigger a Dify workflow with the monitoring snapshot as input.

        Returns:
            dict with keys: success, workflow_run_id, outputs (if any), error.
        """
        result: dict[str, Any] = {
            "timestamp": time.time(),
            "success": False,
        }

        if not self.api_key:
            result["error"] = "Dify API key not configured"
            logger.warning("Dify push skipped: no API key configured")
            return result

        if not self.workflow_id:
            result["error"] = "Dify workflow_id not configured"
            logger.warning("Dify push skipped: no workflow_id configured")
            return result

        # Build inputs dict according to user mapping
        snapshot_str = json.dumps(snapshot, default=str)
        if len(snapshot_str) > 50000:
            snapshot_str = snapshot_str[:50000] + "\n... [truncated]"

        inputs: dict[str, str] = {}
        for dify_var, _ in self.input_mapping.items():
            inputs[dify_var] = snapshot_str

        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": "rdma_monitor",
        }

        url = f"{self.api_url}/workflows/run"

        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
            result["success"] = True
            result["workflow_run_id"] = body.get("workflow_run_id", "")
            result["outputs"] = body.get("data", {}).get("outputs", {})
            logger.info(
                "Dify workflow triggered: run_id=%s",
                result["workflow_run_id"],
            )
        except requests.exceptions.RequestException as exc:
            result["error"] = str(exc)
            logger.error("Dify API request failed: %s", exc)
        except (KeyError, ValueError) as exc:
            result["error"] = f"Unexpected Dify response: {exc}"
            logger.error("Dify response parse error: %s", exc)

        return result

    def send_chat_message(self, message: str,
                          conversation_id: str = "") -> dict[str, Any]:
        """Send a chat message to a Dify chatbot app (alternative mode).

        Useful when users configure a Dify chatbot instead of a workflow.
        """
        result: dict[str, Any] = {"success": False}

        if not self.api_key:
            result["error"] = "Dify API key not configured"
            return result

        payload: dict[str, Any] = {
            "inputs": {},
            "query": message,
            "response_mode": "blocking",
            "user": "rdma_monitor",
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        url = f"{self.api_url}/chat-messages"

        try:
            resp = requests.post(
                url, headers=self._headers(), json=payload, timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
            result["success"] = True
            result["answer"] = body.get("answer", "")
            result["conversation_id"] = body.get("conversation_id", "")
        except requests.exceptions.RequestException as exc:
            result["error"] = str(exc)
            logger.error("Dify chat request failed: %s", exc)

        return result
