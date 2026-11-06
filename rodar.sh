#!/usr/bin/env bash
# IDEAS CAPITAL assets — abre o app no Mac/Linux:  ./rodar.sh
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Criando ambiente Python..."
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
else
  . .venv/bin/activate
fi
streamlit run app.py
