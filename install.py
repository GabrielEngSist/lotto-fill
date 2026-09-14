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

    try:
        criar_atalhos(Path(py_venv))
    except Exception as exc:
        log(f"  aviso: não consegui criar o atalho ({exc})")

    log("")
    log("Pronto.")
    log("  Dois cliques no ícone Lotto Fill (área de trabalho) abre o navegador.")
    log("  Fechar a aba encerra o aplicativo.")
    log(f"    {python_cmd} apostas_web.py")
    log("  Linha de comando:")
    log(f"    {ativar}")
    log(f"    {python_cmd} apostas.py --listar")
    return 0


def pasta_area_trabalho() -> Path:
    for nome in ("Desktop", "Área de Trabalho", "Área de trabalho"):
        pasta = Path.home() / nome
        if pasta.is_dir():
            return pasta
    return Path.home() / "Desktop"


def criar_atalhos(py_venv: Path) -> None:
    app = ROOT / "apostas_web.py"
    desktop = pasta_area_trabalho()
    if sys.platform == "darwin":
        destino = desktop / "Lotto Fill.app"
        macos = destino / "Contents" / "MacOS"
        macos.mkdir(parents=True, exist_ok=True)
        exe = macos / "LottoFill"
        exe.write_text(
            "#!/bin/bash\n"
            f'ROOT="{ROOT}"\n'
            f'APP="{app}"\n'
            f'VENV_PY="{py_venv}"\n'
            'export VIRTUAL_ENV="$(cd "$(dirname "$VENV_PY")/.." && pwd)"\n'
            'cd "$ROOT" || exit 1\n'
            'PYVER=$("$VENV_PY" -c "import sys; print(f\'{sys.version_info[0]}.{sys.version_info[1]}\')" 2>/dev/null)\n'
            'export PYTHONPATH="$ROOT:$VIRTUAL_ENV/lib/python${PYVER}/site-packages"\n'
            "export PYTHONNOUSERSITE=1\n"
            'BASE=$("$VENV_PY" -c "import sys; print(sys.base_prefix)" 2>/dev/null)\n'
            'PYAPP="$BASE/Resources/Python.app/Contents/MacOS/Python"\n'
            'if [ ! -x "$PYAPP" ]; then PYAPP="$VENV_PY"; fi\n'
            'LOG="$HOME/Library/Logs/lotto-fill.log"\n'
            'mkdir -p "$(dirname "$LOG")"\n'
            'echo "$(date "+%Y-%m-%d %H:%M:%S") $PYAPP $APP" >> "$LOG"\n'
            'exec "$PYAPP" "$APP" >> "$LOG" 2>&1\n',
            encoding="utf-8",
        )
        exe.chmod(0o755)
        plist = destino / "Contents" / "Info.plist"
        if not plist.is_file():
            plist.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                "<plist version=\"1.0\"><dict>\n"
                "  <key>CFBundleName</key><string>Lotto Fill</string>\n"
                "  <key>CFBundleDisplayName</key><string>Lotto Fill</string>\n"
                "  <key>CFBundleIdentifier</key><string>com.lottofill.app</string>\n"
                "  <key>CFBundleExecutable</key><string>LottoFill</string>\n"
                "  <key>CFBundlePackageType</key><string>APPL</string>\n"
                "  <key>NSHighResolutionCapable</key><true/>\n"
                "</dict></plist>\n",
                encoding="utf-8",
            )
        log(f"  aplicativo: {destino}")
        return
    if os.name == "nt":
        pythonw = py_venv.with_name("pythonw.exe")
        alvo = pythonw if pythonw.is_file() else py_venv
        lnk = desktop / "Lotto Fill.lnk"
        ps = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{lnk}'); "
            f"$s.TargetPath = '{alvo}'; "
            f"$s.Arguments = '\"{app}\"'; "
            f"$s.WorkingDirectory = '{ROOT}'; "
            "$s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=False,
            capture_output=True,
        )
        log(f"  atalho: {lnk}")
        return
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    desktop_file = apps / "lotto-fill.desktop"
    desktop_file.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Lotto Fill\n"
        "Comment=Montar apostas da Caixa\n"
        f'Exec="{py_venv}" "{app}"\n'
        f"Path={ROOT}\n"
        "Terminal=false\n"
        "Categories=Utility;\n",
        encoding="utf-8",
    )
    desktop_file.chmod(0o755)
    if desktop.is_dir():
        (desktop / "Lotto Fill.desktop").write_text(
            desktop_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
    log(f"  atalho: {desktop_file}")


if __name__ == "__main__":
    raise SystemExit(main())
