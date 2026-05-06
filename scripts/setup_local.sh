#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"
export UV_CACHE_DIR

PYTHON_BIN="${PYTHON_BIN:-}"
SKIP_BACKEND=0
SKIP_FRONTEND=0
RESET_VENV=0

usage() {
  cat <<'EOF'
Usage: scripts/setup_local.sh [options]

Installs local prerequisites for MCP Hub:
  - Python backend virtual environment managed by uv
  - backend/requirements.txt packages installed by uv
  - backend/.env from backend/.env.example when missing
  - frontend npm dependencies

Options:
  --skip-backend    Do not create/install backend venv
  --skip-frontend   Do not install frontend npm packages
  --reset-venv      Delete backend/venv before recreating it
  -h, --help        Show this help

Environment:
  PYTHON_BIN=/path/to/python3   Override Python interpreter
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

version_ge() {
  # Returns true when $1 >= $2. Versions are dot-separated integers.
  local actual="$1"
  local required="$2"
  [ "$(printf '%s\n%s\n' "$required" "$actual" | sort -V | head -n1)" = "$required" ]
}

find_python() {
  if [ -n "$PYTHON_BIN" ]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN '$PYTHON_BIN' was not found"
    return
  fi

  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      return
    fi
  done

  die "Python 3.11+ is required but no Python interpreter was found"
}

check_python() {
  find_python
  local version
  version="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  version_ge "$version" "3.11.0" || die "Python 3.11+ is required; found $version at '$PYTHON_BIN'"
  log "Using Python $version ($PYTHON_BIN)"
}

check_uv() {
  command -v uv >/dev/null 2>&1 || die "uv is required for backend setup. Install it from https://docs.astral.sh/uv/ or run with --skip-backend."
  log "Using $(uv --version)"
}

check_node() {
  command -v node >/dev/null 2>&1 || die "Node.js 18+ is required but node was not found"
  command -v npm >/dev/null 2>&1 || die "npm is required but was not found"

  local node_version npm_version
  node_version="$(node -p 'process.versions.node')"
  npm_version="$(npm -v)"
  version_ge "$node_version" "18.0.0" || die "Node.js 18+ is required; found $node_version"
  log "Using Node.js $node_version and npm $npm_version"
}

setup_backend() {
  check_python
  check_uv

  if [ "$RESET_VENV" -eq 1 ] && [ -d "$VENV_DIR" ]; then
    log "Removing existing backend virtual environment"
    rm -rf "$VENV_DIR"
  fi

  if [ ! -d "$VENV_DIR" ]; then
    log "Creating backend virtual environment at backend/venv with uv"
    uv venv "$VENV_DIR" --python "$PYTHON_BIN"
  else
    log "Using existing backend virtual environment at backend/venv"
  fi

  log "Installing backend requirements with uv"
  uv pip install --python "$VENV_DIR/bin/python" -r "$BACKEND_DIR/requirements.txt"

  if [ ! -f "$BACKEND_DIR/.env" ]; then
    log "Creating backend/.env from backend/.env.example"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    cat <<'EOF' >> "$BACKEND_DIR/.env"

# Local no-key defaults added by scripts/setup_local.sh
OPENAI_API_KEY=mock
MOCK_LLM=true
EOF
  else
    log "backend/.env already exists; leaving it unchanged"
  fi

  log "Ensuring local upload directory exists"
  mkdir -p "$ROOT_DIR/uploads" "$BACKEND_DIR/uploads"
}

setup_frontend() {
  check_node

  log "Installing frontend npm dependencies"
  (cd "$FRONTEND_DIR" && npm install)
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-backend)
      SKIP_BACKEND=1
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      ;;
    --reset-venv)
      RESET_VENV=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
  shift
done

cd "$ROOT_DIR"

log "Setting up MCP Hub local prerequisites"

if [ "$SKIP_BACKEND" -eq 0 ]; then
  setup_backend
else
  log "Skipping backend setup"
fi

if [ "$SKIP_FRONTEND" -eq 0 ]; then
  setup_frontend
else
  log "Skipping frontend setup"
fi

cat <<EOF

Setup complete.

Run the backend:
  source backend/venv/bin/activate
  python run.py

Run the frontend in another terminal:
  cd frontend
  npm run dev

Open:
  Frontend: http://localhost:5173
  Backend:  http://localhost:8000
  Docs:     http://localhost:8000/docs
EOF
