from __future__ import annotations

import argparse
import time

from leadbot_worker.db.connection import connect
from leadbot_worker.pipeline.collect_urls import provider_from_env
from leadbot_worker.pipeline.run_job import run_search_job
from leadbot_worker.worker import process_next_job, run_simulated_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LeadBot V1 worker.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job.")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument(
        "--mode",
        choices=["simulate", "pipeline"],
        default="simulate",
        help="Use simulate for Milestone 3 queue lifecycle checks; pipeline runs later stages.",
    )
    args = parser.parse_args()

    if args.mode == "pipeline":
        provider = provider_from_env()

        def job_runner(connection, job):
            return run_search_job(connection, job, provider)

    else:
        job_runner = run_simulated_job

    while True:
        process_next_job(connect, job_runner)

        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
