"""Parse de cookies copiados do navegador ou de arquivo."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

DOMINIO = ".loteriasonline.caixa.gov.br"
URL_BASE = "https://www.loteriasonline.caixa.gov.br"


def parse_cookie_header(texto: str) -> list[dict[str, Any]]:
    """Aceita 'a=b; c=d', 'Cookie: a=b; c=d' ou um único par."""
    bruto = texto.strip()
    if not bruto:
        return []
    if bruto.lower().startswith("cookie:"):
        bruto = bruto.split(":", 1)[1].strip()
    cookies: list[dict[str, Any]] = []
    for parte in bruto.split(";"):
        parte = parte.strip()
        if not parte or "=" not in parte:
            continue
        nome, valor = parte.split("=", 1)
        nome = nome.strip()
        valor = valor.strip()
        if nome.lower() in {"path", "domain", "expires", "max-age", "secure", "httponly", "samesite"}:
            continue
        if not nome:
            continue
        cookies.append(_cookie_playwright(nome, valor))
    return cookies


def parse_netscape(texto: str) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split("\t")
        if len(partes) < 7:
            partes = re.split(r"\s+", linha)
        if len(partes) < 7:
            continue
        dominio, _flag, path, secure, expires, nome, valor = partes[:7]
        item = _cookie_playwright(nome, valor, dominio=dominio, path=path)
        item["secure"] = secure.upper() == "TRUE"
        try:
            exp = int(expires)
            if exp > 0:
                item["expires"] = exp
        except ValueError:
            pass
        cookies.append(item)
    return cookies


def parse_json_cookies(texto: str) -> list[dict[str, Any]]:
    dados = json.loads(texto)
    if isinstance(dados, dict) and "cookies" in dados:
        dados = dados["cookies"]
    if not isinstance(dados, list):
        raise ValueError("JSON de cookies deve ser uma lista")
    saida: list[dict[str, Any]] = []
    for item in dados:
        if not isinstance(item, dict) or "name" not in item or "value" not in item:
            continue
        dominio = item.get("domain") or DOMINIO
        path = item.get("path") or "/"
        cookie = _cookie_playwright(
            str(item["name"]),
            str(item["value"]),
            dominio=str(dominio),
            path=str(path),
        )
        if "secure" in item:
            cookie["secure"] = bool(item["secure"])
        if "httpOnly" in item:
            cookie["httpOnly"] = bool(item["httpOnly"])
        if "expires" in item and item["expires"] not in (-1, None, 0):
            try:
                cookie["expires"] = int(item["expires"])
            except (TypeError, ValueError):
                pass
        saida.append(cookie)
    return saida


def _cookie_playwright(
    nome: str,
    valor: str,
    dominio: str = DOMINIO,
    path: str = "/",
) -> dict[str, Any]:
    dominio = dominio.strip() or DOMINIO
    if dominio.startswith("http"):
        dominio = DOMINIO
    return {
        "name": nome,
        "value": valor,
        "domain": dominio,
        "path": path or "/",
        "url": URL_BASE if not dominio.startswith(".") and "caixa.gov.br" not in dominio else None,
    }


def _limpar_nulos(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    limpos: list[dict[str, Any]] = []
    for cookie in cookies:
        item = {k: v for k, v in cookie.items() if v is not None}
        if "domain" not in item and "url" not in item:
            item["domain"] = DOMINIO
        if "url" in item and "domain" in item:
            # Playwright aceita url OU domain, não os dois de forma conflitante.
            item.pop("url", None)
        limpos.append(item)
    return limpos


def carregar_cookies(
    texto: str | None = None,
    arquivo: str | Path | None = None,
) -> list[dict[str, Any]]:
    if arquivo:
        path = Path(arquivo)
        if not path.is_file():
            raise FileNotFoundError(f"arquivo de cookies não encontrado: {path}")
        conteudo = path.read_text(encoding="utf-8-sig").strip()
        if not conteudo:
            raise ValueError(f"arquivo de cookies vazio: {path}")
        cookies = _detectar_e_parse(conteudo)
        if not cookies:
            raise ValueError(f"nenhum cookie válido em {path}")
        return _limpar_nulos(cookies)

    if texto:
        cookies = _detectar_e_parse(texto)
        if not cookies:
            raise ValueError("nenhum cookie válido no texto informado")
        return _limpar_nulos(cookies)

    env = os.environ.get("CAIXA_COOKIE") or os.environ.get("CAIXA_COOKIES")
    if env:
        return _limpar_nulos(_detectar_e_parse(env))

    env_arquivo = os.environ.get("CAIXA_COOKIE_FILE")
    if env_arquivo:
        return carregar_cookies(arquivo=env_arquivo)

    return []


def _detectar_e_parse(conteudo: str) -> list[dict[str, Any]]:
    bruto = conteudo.strip()
    if not bruto:
        return []
    if bruto[0] in "[{":
        return parse_json_cookies(bruto)
    if "\t" in bruto or bruto.startswith("# Netscape") or bruto.startswith("# HttpOnly"):
        netscape = parse_netscape(bruto)
        if netscape:
            return netscape
    return parse_cookie_header(bruto)
