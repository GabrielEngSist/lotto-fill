"""Consulta opcional do concurso atual (API pública de resultados)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from caixa_apostas.modalidades import Modalidade

API = "https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/"


@dataclass
class InfoConcurso:
    numero: int | None
    proximo: int | None
    data_proximo: str | None
    estimativa: float | None
    acumulado: bool | None

    def resumo(self) -> str:
        partes: list[str] = []
        if self.numero is not None:
            partes.append(f"último sorteio: {self.numero}")
        if self.proximo is not None:
            partes.append(f"próximo concurso: {self.proximo}")
        if self.data_proximo:
            partes.append(f"data: {self.data_proximo}")
        if self.estimativa:
            partes.append(f"estimativa: R$ {self.estimativa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        return " | ".join(partes) if partes else "concurso em aberto no site da Caixa"


def obter_info_concurso(modalidade: Modalidade, timeout: float = 8.0) -> InfoConcurso | None:
    url = API.format(slug=modalidade.api_slug)
    pedido = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (caixa-apostas)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resp:
            dados = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(dados, dict):
        return None
    return InfoConcurso(
        numero=_int_ou_none(dados.get("numero")),
        proximo=_int_ou_none(dados.get("numeroConcursoProximo")),
        data_proximo=_str_ou_none(dados.get("dataProximoConcurso")),
        estimativa=_float_ou_none(dados.get("valorEstimadoProximoConcurso")),
        acumulado=bool(dados.get("acumulado")) if "acumulado" in dados else None,
    )


def _int_ou_none(valor: object) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _float_ou_none(valor: object) -> float | None:
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _str_ou_none(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None
