#!/bin/bash
# Prepara o Estúdio de Reels ao abrir uma sessão do Claude Code na nuvem (FFmpeg + .venv-reels).
# No Codespace e no computador não faz nada: lá o devcontainer/instalar.sh já cuidam disso.
set -uo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
echo '{"async": true, "asyncTimeout": 300000}'
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
if ! bash estudio_reels/instalar.sh >/tmp/preparar_estudio.log 2>&1; then
  echo "Aviso: o Estúdio de Reels não terminou de instalar. Veja /tmp/preparar_estudio.log"
fi
