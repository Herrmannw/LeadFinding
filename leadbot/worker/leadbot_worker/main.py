from __future__ import annotations

import argparse
import time

from leadbot_worker.db.connection import connect
from leadbot_worker.db.queries import claim_next_queued_job
from leadbot_worker.pipeline.collect_urls import provider_from_env
from leadbot_worker.pipeline.run_job import run_search_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LeadBot V1 worker.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job.")
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()

    provider = provider_from_env()

    while True:
        with connect() as connection:
            job = claim_next_queued_job(connection)

        if job:
            with connect() as connection:
                run_search_job(connection, job, provider)

        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
