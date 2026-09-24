# oxzoo-worker-python

An official ox deploy example: a Python 3.13 background worker managed by uv, deployed to a single Ubuntu VPS by the [ox](https://github.com/saurav-codes/vps-ctl) control plane from one `ox.toml` manifest at the repo root. The worker consumes jobs from the project's Redis queue (BRPOP on `oxzoo-worker-python:jobs`) and writes one row per completed job to Postgres — a genuine interdependent pair with no web surface. This is an internal worker: no domain, no HTTP server, no readiness probe. ox runs it as a systemd service with `Restart=always` and its output is verified through `journalctl`; the journal is the product. The manifest still declares `port = 9122` because ox requires a project port even for non-listening workers; nothing binds to it.

## Stack

| Component | Version | Purpose |
|---|---|---|
| Runtime | Python 3.13 | runs `worker.py`, pops the queue, writes rows |
| Queue | redis 6.4 (client) | BRPOP `oxzoo-worker-python:jobs`; the server comes from the host-shared `redis@7` catalog service |
| Database | psycopg 3.3 (binary) | one INSERT per completed job into `completed_jobs`; the server comes from the host-shared `postgres@17` catalog service |
| Package manager | uv 0.11.32 | lockfile (`uv.lock`) is committed; `uv sync --frozen` is the install hook |
| Deploy | ox | `ox.toml` defines the `worker` process as a systemd service with `Restart=always` |

## Environment flow

Two variables, runtime only, both autowired by the catalog services in `ox.toml`:

**`REDIS_URL`**: the `redis@7` service fills it with the project's own database index, so the queue never collides with other projects.

**`DATABASE_URL`**: the `postgres@17` service fills it; the env's database is named after the project.

`worker.py` reads each from `os.environ` at startup and refuses to start without either: a missing or empty value prints a clear error to stderr and exits nonzero, so systemd's `Restart=always` keeps retrying and the journal shows the failure loudly. With both present, the worker creates `completed_jobs` idempotently, BRPOPs `oxzoo-worker-python:jobs`, and for each job inserts one row then prints `completed job from <queue>: <payload>`, forever. `.env.example` documents both variables as blank placeholders (ox fills them); real values live in the ox dashboard, never in git.

## Deploy with ox

1. Add the repo in the ox dashboard: paste the clone URL `git@github.com:saurav-codes/oxzoo-worker-python`.
2. No environment variables are needed: the two catalog services autowire `REDIS_URL` and `DATABASE_URL`.
3. Press **Deploy**; no domain is needed. ox runs `uv sync --frozen` as the install hook in the release worktree, then starts the `worker` process as a systemd service with `Restart=always`.

## Expected output

There is no URL to visit; the journal is the product. Tail the unit:

```bash
journalctl -u ox-oxzoo-worker-python-worker.service -f
```

It shows the startup line, then one completion line per job pushed onto the queue:

```
watching queue oxzoo-worker-python:jobs
completed job from oxzoo-worker-python:jobs: hello
```

Push a test job from the host (the index in the project's `REDIS_URL` is the one the worker pops):

```bash
redis-cli LPUSH oxzoo-worker-python:jobs hello
```

The unit name follows ox's `ox-<project>-<process>.service` scheme: project `oxzoo-worker-python` plus process `worker` gives `ox-oxzoo-worker-python-worker.service`. If `REDIS_URL` or `DATABASE_URL` is missing or empty, the same journal shows the stderr error and the service restarting under `Restart=always`.

## Local development

```bash
uv sync
REDIS_URL=redis://127.0.0.1:6379/0 DATABASE_URL=postgres://localhost/ uv run python worker.py
```

Push jobs with `redis-cli LPUSH oxzoo-worker-python:jobs hello` and watch the table grow (`SELECT count(*) FROM completed_jobs;`). Stop with Ctrl-C. `worker.py` passes `flush=True` on every print even though ox sets `PYTHONUNBUFFERED=1`, so lines appear immediately when piping output locally too. Pass env inline per the command above; never commit a real `.env`.
