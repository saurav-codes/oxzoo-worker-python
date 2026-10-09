# oxzoo-worker-python

Deployed with [ox](https://deploywithox.com): deploy a repo to your own server with one command, no Docker. [Docs](https://deploywithox.com/docs) · [Guide for Python](https://deploywithox.com/docs/guides/fastapi)

An [ox](https://deploywithox.com) deploy example: a Python 3.13 worker that consumes jobs from a Redis queue and records each completed job in Postgres, deployed to your own Ubuntu server. There is no domain and no HTTP server. ox installs Python and uv, runs `uv sync`, gives the project Postgres and Redis, and runs the worker under systemd, restarting it if it exits.

## Stack

| Component | Version | Purpose |
|---|---|---|
| Worker | Python 3.13 (`.python-version`), uv | `worker.py`, a `BRPOP` loop |
| Clients | psycopg 3.3, redis-py 6.4 | pinned in `pyproject.toml` and `uv.lock` |
| Services | PostgreSQL 18, Redis 8 | provided by ox from `[services]` |

## ox.toml

```toml
# A Python worker on a Redis queue that records each job in Postgres: no web process.

[app]
enabled = false

[workers]
worker = "uv run python worker.py"

[services]
postgres = {}
redis    = {}
```

`[app] enabled = false` says the project has no web process, so ox adds none and asks for no domain. ox detects `uv sync --frozen --no-dev` from `uv.lock`.

## Environment flow

ox provides `DATABASE_URL` and `REDIS_URL` from `[services]`; there is nothing for you to set. `worker.py` refuses to start without either, and creates its `completed_jobs` table on startup, so a fresh deploy needs no migrate step.

## Deploy with ox

```sh
curl -fsSL https://deploywithox.com/install.sh | sh
ox login
ox new https://github.com/saurav-codes/oxzoo-worker-python
ox review oxzoo-worker-python --wait
```

The plan, offline:

```console
$ ox check .
ox check . (manifest: ox.toml)

  build.install              uv sync --frozen --no-dev                            detected:uv.lock
  workers.worker             uv run python worker.py                              declared
  tools.python               3.13                                                 detected:.python-version
  tools.uv                   0.11                                                 default
  services.postgres          postgres 18 (shared)                                 default
  services.redis             redis 8 (only for this project)                      default

  Provided by ox: PORT, HOST, OX_ENV, OX_PROJECT, OX_RELEASE, OX_DATA_DIR, DATABASE_URL, REDIS_URL

Ready to deploy.
```

## Expected output

```sh
ox logs oxzoo-worker-python --follow
```

shows `watching queue oxzoo-worker-python:jobs`, then one line per job pushed onto the queue:

```
completed job from oxzoo-worker-python:jobs: hello
```

To push a test job, run `redis-cli -u "$REDIS_URL" LPUSH oxzoo-worker-python:jobs hello` on the server, with the URL from `ox vars oxzoo-worker-python --reveal`. `ox explore oxzoo-worker-python postgres table completed_jobs` then shows the row.

## Local development

```sh
uv sync
DATABASE_URL=postgresql://localhost/oxzoo_worker REDIS_URL=redis://localhost:6379/0 uv run python worker.py
redis-cli LPUSH oxzoo-worker-python:jobs hello
```
