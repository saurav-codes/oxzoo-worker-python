# oxzoo-worker-python

An official ox deploy example: a minimal Python 3.13 background worker managed by uv, with zero third-party dependencies, deployed to a single Ubuntu VPS by the [ox](https://github.com/saurav-codes/vps-ctl) control plane from one `ox.toml` manifest at the repo root. This is an internal worker: no domain, no HTTP server, no readiness probe. ox runs it as a systemd service with `Restart=always` and its output is verified through `journalctl`; the journal is the product. The manifest still declares `port = 9118` because ox requires a project port even for non-listening workers; nothing binds to it.

## Stack

| Component | Version | Purpose |
|---|---|---|
| Runtime | Python 3.13 | runs `worker.py`, prints the greeting line |
| Stdlib | os, sys, time | env read, stderr error path, 10-second sleep loop |
| Package manager | uv 0.11.32 | lockfile (`uv.lock`) is committed; `uv sync --frozen` is the install hook |
| Deploy | ox | `ox.toml` defines the `worker` process as a systemd service with `Restart=always` |

## Environment flow

One variable, runtime only:

**`GREETING_TAG`**: ox injects the project env file (`/srv/ox/oxzoo-worker-python/env`, 0600 root-owned, edited in the ox Environment editor) into the process environment. `worker.py` reads `GREETING_TAG` from `os.environ` at startup and refuses to start without it: a missing or empty value prints a clear error to stderr and exits nonzero, so systemd's `Restart=always` keeps retrying and the journal shows the failure loudly. With the value present, the worker prints `hello world oxzoo-worker-python_<GREETING_TAG>` to stdout once every 10 seconds, forever, starting immediately (the first print comes before the first sleep). `.env.example` documents the variable with a placeholder; real values live in the ox dashboard, never in git.

## Deploy with ox

1. Add the repo in the ox dashboard: paste the clone URL `git@github.com:saurav-codes/oxzoo-worker-python`.
2. In the Environment editor, set `GREETING_TAG=w3-04`.
3. Press **Deploy**; no domain is needed. ox runs `uv sync --frozen` as the install hook in the release worktree, then starts the `worker` process as a systemd service with `Restart=always`.

## Expected output

There is no URL to visit; the journal is the product. Tail the unit:

```bash
journalctl -u ox-oxzoo-worker-python-worker.service -f
```

It shows the exact line, repeating every 10 seconds:

```
hello world oxzoo-worker-python_w3-04
```

The unit name follows ox's `ox-<project>-<process>.service` scheme: project `oxzoo-worker-python` plus process `worker` gives `ox-oxzoo-worker-python-worker.service`. If `GREETING_TAG` is missing or empty, the same journal shows the stderr error and the service restarting under `Restart=always`.

## Local development

```bash
uv sync
GREETING_TAG=dev uv run python worker.py
```

Stop with Ctrl-C. `worker.py` passes `flush=True` on every print even though ox sets `PYTHONUNBUFFERED=1`, so lines appear immediately when piping output locally too. Pass env inline per the command above; never commit a real `.env`.
