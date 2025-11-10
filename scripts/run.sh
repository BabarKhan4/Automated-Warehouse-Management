#!/usr/bin/env zsh
# Convenience script: create venv, install deps and run the app.
# Usage:
#   ./scripts/run.sh            # create venv (if needed) and launch
#   ./scripts/run.sh --setup    # only run setup (venv + install)
#   ./scripts/run.sh --recreate --build-planner

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FORCE_RECREATE="false"
BUILD_PLANNER="false"
SETUP_ONLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recreate) FORCE_RECREATE="true"; shift ;;
    --build-planner) BUILD_PLANNER="true"; shift ;;
    --setup) SETUP_ONLY="true"; shift ;;
    -h|--help) echo "Usage: $0 [--recreate] [--build-planner] [--setup]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

PY="$REPO_ROOT/main.py"

# Run setup via main.py --setup which will create .venv and install requirements
echo "Running setup..."
if [[ "${FORCE_RECREATE}" == "true" ]]; then
  python3 "$PY" --setup --force-recreate --build-planner="$BUILD_PLANNER"
else
  python3 "$PY" --setup $( [[ "${BUILD_PLANNER}" == "true" ]] && echo "--build-planner" )
fi

if [[ "${SETUP_ONLY}" == "true" ]]; then
  echo "Setup finished (setup-only)."; exit 0
fi

# Launch the app using the venv python
VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ -x "$VENV_PY" ]]; then
  echo "Launching app with .venv python..."
  "$VENV_PY" "$REPO_ROOT/main.py"
else
  echo "Warning: .venv python not found or not executable. Try running: python3 $PY --setup"; exit 2
fi
