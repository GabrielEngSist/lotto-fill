from pathlib import Path

from caixa_apostas.web import api_csv, api_modalidades, api_parse_csv, api_simular, api_surpresinha


def test_modalidades_json():
    dados = api_modalidades()["dados"]
    chaves = {m["chave"] for m in dados}
    assert "lotofacil" in chaves
    assert "mega-sena" in chaves
    loto = next(m for m in dados if m["chave"] == "lotofacil")
    assert loto["min_dezenas"] == 15
    assert loto["cor"].startswith("#")


def test_surpresinha_e_simular():
    gerados = api_surpresinha(
        {"modalidade": "lotofacil", "dezenas": 15,
            "quantidade": 2, "existentes": []}
    )
    jogos = gerados["jogos"]
    assert len(jogos) == 2
    assert len(jogos[0]["dezenas"]) == 15
    sim = api_simular({"modalidade": "lotofacil",
                      "jogos": jogos, "teimosinha": 0, "cotas": 2})
    assert sim["quantidade"] == 2
    assert sim["cotas"] == 2
    assert sim["total"] == "R$ 7,00"
    assert sim["por_cota"] == "R$ 3,50"


def test_csv_download():
    jogo = {
        "identificador": "010203040506070809101112131415",
        "dezenas": list(range(1, 16)),
        "extras": {},
    }
    conteudo, nome = api_csv({"modalidade": "lotofacil", "jogos": [jogo]})
    assert nome.endswith(".csv")
    assert b"Numeros" in conteudo


def test_simular_carrinho_vazio():
    try:
        api_simular({"modalidade": "lotofacil", "jogos": []})
    except ValueError as exc:
        assert "vazio" in str(exc)
    else:
        raise AssertionError("esperava ValueError")


def test_parse_csv_exemplo():
    texto = Path("exemplos/lotofacil.csv").read_text(encoding="utf-8")
    saida = api_parse_csv(
        {"modalidade": "lotofacil", "csv": texto, "nome": "lotofacil.csv"})
    assert saida["jogos"]
    assert all(len(j["dezenas"]) >= 15 for j in saida["jogos"])
