"""oxzoo worker: prints the ox greeting line to stdout every 10 seconds.

An internal worker with no HTTP surface. ox runs it as a systemd service
with Restart=always and its output is verified through journalctl.
GREETING_TAG arrives as runtime env from the project env file ox injects.
"""

import os
import sys
import time

INTERVAL_SECONDS = 10


def main() -> int:
    tag = os.environ.get("GREETING_TAG", "")
    if not tag:
        print(
            "GREETING_TAG is missing or empty; refusing to start. "
            "Set it in the ox environment editor (see .env.example).",
            file=sys.stderr,
            flush=True,
        )
        return 1

    while True:
        print(f"hello world oxzoo-worker-python_{tag}", flush=True)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
