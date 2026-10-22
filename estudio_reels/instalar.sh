#!/usr/bin/env bash
# Instala o que o Estúdio de Reels precisa neste Codespace. Pode rodar mais de uma vez.
set -e
cd "$(dirname "$0")/.."

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Instalando o FFmpeg..."
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core
else
  echo "FFmpeg já instalado: $(ffmpeg -version | head -n 1)"
fi

# Ambiente Python separado (.venv-reels), para não mexer no Python do sistema.
if [ ! -x .venv-reels/bin/python ]; then
  echo "Criando o ambiente Python .venv-reels..."
  if ! python3 -m venv .venv-reels; then
    sudo apt-get install -y --no-install-recommends python3-venv
    python3 -m venv .venv-reels
  fi
fi
echo "Instalando as bibliotecas Python..."
.venv-reels/bin/python -m pip install -q --upgrade pip
.venv-reels/bin/python -m pip install -q -r estudio_reels/requirements.txt

echo ""
echo "Pronto. Para abrir o estúdio, rode a tarefa 'Reels: abrir estúdio' ou: bash estudio_reels/iniciar.sh"
