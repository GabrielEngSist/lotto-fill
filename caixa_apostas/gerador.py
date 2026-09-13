"""Geração de volantes aleatórios, sem repetir jogos já existentes."""

from __future__ import annotations

import random
from dataclasses import dataclass

from caixa_apostas.csv_parser import Jogo
from caixa_apostas.modalidades import Modalidade


@dataclass(frozen=True)
class Configuracao:
    dezenas: int
    quantidade: int


class GeradorError(ValueError):
    pass


def pode_gerar(modalidade: Modalidade) -> bool:
    return modalidade.extra not in {"colunas", "loteca"}


def chave_jogo(jogo: Jogo, modalidade: Modalidade) -> tuple[int, ...]:
    if modalidade.extra == "colunas":
        return tuple(jogo.dezenas)
    return tuple(sorted(jogo.dezenas))


def parse_configs(valores: list[str] | tuple[str, ...]) -> list[Configuracao]:
    configs: list[Configuracao] = []
    for item in valores:
        if isinstance(item, (list, tuple)):
            configs.extend(parse_configs(list(item)))
            continue
        for parte in str(item).replace(",", " ").split():
            if parte:
                configs.append(parse_config(parte))
    return configs


def parse_config(texto: str) -> Configuracao:
    bruto = texto.strip().lower().replace("x", ":").replace("-", ":")
    if ":" not in bruto:
        raise GeradorError(
            f"configuração inválida: {texto!r} (use dezenas:quantidade)")
    esq, dir_ = bruto.split(":", 1)
    try:
        dezenas = int(esq)
        quantidade = int(dir_)
    except ValueError as exc:
        raise GeradorError(f"configuração inválida: {texto!r}") from exc
    if dezenas <= 0 or quantidade <= 0:
        raise GeradorError(f"configuração inválida: {texto!r}")
    return Configuracao(dezenas, quantidade)


def validar_configuracao(config: Configuracao, modalidade: Modalidade) -> None:
    if not pode_gerar(modalidade):
        raise GeradorError(
            f"{modalidade.nome} não tem gerador aleatório nesta versão."
        )
    if not modalidade.min_dezenas <= config.dezenas <= modalidade.max_dezenas:
        raise GeradorError(
            f"{modalidade.nome} aceita {modalidade.min_dezenas}–"
            f"{modalidade.max_dezenas} dezenas, veio {config.dezenas}"
        )


def _extras_aleatorios(modalidade: Modalidade, rng: random.Random) -> dict[str, object]:
    if modalidade.extra == "mes":
        return {"mes": rng.randint(1, 12)}
    if modalidade.extra == "time":
        return {"time": rng.randint(1, 80)}
    if modalidade.extra == "trevos":
        return {"trevos": sorted(rng.sample(range(1, 7), 2))}
    return {}


def gerar_um(
    modalidade: Modalidade,
    qtd_dezenas: int,
    vistos: set[tuple[int, ...]],
    rng: random.Random | None = None,
    *,
    linha: int = 0,
) -> Jogo:
    rng = rng or random.Random()
    validar_configuracao(Configuracao(qtd_dezenas, 1), modalidade)
    universo = list(range(modalidade.dezena_min, modalidade.dezena_max + 1))
    for _ in range(20_000):
        dezenas = sorted(rng.sample(universo, qtd_dezenas))
        chave = tuple(dezenas)
        if chave in vistos:
            continue
        vistos.add(chave)
        ident = "".join(f"{n:0{modalidade.largura_digitos}d}" for n in dezenas)
        return Jogo(
            identificador=ident,
            dezenas=dezenas,
            linha=linha,
            extras=_extras_aleatorios(modalidade, rng),
            numeros_brutos=ident,
        )
    raise GeradorError(
        "não consegui gerar um jogo inédito; o espaço de combinações esgotou")


def aplicar_configs_ao_restante(
    configs: list[Configuracao],
    restante: int,
    *,
    dezenas_padrao: int | None = None,
) -> list[Configuracao]:
    if restante <= 0:
        return []
    saida: list[Configuracao] = []
    falta = restante
    for config in configs:
        if falta <= 0:
            break
        qtd = min(config.quantidade, falta)
        saida.append(Configuracao(config.dezenas, qtd))
        falta -= qtd
    if falta > 0 and dezenas_padrao is not None:
        saida.append(Configuracao(dezenas_padrao, falta))
    return saida


def gerar_jogos(
    modalidade: Modalidade,
    configs: list[Configuracao],
    *,
    vistos: set[tuple[int, ...]] | None = None,
    rng: random.Random | None = None,
    linha_inicio: int = 1000,
) -> list[Jogo]:
    rng = rng or random.Random()
    usados = set(vistos or ())
    jogos: list[Jogo] = []
    linha = linha_inicio
    for config in configs:
        validar_configuracao(config, modalidade)
        for _ in range(config.quantidade):
            jogos.append(
                gerar_um(
                    modalidade,
                    config.dezenas,
                    usados,
                    rng,
                    linha=linha,
                )
            )
            linha += 1
    return jogos


def completar_ate_limite(
    existentes: list[Jogo],
    modalidade: Modalidade,
    configs: list[Configuracao],
    limite: int,
    rng: random.Random | None = None,
) -> list[Jogo]:
    base = list(existentes)
    if limite <= 0:
        return base
    if len(base) >= limite:
        return base[:limite]
    falta = limite - len(base)
    usados = {chave_jogo(jogo, modalidade) for jogo in base}
    recorte = aplicar_configs_ao_restante(
        configs, falta, dezenas_padrao=modalidade.min_dezenas
    )
    if not recorte:
        recorte = [Configuracao(modalidade.min_dezenas, falta)]
    gerados = gerar_jogos(
        modalidade,
        recorte,
        vistos=usados,
        rng=rng,
        linha_inicio=10_000,
    )
    return base + gerados
