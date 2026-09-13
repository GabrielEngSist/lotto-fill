#!/usr/bin/env python3
"""Instala o lotto-fill no Linux, macOS e Windows."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
MIN_PY = (3, 10)


def log(msg: str) -> None:
    print(msg, flush=True)


def falhou(msg: str, codigo: int = 1) -> int:
    print(f"Erro: {msg}", file=sys.stderr)
    return codigo


def python_venv() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def pip_venv() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "pip.exe"
    return VENV / "bin" / "pip"


def python_ok(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(
            cmd +
            ["-c",
                "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    partes = proc.stdout.strip().split(".")
    try:
        versao = (int(partes[0]), int(partes[1]))
    except (ValueError, IndexError):
        return False
    return versao >= MIN_PY


def achar_python() -> list[str]:
    if python_ok([sys.executable]):
        return [sys.executable]
    candidatos = []
    if os.name == "nt":
        candidatos.extend([["py", "-3.12"], ["py", "-3.11"],
                          ["py", "-3.10"], ["py", "-3"], ["python"], ["python3"]])
    else:
        candidatos.extend([["python3.12"], ["python3.11"], [
                          "python3.10"], ["python3"], ["python"]])
    for cmd in candidatos:
        if shutil.which(cmd[0]) and python_ok(cmd):
            return cmd
    raise RuntimeError(
        f"Python {MIN_PY[0]}.{MIN_PY[1]}+ não encontrado. "
        "Instale em https://www.python.org/downloads/ e rode de novo."
    )


def rodar(cmd: list[str], **kwargs) -> None:
    log("  $ " + " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main() -> int:
    os.chdir(ROOT)
    log(f"Instalando lotto-fill em {ROOT}")
    try:
        py = achar_python()
    except RuntimeError as exc:
        return falhou(str(exc))
    log(f"Python: {' '.join(py)}")

    if not (ROOT / "requirements.txt").is_file():
        return falhou("requirements.txt não encontrado. Rode o instalador na pasta do projeto.")

    log("Criando ambiente virtual .venv …")
    if python_venv().is_file():
        log("  .venv já existe; reusando.")
    else:
        try:
            rodar(py + ["-m", "venv", str(VENV)])
        except subprocess.CalledProcessError as exc:
            return falhou(f"não consegui criar o venv (código {exc.returncode})")

    pip = str(pip_venv())
    py_venv = str(python_venv())
    if not Path(py_venv).is_file():
        return falhou("venv criado, mas o Python dele não apareceu.")

    log("Atualizando pip …")
    try:
        rodar([py_venv, "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        return falhou(f"falha ao atualizar pip (código {exc.returncode})")

    log("Instalando dependências …")
    try:
        rodar([pip, "install", "-r", str(ROOT / "requirements.txt")], cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        return falhou(f"falha no pip install (código {exc.returncode})")

    log("Baixando o Chromium do Playwright …")
    try:
        rodar([py_venv, "-m", "playwright", "install", "chromium"], cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        return falhou(f"falha no playwright install (código {exc.returncode})")

    if os.name == "nt":
        ativar = r".venv\Scripts\activate"
        python_cmd = r".venv\Scripts\python"
    else:
        ativar = "source .venv/bin/activate"
        python_cmd = ".venv/bin/python"

    log("")
    log("Pronto.")
    log(f"  {ativar}")
    log(f"  {python_cmd} apostas.py --listar")
    log(f"  {python_cmd} apostas.py --modalidade lotofacil --limite 5 --config 15:5 --dry-run --aceitar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
