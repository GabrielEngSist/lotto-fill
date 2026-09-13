from caixa_apostas.csv_parser import (
    detectar_delimitador,
    ler_csv_texto,
    parse_numeros_concatenados,
    validar_jogos,
)
from caixa_apostas.modalidades import obter_modalidade


def test_parse_numeros_concatenados_megasena():
    assert parse_numeros_concatenados("051223334455", 2) == [5, 12, 23, 33, 44, 55]


def test_parse_numeros_separados():
    assert parse_numeros_concatenados("05 12 23 33 44 55", 2) == [5, 12, 23, 33, 44, 55]
    assert parse_numeros_concatenados("5,12,23,33,44,55", 2) == [5, 12, 23, 33, 44, 55]
    assert parse_numeros_concatenados("05-12-23-33-44-55", 2) == [5, 12, 23, 33, 44, 55]


def test_parse_super_sete_um_digito():
    assert parse_numeros_concatenados("1538204", 1) == [1, 5, 3, 8, 2, 0, 4]


def test_detectar_delimitador_ponto_e_virgula():
    amostra = "Jogo;D1;D2;Numeros\n1;01;02;0102\n"
    assert detectar_delimitador(amostra) == ";"


def test_ler_csv_colunas_d():
    mega = obter_modalidade("mega-sena")
    texto = (
        "Jogo,D1,D2,D3,D4,D5,D6,Numeros\n"
        "051223334455,05,12,23,33,44,55,051223334455\n"
    )
    leitura = ler_csv_texto(texto, mega)
    assert leitura.erros == []
    assert len(leitura.jogos) == 1
    jogo = leitura.jogos[0]
    assert jogo.identificador == "051223334455"
    assert jogo.dezenas == [5, 12, 23, 33, 44, 55]


def test_ler_csv_somente_numeros():
    mega = obter_modalidade("mega-sena")
    texto = "Jogo,Numeros\nJ1,010203040506\n"
    leitura = ler_csv_texto(texto, mega)
    assert leitura.jogos[0].dezenas == [1, 2, 3, 4, 5, 6]


def test_ler_csv_excel_ponto_e_virgula_e_acento():
    mega = obter_modalidade("mega-sena")
    texto = "Jogo;D1;D2;D3;D4;D5;D6;Números\nA;1;2;3;4;5;6;010203040506\n"
    leitura = ler_csv_texto(texto, mega)
    assert leitura.jogos[0].dezenas == [1, 2, 3, 4, 5, 6]


def test_validar_jogo_ok_e_fora_da_faixa():
    mega = obter_modalidade("mega-sena")
    texto = (
        "Jogo,D1,D2,D3,D4,D5,D6,Numeros\n"
        "ok,01,02,03,04,05,06,010203040506\n"
        "ruim,01,02,03,04,05,61,010203040561\n"
        "curto,01,02,03,04,05,,0102030405\n"
    )
    leitura = ler_csv_texto(texto, mega)
    validos, erros = validar_jogos(leitura.jogos, mega)
    assert [j.identificador for j in validos] == ["ok"]
    assert any("61" in e for e in erros)
    assert any("5 dezenas" in e for e in erros)


def test_lotofacil_quinze_dezenas():
    loto = obter_modalidade("lotofacil")
    texto = (
        "Jogo,D1,D2,D3,D4,D5,D6,D7,D8,D9,D10,D11,D12,D13,D14,D15,Numeros\n"
        "a,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,010203040506070809101112131415\n"
    )
    leitura = ler_csv_texto(texto, loto)
    validos, erros = validar_jogos(leitura.jogos, loto)
    assert erros == []
    assert validos[0].dezenas == list(range(1, 16))


def test_dia_de_sorte_mes():
    dia = obter_modalidade("dia-de-sorte")
    texto = "Jogo,D1,D2,D3,D4,D5,D6,D7,Mes,Numeros\n1,1,2,3,4,5,6,7,JAN,01020304050607\n"
    leitura = ler_csv_texto(texto, dia)
    validos, erros = validar_jogos(leitura.jogos, dia)
    assert erros == []
    assert validos[0].extras["mes"] == 1


def test_lotomania_100_vira_zero():
    loto = obter_modalidade("lotomania")
    dezenas = list(range(1, 50)) + [100]
    texto = "Jogo," + ",".join(f"D{i}" for i in range(1, 51)) + "\n"
    texto += "x," + ",".join(str(n) for n in dezenas) + "\n"
    leitura = ler_csv_texto(texto, loto)
    validos, erros = validar_jogos(leitura.jogos, loto)
    assert erros == []
    assert validos[0].dezenas[-1] == 0


def test_duplicado_rejeitado():
    mega = obter_modalidade("mega-sena")
    texto = "Jogo,Numeros\na,010203040506\nb,06 05 04 03 02 01\n"
    leitura = ler_csv_texto(texto, mega)
    validos, erros = validar_jogos(leitura.jogos, mega)
    assert len(validos) == 1
    assert any("duplicado" in e for e in erros)
