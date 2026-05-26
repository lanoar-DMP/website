"""
Trace ID generation and linking utilities.

Every ``trace_id`` is a UUID4 that can be linked back through the
entire data pipeline: API source -> DB insert -> AI analysis -> signal.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


def generate_trace_id() -> str:
    """Generate a unique trace ID for the audit trail.

    Returns:
        A new UUID4 string.
    """
    return str(uuid.uuid4())


def create_trace_context(
    source_type: str,
    source_id: str,
    action: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a full trace context dict for logging.

    The returned dict contains a fresh ``trace_id`` together with the
    provided source/action information and an ISO-8601 UTC timestamp.

    Args:
        source_type: Category of the data source (e.g. ``"fred"``,
            ``"yfinance"``, ``"defillama"``, ``"claude_ai"``).
        source_id: Identifier within that source (e.g. indicator code,
            ticker, protocol name).
        action: What happened (e.g. ``"data_fetch"``,
            ``"anomaly_detected"``, ``"signal_generated"``).
        metadata: Optional free-form dict of additional context.

    Returns:
        A dict with keys ``trace_id``, ``source_type``, ``source_id``,
        ``action``, ``timestamp``, and ``metadata``.
    """
    return {
        "trace_id": generate_trace_id(),
        "source_type": source_type,
        "source_id": source_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
