#!/usr/bin/env bash
# Atalho para a linha de comando do estúdio usando o ambiente .venv-reels.
# Exemplos: bash estudio_reels/rodar.sh sistema | validar ID | renderizar ID | exemplo
cd "$(dirname "$0")/.."
if ! command -v ffmpeg >/dev/null 2>&1 || [ ! -x .venv-reels/bin/python ] || ! .venv-reels/bin/python -c "import flask, jsonschema, PIL" >/dev/null 2>&1; then
  bash estudio_reels/instalar.sh || exit 1
fi
exec .venv-reels/bin/python -m estudio_reels "$@"
