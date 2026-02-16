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
