"""oxzoo worker: consumes jobs from the project's Redis queue and records
each completed job in Postgres.

An internal worker with no HTTP surface. ox runs it as a systemd worker
that restarts if it exits, and its lines show in ox logs. DATABASE_URL and
REDIS_URL come from the postgres and redis services in ox.toml; the worker
refuses to start without either.
"""

import os
import sys

import psycopg
import redis

# Project-scoped queue name. ox gives this project its own Redis instance.
QUEUE = "oxzoo-worker-python:jobs"

# Created idempotently at startup so a fresh deploy needs no migrate step.
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS completed_jobs (
    id bigserial PRIMARY KEY,
    queue text NOT NULL,
    payload text NOT NULL,
    completed_at timestamptz NOT NULL DEFAULT now()
)
"""


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print(
            "DATABASE_URL is missing or empty; refusing to start. "
            "The manifest must declare postgres (see ox.toml).",
            file=sys.stderr,
            flush=True,
        )
        return 1
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        print(
            "REDIS_URL is missing or empty; refusing to start. "
            "The manifest must declare redis (see ox.toml).",
            file=sys.stderr,
            flush=True,
        )
        return 1

    # autocommit: each completed job is its own INSERT, visible to readers
    # as soon as it lands.
    conn = psycopg.connect(database_url, autocommit=True)
    conn.execute(CREATE_TABLE)
    client = redis.Redis.from_url(redis_url)

    print(f"watching queue {QUEUE}", flush=True)
    while True:
        # BRPOP blocks for a job; the short timeout keeps the loop responsive
        # to restarts without busy-spinning on an empty queue.
        item = client.brpop([QUEUE], timeout=5)
        if item is None:
            continue
        _, payload = item
        text = payload.decode()
        conn.execute(
            "INSERT INTO completed_jobs (queue, payload) VALUES (%s, %s)",
            (QUEUE, text),
        )
        print(f"completed job from {QUEUE}: {text}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
