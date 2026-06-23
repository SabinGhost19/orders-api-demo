"""Async worker that pretends to drain an orders queue.

The pinned deps in requirements.txt (cryptography / requests / pyyaml) are the
SAME versions analytics-worker uses — declared here for the SBOM/CVE footprint
so the Blast Radius graph correlates orders-worker with analytics-worker on the
shared package + CVE nodes. This module itself stays stdlib-only so the unit
tests need nothing extra (same convention as analytics-engine-demo).
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("orders-worker")

_STOPPING = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _STOPPING
    logger.info("received signal %s, shutting down", signum)
    _STOPPING = True


def parse_tick_interval(raw: str | None, default: float = 2.0) -> float:
    """Parse the TICK_INTERVAL env value into a positive float of seconds.

    Pure helper (no I/O) so it is unit-testable. Falls back to ``default``
    for missing, empty, non-numeric or non-positive values.
    """
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def main() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    interval = parse_tick_interval(os.environ.get("TICK_INTERVAL"))
    logger.info("orders-worker starting (tick=%ss)", interval)
    while not _STOPPING:
        logger.info("processed orders batch")
        time.sleep(interval)
    logger.info("orders-worker has stopped")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
