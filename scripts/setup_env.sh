#!/usr/bin/env bash
# Simple environment setup script
# Installs Python dependencies listed in requirements.txt

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

pip install -r "$REPO_ROOT/requirements.txt"
