#!/usr/bin/env bash
set -euo pipefail

# Load API key from .env
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

export PYTHONIOENCODING=utf-8
cd /mnt/c/Users/ariel/projects/tri_tfm_v3
python "$@"
