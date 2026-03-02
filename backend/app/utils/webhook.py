"""Fire-and-forget webhook notifications for AgentGuard events"""
import hashlib
import hmac
import json
import threading
from datetime import datetime
from typing import Any, Dict

from app.config import settings
from app.utils.logger import logger


def _deliver(url: str, body: bytes, headers: Dict[str, str]) -> None:
    """Deliver webhook payload in a daemon background thread (fire-and-forget)."""
    try:
        import requests
        resp = requests.post(url, data=body, headers=headers, timeout=5)
        logger.debug(
            "Webhook delivered",
            extra={"url": url, "status_code": resp.status_code},
        )
    except Exception as exc:
        logger.warning(
            "Webhook delivery failed",
            extra={"url": url, "error": str(exc)},
        )


def _slack_body(event_type: str, payload: Dict[str, Any]) -> bytes:
    """Format an AgentGuard event as a Slack incoming-webhook message."""
    action = payload.get("action", "unknown")
    agent_name = payload.get("agent_name") or payload.get("agent_id", "unknown")
    resource = payload.get("resource") or ""
    resource_part = f" on `{resource}`" if resource else ""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if event_type == "approval.created":
        text = (
            f"*AgentGuard — Human Approval Required* :hourglass_flowing_sand:\n"
            f"Agent *{agent_name}* wants to perform `{action}`{resource_part}.\n"
            f"<http://localhost:3000/approvals|Review in AgentGuard UI>"
        )
        color = "#F59E0B"
    elif event_type == "approval.approved":
        reason = payload.get("decision_reason", "")
        text = (
            f"*AgentGuard — Request Approved* :white_check_mark:\n"
            f"Agent *{agent_name}* action `{action}`{resource_part} was *approved*."
            + (f"\n> {reason}" if reason else "")
        )
        color = "#10B981"
    else:  # approval.denied
        reason = payload.get("decision_reason", "")
        text = (
            f"*AgentGuard — Request Denied* :x:\n"
            f"Agent *{agent_name}* action `{action}`{resource_part} was *denied*."
            + (f"\n> {reason}" if reason else "")
        )
        color = "#EF4444"

    slack_payload = {
        "attachments": [{
            "color": color,
            "text": text,
            "footer": f"AgentGuard | {ts}",
        }]
    }
    return json.dumps(slack_payload).encode()


def send_webhook(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Send a webhook notification for an AgentGuard event (non-blocking).

    Supported event types:
      - ``approval.created``   — a new approval request needs a human decision
      - ``approval.approved``  — a human approved the request
      - ``approval.denied``    — a human denied the request

    Configuration (backend/.env):
      - ``WEBHOOK_URL``    — destination URL; Slack incoming webhooks are auto-detected
                             and formatted with Slack's attachment format automatically.
      - ``WEBHOOK_SECRET`` — if set, adds ``X-AgentGuard-Signature: sha256=<hex>`` header
                             so the receiver can verify authenticity.

    The call returns immediately; delivery happens in a daemon thread.
    """
    url = settings.WEBHOOK_URL
    if not url:
        return

    is_slack = "hooks.slack.com" in url

    if is_slack:
        body = _slack_body(event_type, payload)
        headers: Dict[str, str] = {"Content-Type": "application/json"}
    else:
        body_dict: Dict[str, Any] = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **payload,
        }
        body = json.dumps(body_dict, default=str).encode()
        headers = {"Content-Type": "application/json"}

        if settings.WEBHOOK_SECRET:
            sig = hmac.new(
                settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256
            ).hexdigest()
            headers["X-AgentGuard-Signature"] = f"sha256={sig}"

    threading.Thread(target=_deliver, args=(url, body, headers), daemon=True).start()
