#!/bin/bash
# Dois cliques: abre o Lotto Fill no navegador e encerra ao fechar a aba.
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
"$PY" apostas_web.py
if [ "$(uname)" = "Darwin" ]; then
  osascript -e 'tell application "Terminal" to close (every window whose name contains "LottoFill")' >/dev/null 2>&1 || true
fi
