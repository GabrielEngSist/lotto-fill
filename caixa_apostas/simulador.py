"""Preço e probabilidade de um volante (modelo hipergeométrico oficial)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from caixa_apostas.csv_parser import Jogo
from caixa_apostas.modalidades import Modalidade


@dataclass(frozen=True)
class RegraSorteio:
    sorteados: int
    faixa_minima: int
    preco_unidade: float
    zero_tambem_premio: bool = False


# Unidade = preço da aposta simples. Volante maior = C(k, simples) × unidade.
REGRAS: dict[str, RegraSorteio] = {
    "megasena": RegraSorteio(6, 4, 6.0),
    "lotofacil": RegraSorteio(15, 11, 3.5),
    "quina": RegraSorteio(5, 2, 3.0),
    "lotomania": RegraSorteio(20, 15, 3.0, zero_tambem_premio=True),
    "duplasena": RegraSorteio(6, 3, 3.0),
    "diadesorte": RegraSorteio(7, 4, 2.5),
    "timemania": RegraSorteio(7, 3, 3.5),
    "maismilionaria": RegraSorteio(6, 2, 6.0),
}


@dataclass(frozen=True)
class ResultadoSimulacao:
    jogo: Jogo
    preco: float
    p_maximo: float
    p_qualquer: float
    acertos_maximo: int
    acertos_minimo: int


def regra_da(modalidade: Modalidade) -> RegraSorteio:
    regra = REGRAS.get(modalidade.api_slug)
    if regra is None:
        raise ValueError(f"sem regra de simulação para {modalidade.nome}")
    return regra


def universo(modalidade: Modalidade) -> int:
    return modalidade.dezena_max - modalidade.dezena_min + 1


def preco_volante(modalidade: Modalidade, qtd_dezenas: int) -> float:
    regra = regra_da(modalidade)
    simples = modalidade.min_dezenas
    if qtd_dezenas < simples:
        return 0.0
    return math.comb(qtd_dezenas, simples) * regra.preco_unidade


def hipergeometrica(n_universo: int, sorteados: int, no_volante: int, acertos: int) -> float:
    if sorteados > n_universo or no_volante > n_universo:
        return 0.0
    denom = math.comb(n_universo, sorteados)
    if denom == 0:
        return 0.0
    if acertos < 0 or acertos > no_volante or acertos > sorteados:
        return 0.0
    resto_sorteio = sorteados - acertos
    fora_volante = n_universo - no_volante
    if resto_sorteio > fora_volante:
        return 0.0
    return math.comb(no_volante, acertos) * math.comb(fora_volante, resto_sorteio) / denom


def probabilidade_faixas(
    modalidade: Modalidade,
    qtd_dezenas: int,
) -> tuple[float, float, int, int]:
    regra = regra_da(modalidade)
    n = universo(modalidade)
    k = regra.sorteados
    p_max = hipergeometrica(n, k, qtd_dezenas, k)
    p_qualquer = 0.0
    for acertos in range(regra.faixa_minima, k + 1):
        p_qualquer += hipergeometrica(n, k, qtd_dezenas, acertos)
    if regra.zero_tambem_premio:
        p_qualquer += hipergeometrica(n, k, qtd_dezenas, 0)
    return p_max, min(1.0, p_qualquer), k, regra.faixa_minima


def simular_jogo(jogo: Jogo, modalidade: Modalidade) -> ResultadoSimulacao:
    qtd = len(jogo.dezenas)
    p_max, p_qualquer, acertos_max, acertos_min = probabilidade_faixas(
        modalidade, qtd)
    return ResultadoSimulacao(
        jogo=jogo,
        preco=preco_volante(modalidade, qtd),
        p_maximo=p_max,
        p_qualquer=p_qualquer,
        acertos_maximo=acertos_max,
        acertos_minimo=acertos_min,
    )


def simular_jogos(jogos: list[Jogo], modalidade: Modalidade) -> list[ResultadoSimulacao]:
    return [simular_jogo(jogo, modalidade) for jogo in jogos]


def chance_conjunto(probs: list[float]) -> float:
    nenhuma = 1.0
    for p in probs:
        nenhuma *= 1.0 - min(1.0, max(0.0, p))
    return 1.0 - nenhuma


def custo_com_teimosinha(preco_concurso: float, teimosinha: int) -> float:
    """Teimosinha 0 = só este concurso; 2 = este e os 2 seguintes."""
    concursos = 1 + max(0, int(teimosinha or 0))
    return preco_concurso * concursos


def valor_por_cota(total: float, cotas: int) -> float:
    n = max(1, int(cotas or 1))
    return total / n


def formatar_reais(valor: float) -> str:
    centavos = int(round(valor * 100))
    sinal = "-" if centavos < 0 else ""
    centavos = abs(centavos)
    inteiro, frac = divmod(centavos, 100)
    agrupado = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {agrupado},{frac:02d}"


def formatar_chance(p: float) -> str:
    if p <= 0:
        return "impossível"
    if p >= 1:
        return "certeza"
    inverso = 1.0 / p
    if inverso >= 2:
        return f"1 em {int(round(inverso)):,}".replace(",", ".")
    return f"{p * 100:.2f}%".replace(".", ",")


def linha_simulacao(indice: int, resultado: ResultadoSimulacao, modalidade: Modalidade) -> str:
    dezenas = resultado.jogo.dezenas_formatadas(modalidade.largura_digitos)
    return (
        f"  {indice}. {dezenas}  |  {formatar_reais(resultado.preco)}  |  "
        f"{resultado.acertos_maximo} acertos {formatar_chance(resultado.p_maximo)}  |  "
        f"qualquer prêmio {formatar_chance(resultado.p_qualquer)}"
    )
