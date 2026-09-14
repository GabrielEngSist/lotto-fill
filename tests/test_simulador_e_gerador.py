import math
import random
from pathlib import Path

from caixa_apostas.csv_parser import escrever_csv, ler_csv, validar_jogos
from caixa_apostas.gerador import (
    Configuracao,
    aplicar_configs_ao_restante,
    completar_ate_limite,
    gerar_jogos,
    parse_config,
    parse_configs,
)
from caixa_apostas.modalidades import obter_modalidade
from caixa_apostas.simulador import (
    custo_com_teimosinha,
    formatar_reais,
    hipergeometrica,
    preco_volante,
    probabilidade_faixas,
    simular_jogo,
    valor_por_cota,
)


def test_parse_config():
    assert parse_config("15:10") == Configuracao(15, 10)
    assert parse_config("16x5") == Configuracao(16, 5)
    assert parse_configs([["18:2", "20:1"]]) == [
        Configuracao(18, 2),
        Configuracao(20, 1),
    ]


def test_configs_na_ordem_e_completa_ou_corta_no_limite():
    loto = obter_modalidade("lotofacil")
    recorte = aplicar_configs_ao_restante(
        [Configuracao(18, 2), Configuracao(20, 1)],
        5,
        dezenas_padrao=15,
    )
    assert recorte == [
        Configuracao(18, 2),
        Configuracao(20, 1),
        Configuracao(15, 2),
    ]
    cortado = aplicar_configs_ao_restante(
        [Configuracao(18, 2), Configuracao(20, 5)],
        3,
        dezenas_padrao=15,
    )
    assert cortado == [Configuracao(18, 2), Configuracao(20, 1)]

    jogos = completar_ate_limite(
        [],
        loto,
        [Configuracao(18, 2), Configuracao(20, 1)],
        limite=5,
        rng=random.Random(9),
    )
    assert [len(j.dezenas) for j in jogos] == [18, 18, 20, 15, 15]


def test_gerar_sem_duplicar():
    loto = obter_modalidade("lotofacil")
    rng = random.Random(1)
    jogos = gerar_jogos(loto, [Configuracao(15, 8)], rng=rng)
    assert len(jogos) == 8
    chaves = {tuple(sorted(j.dezenas)) for j in jogos}
    assert len(chaves) == 8
    for jogo in jogos:
        assert len(jogo.dezenas) == 15
        assert all(1 <= n <= 25 for n in jogo.dezenas)


def test_completar_planilha_ate_limite():
    loto = obter_modalidade("lotofacil")
    rng = random.Random(2)
    base = gerar_jogos(loto, [Configuracao(15, 2)], rng=rng)
    todos = completar_ate_limite(
        base, loto, [Configuracao(15, 10)], limite=5, rng=rng
    )
    assert len(todos) == 5
    assert todos[:2] == base
    chaves = {tuple(sorted(j.dezenas)) for j in todos}
    assert len(chaves) == 5


def test_preco_lotofacil_15_e_16():
    loto = obter_modalidade("lotofacil")
    assert preco_volante(loto, 15) == 3.5
    assert preco_volante(loto, 16) == 56.0


def test_probabilidade_lotofacil_simples():
    loto = obter_modalidade("lotofacil")
    p_max, p_qualquer, acertos_max, acertos_min = probabilidade_faixas(
        loto, 15)
    assert acertos_max == 15
    assert acertos_min == 11
    assert abs(p_max - 1 / math.comb(25, 15)) < 1e-15
    assert 0 < p_qualquer < 1
    esperado_11 = sum(
        hipergeometrica(25, 15, 15, k) for k in range(11, 16)
    )
    assert abs(p_qualquer - esperado_11) < 1e-12


def test_simular_jogo_tem_preco():
    loto = obter_modalidade("lotofacil")
    jogo = gerar_jogos(loto, [Configuracao(15, 1)], rng=random.Random(3))[0]
    resultado = simular_jogo(jogo, loto)
    assert resultado.preco == 3.5
    assert formatar_reais(resultado.preco) == "R$ 3,50"


def test_escrever_e_ler_csv(tmp_path: Path):
    loto = obter_modalidade("lotofacil")
    jogos = gerar_jogos(loto, [Configuracao(15, 3)], rng=random.Random(4))
    caminho = tmp_path / "saida.csv"
    escrever_csv(caminho, jogos, loto)
    leitura = ler_csv(caminho, loto)
    validos, erros = validar_jogos(leitura.jogos, loto)
    assert erros == []
    assert len(validos) == 3
    assert [tuple(j.dezenas) for j in validos] == [
        tuple(j.dezenas) for j in jogos]


def test_cotas_e_teimosinha():
    assert custo_com_teimosinha(7.0, 0) == 7.0
    assert custo_com_teimosinha(7.0, 2) == 21.0
    assert valor_por_cota(21.0, 3) == 7.0
    assert valor_por_cota(10.0, 0) == 10.0
    assert formatar_reais(valor_por_cota(7.0, 2)) == "R$ 3,50"
