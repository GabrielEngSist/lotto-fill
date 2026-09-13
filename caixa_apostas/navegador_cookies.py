"""Lê a sessão da Caixa direto do Chrome, Edge, Firefox e afins."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from caixa_apostas.cookies import DOMINIO, _cookie_playwright, _limpar_nulos

DOMINIO_CAIXA = "loteriasonline.caixa.gov.br"
NOMES_AUTH = (
    "jsessionid",
    "session",
    "sessionid",
    "auth",
    "token",
    "jwt",
    "sid",
    "ltpatoken",
    "ltpatoken2",
    "remember",
    "silce",
)

NAVEGADORES_ORDEM = ("chrome", "edge", "brave", "chromium", "firefox", "opera")


@dataclass
class SessaoNavegador:
    navegador: str
    perfil: str
    cookies: list[dict[str, Any]]
    ultimo_acesso: int = 0
    origem: str = ""
    aviso: str = ""

    @property
    def nomes_auth(self) -> list[str]:
        return [
            str(c["name"])
            for c in self.cookies
            if _eh_auth(str(c.get("name") or ""))
        ]

    @property
    def autenticada(self) -> bool:
        return bool(self.nomes_auth)

    def resumo(self) -> str:
        auth = ", ".join(self.nomes_auth) if self.nomes_auth else "sem JSESSIONID"
        return (
            f"{self.navegador} / {self.perfil}: {len(self.cookies)} cookie(s) "
            f"({auth})"
        )

    def chave_ordenacao(self) -> tuple:
        prioridade = {nome: i for i, nome in enumerate(NAVEGADORES_ORDEM)}
        return (
            1 if self.autenticada else 0,
            self.ultimo_acesso,
            len(self.cookies),
            -prioridade.get(self.navegador, 99),
        )


def _eh_auth(nome: str) -> bool:
    n = nome.lower()
    return any(chave in n for chave in NOMES_AUTH)


def dominio_loterias(host: str) -> bool:
    host = (host or "").lstrip(".").lower()
    return host == DOMINIO_CAIXA or host.endswith("." + DOMINIO_CAIXA)


def _cookie_playwright_completo(
    nome: str,
    valor: str,
    dominio: str,
    path: str = "/",
    secure: bool = True,
    expires: int | None = None,
    http_only: bool = False,
) -> dict[str, Any]:
    item = _cookie_playwright(nome, valor, dominio=dominio or DOMINIO, path=path or "/")
    item["secure"] = bool(secure)
    if http_only:
        item["httpOnly"] = True
    if expires and int(expires) > 0:
        item["expires"] = int(expires)
    return item


def _copiar_sqlite(origem: Path) -> Path:
    """Copia o SQLite + WAL para ler os cookies mesmo com o navegador aberto."""
    tmp = Path(tempfile.mkdtemp(prefix="caixa-cookies-"))
    destino = tmp / origem.name
    shutil.copy2(origem, destino)
    for sufixo in ("-wal", "-shm", "-journal"):
        extra = Path(str(origem) + sufixo)
        if extra.exists():
            shutil.copy2(extra, Path(str(destino) + sufixo))
    return destino


def _conectar(copia: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(copia))
    con.row_factory = sqlite3.Row
    return con


def _pastas_usuario_dados(navegador: str) -> list[Path]:
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA") or "")
    roaming = Path(os.environ.get("APPDATA") or "")
    mapa: dict[str, list[Path]] = {
        "chrome": [
            local / "Google/Chrome/User Data",
            home / "Library/Application Support/Google/Chrome",
            home / ".config/google-chrome",
            home / "snap/chromium/common/chromium",
        ],
        "edge": [
            local / "Microsoft/Edge/User Data",
            home / "Library/Application Support/Microsoft Edge",
            home / ".config/microsoft-edge",
        ],
        "brave": [
            local / "BraveSoftware/Brave-Browser/User Data",
            home / "Library/Application Support/BraveSoftware/Brave-Browser",
            home / ".config/BraveSoftware/Brave-Browser",
        ],
        "chromium": [
            local / "Chromium/User Data",
            home / "Library/Application Support/Chromium",
            home / ".config/chromium",
        ],
        "opera": [
            roaming / "Opera Software/Opera Stable",
            home / "Library/Application Support/com.operasoftware.Opera",
            home / ".config/opera",
        ],
        "firefox": [
            roaming / "Mozilla/Firefox/Profiles",
            home / "Library/Application Support/Firefox/Profiles",
            home / ".mozilla/firefox",
        ],
    }
    return [p for p in mapa.get(navegador, []) if p and p.is_dir()]


def _perfis_chromium(user_data: Path) -> list[tuple[str, Path, Path]]:
    """Retorna (nome_perfil, arquivo_cookies, local_state)."""
    local_state = user_data / "Local State"
    encontrados: list[tuple[str, Path, Path]] = []
    candidatos = [user_data / "Default", *sorted(user_data.glob("Profile *"))]
    if not any(p.is_dir() for p in candidatos):
        candidatos = [user_data]
    for perfil_dir in candidatos:
        if not perfil_dir.is_dir():
            continue
        for cookies in (
            perfil_dir / "Network" / "Cookies",
            perfil_dir / "Cookies",
        ):
            if cookies.is_file():
                encontrados.append((perfil_dir.name, cookies, local_state))
                break
    return encontrados


def _metadados_chromium(arquivo: Path) -> tuple[int, list[str]]:
    try:
        con = _conectar(arquivo)
    except sqlite3.Error:
        return 0, []
    try:
        try:
            linhas = con.execute(
                """
                SELECT name, host_key, last_access_utc
                FROM cookies
                """
            ).fetchall()
        except sqlite3.Error:
            return 0, []
    finally:
        con.close()

    ultimo = 0
    nomes: list[str] = []
    for linha in linhas:
        host = linha["host_key"] if isinstance(linha, sqlite3.Row) else linha[1]
        if not dominio_loterias(str(host)):
            continue
        nome = linha["name"] if isinstance(linha, sqlite3.Row) else linha[0]
        acesso = linha["last_access_utc"] if isinstance(linha, sqlite3.Row) else linha[2]
        nomes.append(str(nome))
        try:
            ultimo = max(ultimo, int(acesso or 0))
        except (TypeError, ValueError):
            pass
    return ultimo, nomes


def _cookies_via_browser_cookie3(
    navegador: str,
    cookie_file: Path,
    key_file: Path | None,
) -> list[dict[str, Any]]:
    try:
        import browser_cookie3
    except ImportError as exc:
        raise RuntimeError(
            "Instale browser-cookie3 para ler cookies do Chrome/Edge "
            "(pip install browser-cookie3)."
        ) from exc

    kwargs: dict[str, Any] = {
        "cookie_file": str(cookie_file),
        "domain_name": DOMINIO_CAIXA,
    }
    if key_file and key_file.is_file():
        kwargs["key_file"] = str(key_file)

    loaders = {
        "chrome": getattr(browser_cookie3, "chrome", None),
        "edge": getattr(browser_cookie3, "edge", None),
        "brave": getattr(browser_cookie3, "brave", None),
        "chromium": getattr(browser_cookie3, "chromium", None),
        "opera": getattr(browser_cookie3, "opera", None),
    }
    loader = loaders.get(navegador)
    if loader is None:
        loader = browser_cookie3.chrome
    jar = loader(**kwargs)
    saida: list[dict[str, Any]] = []
    for c in jar:
        if not dominio_loterias(c.domain):
            continue
        saida.append(
            _cookie_playwright_completo(
                c.name,
                c.value,
                c.domain,
                path=c.path or "/",
                secure=bool(c.secure),
                expires=int(c.expires) if c.expires else None,
            )
        )
    return _limpar_nulos(saida)


def _cookies_via_rookiepy(navegador: str) -> list[dict[str, Any]]:
    try:
        import rookiepy
    except ImportError:
        return []
    fn = getattr(rookiepy, navegador, None)
    if fn is None:
        return []
    try:
        crus = fn([DOMINIO_CAIXA, "." + DOMINIO_CAIXA])
    except Exception:
        return []
    saida: list[dict[str, Any]] = []
    for item in crus or []:
        host = str(item.get("domain") or "")
        if not dominio_loterias(host):
            continue
        saida.append(
            _cookie_playwright_completo(
                str(item.get("name") or ""),
                str(item.get("value") or ""),
                host,
                path=str(item.get("path") or "/"),
                secure=bool(item.get("secure")),
                expires=int(item["expires"]) if item.get("expires") else None,
                http_only=bool(item.get("httpOnly") or item.get("httponly")),
            )
        )
    return _limpar_nulos(saida)


def _sessoes_chromium(navegador: str) -> list[SessaoNavegador]:
    sessoes: list[SessaoNavegador] = []
    vistos: set[Path] = set()
    for user_data in _pastas_usuario_dados(navegador):
        for perfil, cookies_path, local_state in _perfis_chromium(user_data):
            if cookies_path in vistos:
                continue
            vistos.add(cookies_path)
            copia = _copiar_sqlite(cookies_path)
            try:
                ultimo, nomes = _metadados_chromium(copia)
                if not nomes:
                    continue
                cookies: list[dict[str, Any]] = []
                aviso = ""
                chave = local_state if local_state.is_file() else None
                try:
                    cookies = _cookies_via_browser_cookie3(navegador, copia, chave)
                except Exception as exc:
                    aviso = str(exc)
                    cookies = _cookies_via_rookiepy(navegador)
                    if cookies:
                        aviso = ""
                if not cookies:
                    sessoes.append(
                        SessaoNavegador(
                            navegador=navegador,
                            perfil=perfil,
                            cookies=[],
                            ultimo_acesso=ultimo,
                            origem=str(cookies_path),
                            aviso=aviso
                            or "não foi possível descriptografar os cookies deste perfil",
                        )
                    )
                    continue
                sessoes.append(
                    SessaoNavegador(
                        navegador=navegador,
                        perfil=perfil,
                        cookies=cookies,
                        ultimo_acesso=ultimo,
                        origem=str(cookies_path),
                        aviso=aviso,
                    )
                )
            finally:
                shutil.rmtree(copia.parent, ignore_errors=True)
    return sessoes


def _ler_firefox_sqlite(arquivo: Path) -> tuple[list[dict[str, Any]], int]:
    copia = _copiar_sqlite(arquivo)
    try:
        con = _conectar(copia)
        try:
            colunas = {
                row[1]
                for row in con.execute("PRAGMA table_info(moz_cookies)").fetchall()
            }
            select = "SELECT name, value, host, path, expiry, isSecure"
            if "isHttpOnly" in colunas:
                select += ", isHttpOnly"
            if "lastAccessed" in colunas:
                select += ", lastAccessed"
            select += " FROM moz_cookies"
            linhas = con.execute(select).fetchall()
        finally:
            con.close()
    finally:
        shutil.rmtree(copia.parent, ignore_errors=True)

    cookies: list[dict[str, Any]] = []
    ultimo = 0
    for linha in linhas:
        dados = dict(linha)
        host = str(dados.get("host") or "")
        if not dominio_loterias(host):
            continue
        acesso = int(dados.get("lastAccessed") or 0)
        ultimo = max(ultimo, acesso)
        cookies.append(
            _cookie_playwright_completo(
                str(dados.get("name") or ""),
                str(dados.get("value") or ""),
                host,
                path=str(dados.get("path") or "/"),
                secure=bool(dados.get("isSecure")),
                expires=int(dados["expiry"]) if dados.get("expiry") else None,
                http_only=bool(dados.get("isHttpOnly")),
            )
        )
    return _limpar_nulos(cookies), ultimo


def _sessoes_firefox() -> list[SessaoNavegador]:
    sessoes: list[SessaoNavegador] = []
    for pasta in _pastas_usuario_dados("firefox"):
        arquivos = list(pasta.glob("*/cookies.sqlite")) + list(pasta.glob("cookies.sqlite"))
        for arquivo in arquivos:
            if not arquivo.is_file():
                continue
            cookies, ultimo = _ler_firefox_sqlite(arquivo)
            if not cookies:
                continue
            sessoes.append(
                SessaoNavegador(
                    navegador="firefox",
                    perfil=arquivo.parent.name,
                    cookies=cookies,
                    ultimo_acesso=ultimo,
                    origem=str(arquivo),
                )
            )
    return sessoes


def listar_sessoes(navegador: str = "auto") -> list[SessaoNavegador]:
    alvo = (navegador or "auto").strip().lower()
    if alvo in {"", "auto", "todos"}:
        nomes = NAVEGADORES_ORDEM
    else:
        if alvo not in NAVEGADORES_ORDEM:
            raise ValueError(
                f"Navegador desconhecido: {navegador!r}. "
                f"Use: auto, {', '.join(NAVEGADORES_ORDEM)}"
            )
        nomes = (alvo,)

    sessoes: list[SessaoNavegador] = []
    for nome in nomes:
        if nome == "firefox":
            sessoes.extend(_sessoes_firefox())
        else:
            sessoes.extend(_sessoes_chromium(nome))
    sessoes.sort(key=lambda s: s.chave_ordenacao(), reverse=True)
    return sessoes


def sessao_mais_recente(navegador: str = "auto") -> SessaoNavegador | None:
    """Devolve a sessão da Caixa com acesso mais recente e cookie de login."""
    return buscar_cookies_navegador(navegador)


def buscar_cookies_navegador(
    navegador: str = "auto",
    *,
    listar: Callable[[str], list[SessaoNavegador]] | None = None,
) -> SessaoNavegador | None:
    fn = listar or listar_sessoes
    todas = fn(navegador)
    sessoes = [s for s in todas if s.cookies]
    autenticadas = [s for s in sessoes if s.autenticada]
    pool = autenticadas or sessoes
    if pool:
        pool.sort(key=lambda s: s.chave_ordenacao(), reverse=True)
        return pool[0]
    falhas = [s for s in todas if s.aviso]
    return falhas[0] if falhas else None
