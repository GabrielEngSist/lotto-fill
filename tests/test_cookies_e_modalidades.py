from caixa_apostas.cookies import (
    carregar_cookies,
    parse_cookie_header,
    parse_json_cookies,
    parse_netscape,
)
from caixa_apostas.modalidades import obter_modalidade


def test_aliases_modalidade():
    assert obter_modalidade("Mega Sena").chave == "mega-sena"
    assert obter_modalidade("loto-facil").chave == "lotofacil"
    assert obter_modalidade("virada").chave == "mega-da-virada"
    assert obter_modalidade("+Milionária").chave == "mais-milionaria"


def test_parse_cookie_header():
    cookies = parse_cookie_header("Cookie: JSESSIONID=abc123; outro=xyz")
    nomes = {c["name"]: c["value"] for c in cookies}
    assert nomes["JSESSIONID"] == "abc123"
    assert nomes["outro"] == "xyz"


def test_parse_netscape(tmp_path):
    texto = (
        "# Netscape HTTP Cookie File\n"
        ".loteriasonline.caixa.gov.br\tTRUE\t/\tTRUE\t0\tJSESSIONID\tabc\n"
    )
    cookies = parse_netscape(texto)
    assert cookies[0]["name"] == "JSESSIONID"
    assert cookies[0]["value"] == "abc"


def test_parse_json():
    cookies = parse_json_cookies(
        '[{"name": "JSESSIONID", "value": "zzz", "domain": ".loteriasonline.caixa.gov.br"}]'
    )
    assert cookies[0]["value"] == "zzz"


def test_carregar_de_arquivo(tmp_path):
    arquivo = tmp_path / "cookies.txt"
    arquivo.write_text("JSESSIONID=token; PATH=/silce-web", encoding="utf-8")
    cookies = carregar_cookies(arquivo=arquivo)
    assert any(c["name"] == "JSESSIONID" and c["value"] == "token" for c in cookies)
    assert all(c["name"].lower() != "path" for c in cookies)
