"""Nome padrão e helpers do carrinho favorito."""

from __future__ import annotations

from pathlib import Path


def nome_favorito_padrao(caminho_csv: str | Path, informado: str | None = None) -> str:
    if informado and informado.strip():
        return informado.strip()
    stem = Path(caminho_csv).stem.strip()
    return stem or "carrinho"
