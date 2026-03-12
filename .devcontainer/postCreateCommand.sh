#!/usr/bin/env bash
set -e

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "🚀 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "🔧 Syncing environment with uv..."
uv sync

echo "✅ uv environment ready."
