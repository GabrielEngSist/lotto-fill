#!/usr/bin/env bash
# Linux e macOS: ./install.sh
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 install.py "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python install.py "$@"
fi

echo "Erro: Python 3.10+ não encontrado. Instale o Python e rode de novo." >&2
exit 1
