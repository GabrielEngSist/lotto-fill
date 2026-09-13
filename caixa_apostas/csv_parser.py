"""Leitura do CSV de jogos (Jogo, D1..DN, Numeros)."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from caixa_apostas.modalidades import MESES, Modalidade


@dataclass
class Jogo:
    identificador: str
    dezenas: list[int]
    linha: int
    extras: dict[str, object] = field(default_factory=dict)
    numeros_brutos: str = ""

    def dezenas_formatadas(self, largura: int = 2) -> str:
        return " ".join(f"{n:0{largura}d}" for n in self.dezenas)


@dataclass
class ResultadoLeitura:
    jogos: list[Jogo]
    avisos: list[str]
    erros: list[str]


_SEP_NUMEROS = re.compile(r"[\s,;|/\-]+")
_COLUNA_D = re.compile(r"^d\s*(\d+)$", re.IGNORECASE)


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalizar_coluna(nome: str) -> str:
    return _sem_acento(nome).strip().lower().replace(" ", "")


def detectar_delimitador(amostra: str) -> str:
    amostra = amostra.lstrip("\ufeff")
    try:
        return csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        pass
    candidatos = [",", ";", "\t", "|"]
    return max(candidatos, key=lambda d: amostra.count(d))


def _para_int(valor: object) -> int | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    texto = texto.replace(".0", "") if re.fullmatch(r"\d+\.0", texto) else texto
    if not re.fullmatch(r"-?\d+", texto):
        return None
    return int(texto)


def parse_numeros_concatenados(texto: str, largura: int) -> list[int]:
    """Quebra a string Numeros em dezenas.

    Aceita '051223334455', '05 12 23 33 44 55', '05,12,23' ou '05-12-23'.
    """
    bruto = str(texto).strip()
    if not bruto:
        return []
    if _SEP_NUMEROS.search(bruto):
        partes = [p for p in _SEP_NUMEROS.split(bruto) if p]
        dezenas: list[int] = []
        for parte in partes:
            if re.fullmatch(r"\d+", parte):
                dezenas.append(int(parte))
        return dezenas
    so_digitos = re.sub(r"\D", "", bruto)
    if not so_digitos:
        return []
    if largura <= 0:
        raise ValueError("largura de dígitos inválida")
    if len(so_digitos) % largura != 0:
        raise ValueError(
            f"string de números {bruto!r} tem {len(so_digitos)} dígitos, "
            f"não é múltiplo de {largura}"
        )
    return [int(so_digitos[i : i + largura]) for i in range(0, len(so_digitos), largura)]


def _colunas_d(cabecalho: list[str]) -> list[str]:
    pares: list[tuple[int, str]] = []
    for original in cabecalho:
        nome = normalizar_coluna(original)
        m = _COLUNA_D.match(nome)
        if m:
            pares.append((int(m.group(1)), original))
    pares.sort(key=lambda item: item[0])
    return [original for _, original in pares]


def _buscar_coluna(mapa: dict[str, str], *nomes: str) -> str | None:
    for nome in nomes:
        if nome in mapa:
            return mapa[nome]
    return None


def _parse_mes(valor: object) -> int | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    numero = _para_int(texto)
    if numero is not None:
        if 1 <= numero <= 12:
            return numero
        return None
    chave = _sem_acento(texto).strip().lower()
    return MESES.get(chave)


def _parse_lista_int(valor: object) -> list[int]:
    if valor is None:
        return []
    texto = str(valor).strip()
    if not texto:
        return []
    partes = _SEP_NUMEROS.split(texto) if _SEP_NUMEROS.search(texto) else [texto]
    saida: list[int] = []
    for parte in partes:
        parte = parte.strip().upper().lstrip("T").lstrip("TM")
        n = _para_int(parte)
        if n is not None:
            saida.append(n)
    return saida


def _parse_loteca(tokens: list[str]) -> list[str]:
    palpites: list[str] = []
    for token in tokens:
        t = token.strip().upper()
        if not t:
            continue
        if t in {"1", "X", "2"}:
            mapa = {"1": "X--", "X": "-X-", "2": "--X"}
            palpites.append(mapa[t])
            continue
        if re.fullmatch(r"[X\-1]{1,3}", t):
            t = t.replace("1", "X")
            t = (t + "---")[:3]
            palpites.append(t)
            continue
        palpites.append(t)
    return palpites


def ler_csv(caminho: str | Path, modalidade: Modalidade) -> ResultadoLeitura:
    path = Path(caminho)
    if not path.is_file():
        raise FileNotFoundError(f"CSV não encontrado: {path}")
    bruto = path.read_text(encoding="utf-8-sig")
    return ler_csv_texto(bruto, modalidade, origem=str(path))


def ler_csv_texto(
    texto: str,
    modalidade: Modalidade,
    origem: str = "<memória>",
) -> ResultadoLeitura:
    texto = texto.lstrip("\ufeff")
    if not texto.strip():
        return ResultadoLeitura([], [], [f"{origem}: arquivo vazio"])

    delimitador = detectar_delimitador(texto)
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not leitor.fieldnames:
        return ResultadoLeitura([], [], [f"{origem}: CSV sem cabeçalho"])

    originais = [c for c in leitor.fieldnames if c is not None]
    mapa = {normalizar_coluna(c): c for c in originais}
    col_jogo = _buscar_coluna(mapa, "jogo", "id", "identificador")
    col_numeros = _buscar_coluna(mapa, "numeros", "numero", "dezenas")
    colunas_d = _colunas_d(originais)
    col_mes = _buscar_coluna(mapa, "mes", "messorte", "mesdosorte")
    col_time = _buscar_coluna(mapa, "time", "timecoracao", "timeheart")
    col_trevos = _buscar_coluna(mapa, "trevos", "trevo")
    col_espelho = _buscar_coluna(mapa, "espelho")
    col_loteca = _buscar_coluna(mapa, "palpites", "loteca")

    jogos: list[Jogo] = []
    avisos: list[str] = []
    erros: list[str] = []

    for i, linha in enumerate(leitor, start=2):
        valores_d: list[int] = []
        for col in colunas_d:
            n = _para_int(linha.get(col))
            if n is not None:
                valores_d.append(n)

        texto_numeros = ""
        if col_numeros:
            texto_numeros = str(linha.get(col_numeros) or "").strip()

        identificador = ""
        if col_jogo:
            identificador = str(linha.get(col_jogo) or "").strip()

        dezenas: list[int] = []
        extras: dict[str, object] = {}

        if modalidade.extra == "loteca":
            tokens: list[str] = []
            if valores_d:
                tokens = [str(v) for v in valores_d]
            elif texto_numeros:
                tokens = [p for p in _SEP_NUMEROS.split(texto_numeros) if p]
            elif identificador:
                tokens = [p for p in _SEP_NUMEROS.split(identificador) if p]
            extras["loteca"] = _parse_loteca(tokens)
            dezenas = []
        else:
            if valores_d:
                dezenas = valores_d
            elif texto_numeros:
                try:
                    dezenas = parse_numeros_concatenados(
                        texto_numeros, modalidade.largura_digitos
                    )
                except ValueError as exc:
                    erros.append(f"linha {i}: {exc}")
                    continue
            elif identificador:
                try:
                    dezenas = parse_numeros_concatenados(
                        identificador, modalidade.largura_digitos
                    )
                except ValueError as exc:
                    erros.append(
                        f"linha {i}: sem dezenas em D1..DN/Numeros e "
                        f"Jogo não pôde ser interpretado ({exc})"
                    )
                    continue
            else:
                erros.append(f"linha {i}: nenhuma dezena encontrada")
                continue

            if modalidade.chave == "lotomania":
                dezenas = [n % 100 for n in dezenas]

        if not identificador:
            identificador = (
                "".join(f"{n:0{modalidade.largura_digitos}d}" for n in dezenas)
                or f"linha-{i}"
            )

        if col_mes and linha.get(col_mes):
            mes = _parse_mes(linha.get(col_mes))
            if mes:
                extras["mes"] = mes
            else:
                avisos.append(f"linha {i}: mês inválido {linha.get(col_mes)!r}")
        if col_time and linha.get(col_time):
            times = _parse_lista_int(linha.get(col_time))
            if times:
                extras["time"] = times[0]
        if col_trevos and linha.get(col_trevos):
            extras["trevos"] = _parse_lista_int(linha.get(col_trevos))
        if col_espelho and str(linha.get(col_espelho) or "").strip().lower() in {
            "1",
            "sim",
            "true",
            "s",
            "x",
        }:
            extras["espelho"] = True
        if col_loteca and linha.get(col_loteca) and "loteca" not in extras:
            tokens = [p for p in _SEP_NUMEROS.split(str(linha.get(col_loteca))) if p]
            extras["loteca"] = _parse_loteca(tokens)

        # extras embutidos no final de Numeros (T1 T2, JAN, TM12)
        if texto_numeros:
            _extrair_extras_do_texto(texto_numeros, extras)

        jogos.append(
            Jogo(
                identificador=identificador,
                dezenas=dezenas,
                linha=i,
                extras=extras,
                numeros_brutos=texto_numeros,
            )
        )

    return ResultadoLeitura(jogos=jogos, avisos=avisos, erros=erros)


def _extrair_extras_do_texto(texto: str, extras: dict[str, object]) -> None:
    tokens = [t for t in re.split(r"[\s,;|]+", texto.strip()) if t]
    trevos: list[int] = []
    for token in tokens:
        up = token.upper()
        if re.fullmatch(r"T[1-6]", up):
            trevos.append(int(up[1]))
        elif re.fullmatch(r"TM\d{1,2}", up) and "time" not in extras:
            extras["time"] = int(up[2:])
        else:
            mes = MESES.get(_sem_acento(token).strip().lower())
            if mes and "mes" not in extras:
                extras["mes"] = mes
    if trevos and "trevos" not in extras:
        extras["trevos"] = trevos


def validar_jogos(
    jogos: list[Jogo],
    modalidade: Modalidade,
) -> tuple[list[Jogo], list[str]]:
    validos: list[Jogo] = []
    erros: list[str] = []
    vistos: set[tuple[int, ...]] = set()

    for jogo in jogos:
        if modalidade.extra == "loteca":
            palpites = jogo.extras.get("loteca") or []
            if len(palpites) != 14:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): "
                    f"Loteca exige 14 palpites, veio {len(palpites)}"
                )
                continue
            validos.append(jogo)
            continue

        qtd = len(jogo.dezenas)
        if qtd < modalidade.min_dezenas or qtd > modalidade.max_dezenas:
            erros.append(
                f"linha {jogo.linha} ({jogo.identificador}): "
                f"{qtd} dezenas, esperado {modalidade.min_dezenas}"
                f"–{modalidade.max_dezenas} para {modalidade.nome}"
            )
            continue

        fora = [
            n
            for n in jogo.dezenas
            if n < modalidade.dezena_min or n > modalidade.dezena_max
        ]
        if fora:
            erros.append(
                f"linha {jogo.linha} ({jogo.identificador}): "
                f"dezenas fora da faixa {modalidade.dezena_min}–"
                f"{modalidade.dezena_max}: {fora}"
            )
            continue

        if modalidade.extra != "colunas":
            unicos = list(dict.fromkeys(jogo.dezenas))
            if len(unicos) != len(jogo.dezenas):
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): dezenas repetidas"
                )
                continue
            chave = tuple(sorted(jogo.dezenas))
        else:
            chave = tuple(jogo.dezenas)

        if chave in vistos:
            erros.append(
                f"linha {jogo.linha} ({jogo.identificador}): jogo duplicado no CSV"
            )
            continue
        vistos.add(chave)

        if modalidade.extra == "mes":
            mes = jogo.extras.get("mes")
            if mes is None:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): "
                    "Dia de Sorte exige coluna Mes (1–12 ou JAN–DEZ)"
                )
                continue
            if not isinstance(mes, int) or not 1 <= mes <= 12:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): mês inválido {mes!r}"
                )
                continue

        if modalidade.extra == "time":
            time = jogo.extras.get("time")
            if time is None:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): "
                    "Timemania exige coluna Time (1–80)"
                )
                continue
            if not isinstance(time, int) or not 1 <= time <= 80:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): time inválido {time!r}"
                )
                continue

        if modalidade.extra == "trevos":
            trevos = jogo.extras.get("trevos") or []
            if not isinstance(trevos, list) or len(trevos) < 2:
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): "
                    "+Milionária exige ao menos 2 trevos (coluna Trevos)"
                )
                continue
            if any(t < 1 or t > 6 for t in trevos):
                erros.append(
                    f"linha {jogo.linha} ({jogo.identificador}): trevos devem ser 1–6"
                )
                continue

        validos.append(jogo)

    return validos, erros
