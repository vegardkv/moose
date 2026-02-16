## Plan: Moose — Async Job Runner with Git-Pull Loop

A self-updating job runner deployed via systemd. `main.py` runs a 60-second poll loop that does `git pull --ff-only` then `uv run jobs.py`. Jobs are defined via an ABC in dedicated modules, executed with asyncio, capped at 5 minutes each, with errors isolated per job. Discord webhooks for alert notifications; structured stdout logging for journalctl; Supabase for persistent storage; no local state on the server.

**Steps**

1. **Add dependencies to `pyproject.toml`**
   - `supabase` — external storage client
   - `python-dotenv` — load `.env` secrets
   - `aiohttp` — async HTTP for Discord webhooks
   - Add `[tool.setuptools.packages.find]` with `where = ["src"]` so `moose` is importable
   - No `asyncio-timeout` needed — stdlib `asyncio.timeout` is available (requires-python >=3.11)

2. **Create `.env.example`** with placeholder keys:
   - `SUPABASE_URL`, `SUPABASE_KEY`
   - `DISCORD_WEBHOOK_URL`
   - `POLL_INTERVAL_SECONDS=60`
   - `DEFAULT_JOB_TIMEOUT_SECONDS=300`
   - `GIT_PULL_TIMEOUT_SECONDS=30`
   - Add `.env` to `.gitignore` (confirm it's already there from standard Python gitignore)

3. **Create `src/moose/__init__.py`** (empty, package marker)

4. **Create `src/moose/config.py`** — centralised settings
   - Load `.env` via `dotenv`
   - Expose typed config values (Supabase creds, Discord URL, poll interval, default timeout, git pull timeout)
   - **Startup validation:** on module load, check each required env var (`SUPABASE_URL`, `SUPABASE_KEY`, `DISCORD_WEBHOOK_URL`). If any is missing, call `sys.exit("FATAL: missing env var <NAME>")` to fail fast with a clear journalctl message

5. **Create `src/moose/notifications.py`** — Discord webhook notifier
   - Async function `send_discord(message: str, level: str)` using `aiohttp`
   - Levels: `info`, `warning`, `error`
   - Format messages with timestamp, job name, and level

6. **Create `src/moose/logging_setup.py`** — logging configuration
   - Configure Python `logging` with a `StreamHandler(sys.stdout)` using a structured formatter: `%(asctime)s %(levelname)s %(name)s %(message)s` — this produces clean, parseable output in journalctl
   - Add a custom handler that forwards `WARNING`+ messages to Discord via `send_discord` — Discord is for alerts only, not routine logs
   - All modules use `logging.getLogger(__name__)`

7. **Create `src/moose/job.py`** — the Job ABC
   - Abstract base class `Job` with:
     - `name: str` (property)
     - `timeout: int` (default 300s, overridable per job)
     - `async def run(self) -> None` (abstract)
   - A `JobResult` dataclass: `job_name`, `success: bool`, `duration: float`, `error: str | None`

8. **Create `src/moose/runner.py`** — the job orchestrator
   - `async def run_all_jobs() -> list[JobResult]`
   - Discover jobs via a registry (list of `Job` subclass instances)
   - For each job:
     - Wrap `job.run()` in `asyncio.wait_for(timeout=job.timeout)`
     - Catch `TimeoutError` → log + mark failed, continue to next job
     - Catch `Exception` → log + mark failed, continue to next job
     - Record `JobResult` with timing
   - After all jobs: send summary notification to Discord
   - Errors in one job never block others

9. **Create `src/moose/modules/__init__.py`** (empty)

10. **Create `src/moose/modules/example_job.py`** — dummy example
    - Subclass `Job`, implement `run()` with a simple `asyncio.sleep(2)` + log message
    - Demonstrates the pattern for future real jobs

11. **Create `jobs.py`** (project root) — entry point for job execution
    - Import `run_all_jobs` from `moose.runner`
    - `asyncio.run(run_all_jobs())`
    - Exit code 0 on success, 1 if any job failed

12. **Rewrite `main.py`** — the poll loop
    - Run synchronously (no asyncio needed here; it shells out to `git` and `uv`)
    - On startup, log "moose started" to Discord
    - Loop:
      1. Sleep `POLL_INTERVAL_SECONDS` (60s)
      2. Run `git pull --ff-only` via `subprocess.run` with `timeout=GIT_PULL_TIMEOUT_SECONDS` (default 30s)
         - **On success:** proceed to step 3
         - **On failure or timeout:** log warning, send one Discord alert ("git pull failed, skipping jobs this cycle"), skip to step 4. No retry within the same cycle — the next loop iteration is the natural retry.
         - **ff-only prevents merge commits** on the server; if fast-forward is not possible, it fails cleanly and is handled like any other pull failure
      3. Run `uv run jobs.py` via `subprocess.run` with `timeout=DEFAULT_JOB_TIMEOUT_SECONDS + 30` (330s)
         - On timeout: log error, send Discord alert, continue loop
      4. While subprocess is running, set a `busy` flag to prevent overlap
      5. Log completion and loop
    - Handle `KeyboardInterrupt` for clean shutdown

13. **Create `moose.service`** — systemd unit file
    - `ExecStart=uv run main.py`
    - `WorkingDirectory=/path/to/moose`
    - `Restart=on-failure`
    - `Environment=PATH=...` (ensure `uv` is on PATH)

**File tree after implementation:**
```
moose/
├── .env.example
├── main.py              # poll loop: git pull --ff-only → uv run jobs.py
├── jobs.py              # entry point: asyncio.run(run_all_jobs())
├── pyproject.toml       # dependencies + [tool.setuptools.packages.find] where=["src"]
├── moose.service        # systemd unit
├── README.md
└── src/
    └── moose/
        ├── __init__.py
        ├── config.py        # .env loading, typed settings, fail-fast validation
        ├── logging_setup.py # structured stdout logging + Discord alert handler
        ├── notifications.py # async Discord webhook
        ├── job.py           # Job ABC + JobResult
        ├── runner.py        # orchestrator with timeout/error isolation
        └── modules/
            ├── __init__.py
            └── example_job.py
```

**Verification**
- `uv run jobs.py` — should run the example job, log structured output to stdout, send Discord notification
- `uv run main.py` — should start the poll loop, perform a `git pull --ff-only`, then invoke `jobs.py`
- Run without `.env` — should exit immediately with `FATAL: missing env var SUPABASE_URL`
- Run with a git repo that has diverged history — `git pull --ff-only` should fail, jobs should be skipped, Discord should get one alert, next cycle should retry normally
- Manually test timeout by creating a job with `asyncio.sleep(600)` and a 5s timeout — confirm it gets killed and other jobs still run
- Manually break a job (raise exception in `run()`) — confirm other jobs still execute and Discord gets an error notification
- Check `journalctl -u moose` — output should be structured and readable

**Decisions**
- Discord webhook over Signal: no daemon dependency, simpler setup
- `main.py` uses `subprocess.run` (sync) rather than asyncio: it only shells out to `git` and `uv`, keeping it simple and avoiding nested event loops
- Job discovery via explicit registry (list in `runner.py`) rather than auto-discovery: simpler, more predictable, easy to add/remove jobs
- 60s poll interval, 300s (5 min) default job timeout per your selections
- `git pull --ff-only` to prevent merge commits on the server
- Subprocess timeouts (30s git, 330s jobs) to prevent hung processes from stalling the service
- `git pull` failure skips jobs for that cycle (next cycle is natural retry) — avoids noisy failure loops
- `src/moose/` package layout for clean imports (`from moose.config import ...`) following standard Python src-layout conventions
- Structured stdout logging for journalctl; Discord reserved for `WARNING+` alerts only
- Fail-fast config validation on startup — missing env vars produce a clear error and immediate exit
