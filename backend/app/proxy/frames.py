from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.types import JSONRPCMessage


def log_frame(
    run_id: str,
    direction: str,
    frame: JSONRPCMessage,
) -> None:
    """Emit one JSON-lines record to stderr. Never raises."""
    try:
        method: str | None = getattr(frame, "method", None)
        msg_id = getattr(frame, "id", None)

        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "run_id": run_id,
            "direction": direction,
            "method": method,
            "msg_id": msg_id,
        }
        print(json.dumps(record), file=sys.stderr, flush=True)
    except Exception:
        pass
