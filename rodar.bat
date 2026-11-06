@echo off
REM IDEAS CAPITAL assets - duplo clique para abrir no Windows.
REM Na primeira vez cria o ambiente e instala as dependencias (~2 min).
cd /d %~dp0
if not exist .venv (
  echo Criando ambiente Python...
  py -3 -m venv .venv
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
streamlit run app.py
