import sqlite3
from pathlib import Path

from caixa_apostas.navegador_cookies import (
    SessaoNavegador,
    buscar_cookies_navegador,
    dominio_loterias,
    _ler_firefox_sqlite,
)


def test_dominio_so_loterias_online():
    assert dominio_loterias(".loteriasonline.caixa.gov.br")
    assert dominio_loterias("www.loteriasonline.caixa.gov.br")
    assert not dominio_loterias("internetbanking.caixa.gov.br")
    assert not dominio_loterias("caixa.gov.br")


def _gravar_firefox(pasta: Path, host: str, nome: str, valor: str, acesso: int) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "cookies.sqlite"
    con = sqlite3.connect(arquivo)
    con.execute(
        """
        CREATE TABLE moz_cookies (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value TEXT,
            host TEXT,
            path TEXT,
            expiry INTEGER,
            lastAccessed INTEGER,
            isSecure INTEGER,
            isHttpOnly INTEGER
        )
        """
    )
    con.execute(
        "INSERT INTO moz_cookies (name, value, host, path, expiry, lastAccessed, isSecure, isHttpOnly) "
        "VALUES (?, ?, ?, '/', 1999999999, ?, 1, 1)",
        (nome, valor, host, acesso),
    )
    con.commit()
    con.close()
    return arquivo


def test_ler_firefox_sqlite(tmp_path):
    arquivo = _gravar_firefox(
        tmp_path / "abcd.default-release",
        ".loteriasonline.caixa.gov.br",
        "JSESSIONID",
        "segredo-nao-vazar",
        100,
    )
    cookies, ultimo = _ler_firefox_sqlite(arquivo)
    assert ultimo == 100
    assert len(cookies) == 1
    assert cookies[0]["name"] == "JSESSIONID"
    assert cookies[0]["value"] == "segredo-nao-vazar"
    assert "loteriasonline.caixa.gov.br" in cookies[0]["domain"]


def test_firefox_ignora_outros_dominios_caixa(tmp_path):
    arquivo = _gravar_firefox(
        tmp_path / "xyz.default",
        ".internetbanking.caixa.gov.br",
        "JSESSIONID",
        "banco",
        50,
    )
    cookies, _ultimo = _ler_firefox_sqlite(arquivo)
    assert cookies == []


def test_escolhe_sessao_mais_recente_com_jsessionid():
    velha = SessaoNavegador(
        navegador="firefox",
        perfil="old",
        cookies=[{"name": "JSESSIONID", "value": "a", "domain": ".loteriasonline.caixa.gov.br"}],
        ultimo_acesso=10,
    )
    nova = SessaoNavegador(
        navegador="chrome",
        perfil="Default",
        cookies=[{"name": "JSESSIONID", "value": "b", "domain": ".loteriasonline.caixa.gov.br"}],
        ultimo_acesso=99,
    )
    sem_login = SessaoNavegador(
        navegador="chrome",
        perfil="Profile 1",
        cookies=[{"name": "visitante", "value": "1", "domain": ".loteriasonline.caixa.gov.br"}],
        ultimo_acesso=1000,
    )

    def listar(_navegador: str):
        return [velha, sem_login, nova]

    escolhida = buscar_cookies_navegador("auto", listar=listar)
    assert escolhida is nova


def test_sem_login_escolhe_acesso_mais_recente():
    a = SessaoNavegador(
        navegador="firefox",
        perfil="a",
        cookies=[{"name": "visitante", "value": "1"}],
        ultimo_acesso=1,
    )
    b = SessaoNavegador(
        navegador="firefox",
        perfil="b",
        cookies=[{"name": "visitante", "value": "2"}],
        ultimo_acesso=50,
    )
    escolhida = buscar_cookies_navegador("firefox", listar=lambda _: [a, b])
    assert escolhida is b


def test_resumo_nao_mostra_valor():
    sessao = SessaoNavegador(
        navegador="chrome",
        perfil="Default",
        cookies=[{"name": "JSESSIONID", "value": "super-secreto"}],
    )
    texto = sessao.resumo()
    assert "JSESSIONID" in texto
    assert "super-secreto" not in texto
