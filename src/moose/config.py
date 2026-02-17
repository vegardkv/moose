"""Centralised configuration with fail-fast validation."""

import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Required environment variables
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "DISCORD_WEBHOOK_URL",
]

# Validate required env vars on module load (fail fast)
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        sys.exit(f"FATAL: missing env var {var}")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Discord webhook
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Polling and timeout settings
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
DEFAULT_JOB_TIMEOUT_SECONDS = int(os.getenv("DEFAULT_JOB_TIMEOUT_SECONDS", "300"))
GIT_PULL_TIMEOUT_SECONDS = int(os.getenv("GIT_PULL_TIMEOUT_SECONDS", "30"))
