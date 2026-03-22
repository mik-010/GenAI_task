"""Near-real-time incremental ingestion: tails the JSONL file for new lines."""

import logging
import os
import time
from typing import Optional

from app.config import DATA_DIR
from app.ingestion.parser import parse_event
from app.ingestion.loader import load_events, refresh_views

logger = logging.getLogger(__name__)


class IncrementalPoller:
    """Watches a JSONL file and ingests new lines periodically."""

    def __init__(self, path: Optional[str] = None, poll_interval: float = 5.0):
        self.path = path or os.path.join(DATA_DIR, "telemetry_logs.jsonl")
        self.poll_interval = poll_interval
        self._offset = 0
        self._running = False

    def _read_new_lines(self):
        """Read lines appended since last offset."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r") as fh:
            fh.seek(self._offset)
            lines = fh.readlines()
            self._offset = fh.tell()
        return lines

    def poll_once(self) -> dict:
        """Read and ingest new lines. Returns {"ok": int, "failed": int}."""
        import json
        lines = self._read_new_lines()
        if not lines:
            return {"ok": 0, "failed": 0}

        events = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                batch = json.loads(line)
            except json.JSONDecodeError:
                continue
            for log_event in batch.get("logEvents", []):
                parsed = parse_event(log_event.get("message", ""))
                if parsed:
                    events.append(parsed)

        if not events:
            return {"ok": 0, "failed": 0}

        result = load_events(events)
        if result["ok"] > 0:
            try:
                refresh_views()
            except Exception:
                logger.warning("View refresh failed during incremental poll")
        logger.info("Incremental poll: ingested %d events (%d failed)", result["ok"], result["failed"])
        return result

    def run(self):
        """Blocking loop that polls until stopped."""
        self._running = True
        # Start at end of file
        if os.path.exists(self.path):
            self._offset = os.path.getsize(self.path)

        logger.info("Incremental poller started — watching %s every %.1fs", self.path, self.poll_interval)
        while self._running:
            try:
                self.poll_once()
            except Exception:
                logger.exception("Error during incremental poll")
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False


def main():
    """CLI entry point for incremental poller."""
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

    parser = argparse.ArgumentParser(description="Real-time incremental telemetry poller")
    parser.add_argument("--path", default=None, help="Path to JSONL file")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval in seconds")
    args = parser.parse_args()

    poller = IncrementalPoller(path=args.path, poll_interval=args.interval)
    try:
        poller.run()
    except KeyboardInterrupt:
        poller.stop()
        logger.info("Poller stopped.")


if __name__ == "__main__":
    main()
