"""SSE (Server-Sent Events) helpers."""

from __future__ import annotations

import json
from typing import Any


def format_event(event: str, data: Any) -> bytes:
    """Format a single SSE frame.

    Output format (each frame ends with a blank line):

        event: <event_name>
        data: <json>
        \\n

    Args:
        event: SSE event type (e.g. "stage", "done", "error").
        data: JSON-serializable payload.

    Returns:
        UTF-8 encoded bytes ready to be yielded by a StreamingResponse.
    """
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
