The purpose of this repo is to support the following workflow:

1. I'll have a dedicated server somewhere that runs the main script via systemd ("uv run main.py")
2. The main script should run an event loop. Every X seconds, if not "busy", run "git pull" followed by "uv run jobs.py". This is an alternative to running cron.
3. "jobs.py" can be (almost) anything, but the core idea is to have it run a set of "jobs", where a "job" is defined via an ABC (or similar). A job should e.g. have a maximum duration. As long as jobs.py runs, the main script should remain "busy". It will be my responsibility to not overload the server, however the maximum duration be a safe-guard against locked jobs. Jobs are expected to run with asyncio.
   1. Each implementation of the ABC should have its implementation in a dedicated script under src/modules (or something aptly named)
4. Ideally, nothing should be stored locally on the server. Instead use external storage (e.g. supabase)
5. Logging needs to be easily accessible somehow. Either create an API end-point, post to supabase, post to discord/signal/email/whatsapp, etc.
6. Need good error handling for jobs so that broken jobs does not ruin execution of other jobs

Some dependencies I assume I will use:
1. supabase for data storage
2. dotenv for secret management
3. async as default
4. push notifications to signal (or something else, depending on ease of implementation)

## Threading Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ MAIN PROCESS (main.py)                                            │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ Main Thread (Synchronous)                                     │ │
│ │                                                               │ │
│ │  while True:                                                  │ │
│ │    ├─ time.sleep(POLL_INTERVAL)    [BLOCKS THREAD]            │ │
│ │    ├─ subprocess: git pull          [BLOCKS THREAD]           │ │
│ │    │                                                          │ │
│ │    └─ subprocess: uv run jobs.py    [BLOCKS THREAD]           │ │
│ │         │                                                     │ │
│ │         │  Spawns new process ───────────────────────┐        │ │
│ │         │                                            │        │ │
│ │         └─ Waits for process to exit                 │        │ │
│ │                                                      │        │ │
│ │  Temporary event loops for notifications:            │        │ │
│ │    └─ asyncio.run(send_discord(...))                 │        │ │
│ └──────────────────────────────────────────────────────┼────────┘ │
└────────────────────────────────────────────────────────┼──────────┘
                                                         │
                                                         ▼
       ┌──────────────────────────────────────────────────────────┐
       │ JOBS PROCESS (jobs.py)                                   │
       │ ┌──────────────────────────────────────────────────────┐ │
       │ │ Main Thread with AsyncIO Event Loop                  │ │
       │ │                                                      │ │
       │ │  asyncio.run(run_all_jobs()):                        │ │
       │ │    │                                                 │ │
       │ │    ├─ Job 1: await job.run()  [ASYNC, TIMEOUT]       │ │
       │ │    │   ├─ Concurrent async tasks possible            │ │
       │ │    │   └─ Returns/Times out                          │ │
       │ │    │                                                 │ │
       │ │    ├─ Job 2: await job.run()  [ASYNC, TIMEOUT]       │ │
       │ │    │   └─ Next job doesn't start until prev done     │ │
       │ │    │                                                 │ │
       │ │    └─ Job N: await job.run()  [ASYNC, TIMEOUT]       │ │
       │ │        └─ Sequential execution                       │ │
       │ │                                                      │ │
       │ │  Process exits with code 0 (success) or 1 (fail)     │ │
       │ └──────────────────────────────────────────────────────┘ │
       └──────────────────────────────────────────────────────────┘

Key Points:
- main.py runs continuously in a single synchronous thread
- jobs.py runs as a separate subprocess, spawned on each poll cycle
- Jobs execute SEQUENTIALLY (one after another), not in parallel
- Individual jobs are async and can use asyncio internally
- Main process blocks while waiting for jobs subprocess to complete
```
