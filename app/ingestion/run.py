"""CLI entry point: ingest telemetry data from generated files into PostgreSQL."""

import argparse
import logging
import os
import sys

from app.ingestion.parser import iter_events_from_jsonl
from app.ingestion.loader import load_employees, load_events, refresh_views, record_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest Claude Code telemetry into PostgreSQL")
    parser.add_argument("--input-dir", default="output", help="Directory with generated data files")
    parser.add_argument("--batch-size", type=int, default=500, help="DB insert batch size")
    args = parser.parse_args()

    employees_path = os.path.join(args.input_dir, "employees.csv")
    telemetry_path = os.path.join(args.input_dir, "telemetry_logs.jsonl")

    if not os.path.exists(telemetry_path):
        logger.error("Telemetry file not found: %s", telemetry_path)
        logger.error("Run 'python3 generate_fake_data.py' first to create the data.")
        sys.exit(1)

    try:
        # 1. Load employees
        if os.path.exists(employees_path):
            logger.info("Loading employees from %s", employees_path)
            emp_count = load_employees(employees_path)
            logger.info("Employees loaded: %d", emp_count)
        else:
            logger.warning("Employee file not found: %s – skipping", employees_path)

        # 2. Load telemetry events
        logger.info("Parsing telemetry from %s", telemetry_path)
        events = iter_events_from_jsonl(telemetry_path)
        result = load_events(events, batch_size=args.batch_size)
        logger.info("Ingestion complete — ok=%d  failed=%d", result["ok"], result["failed"])

        record_ingestion(
            file_name=telemetry_path,
            total=result["ok"] + result["failed"],
            ok=result["ok"],
            failed=result["failed"],
        )

        # 3. Refresh materialized views
        logger.info("Refreshing materialized views...")
        refresh_views()

        logger.info("Done.")
    except Exception:
        logger.exception("Ingestion pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
