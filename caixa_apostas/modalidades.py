"""Modalidades oficiais do Loterias Online da Caixa."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Modalidade:
    chave: str
    nome: str
    menu_id: str
    hash_path: str
    api_slug: str
    min_dezenas: int
    max_dezenas: int
    dezena_min: int
    dezena_max: int
    largura_digitos: int = 2
    extra: str | None = None
    especial: bool = False

    @property
    def descricao_faixa(self) -> str:
        if self.extra == "colunas":
            return (
                f"{self.min_dezenas} colunas, dígitos de "
                f"{self.dezena_min} a {self.dezena_max}"
            )
        if self.extra == "loteca":
            return "14 jogos (1, X ou 2; duplo/triplo com XXX)"
        return (
            f"{self.min_dezenas} a {self.max_dezenas} dezenas, "
            f"de {self.dezena_min:02d} a {self.dezena_max:02d}"
        )


MEGA_SENA = Modalidade(
    chave="mega-sena",
    nome="Mega-Sena",
    menu_id="Mega-Sena",
    hash_path="mega-sena",
    api_slug="megasena",
    min_dezenas=6,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=60,
)

LOTOFACIL = Modalidade(
    chave="lotofacil",
    nome="Lotofácil",
    menu_id="Lotofacil",
    hash_path="lotofacil",
    api_slug="lotofacil",
    min_dezenas=15,
    max_dezenas=20,
    dezena_min=1,
    dezena_max=25,
)

QUINA = Modalidade(
    chave="quina",
    nome="Quina",
    menu_id="Quina",
    hash_path="quina",
    api_slug="quina",
    min_dezenas=5,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=80,
)

LOTOMANIA = Modalidade(
    chave="lotomania",
    nome="Lotomania",
    menu_id="Lotomania",
    hash_path="lotomania",
    api_slug="lotomania",
    min_dezenas=50,
    max_dezenas=50,
    dezena_min=0,
    dezena_max=99,
)

DUPLA_SENA = Modalidade(
    chave="dupla-sena",
    nome="Dupla Sena",
    menu_id="Dupla-Sena",
    hash_path="dupla-sena",
    api_slug="duplasena",
    min_dezenas=6,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=50,
)

DIA_DE_SORTE = Modalidade(
    chave="dia-de-sorte",
    nome="Dia de Sorte",
    menu_id="Dia-de-Sorte",
    hash_path="dia-de-sorte",
    api_slug="diadesorte",
    min_dezenas=7,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=31,
    extra="mes",
)

TIMEMANIA = Modalidade(
    chave="timemania",
    nome="Timemania",
    menu_id="Timemania",
    hash_path="timemania",
    api_slug="timemania",
    min_dezenas=10,
    max_dezenas=10,
    dezena_min=1,
    dezena_max=80,
    extra="time",
)

MAIS_MILIONARIA = Modalidade(
    chave="mais-milionaria",
    nome="+Milionária",
    menu_id="Mais-Milionaria",
    hash_path="maismilionaria",
    api_slug="maismilionaria",
    min_dezenas=6,
    max_dezenas=12,
    dezena_min=1,
    dezena_max=50,
    extra="trevos",
)

SUPER_SETE = Modalidade(
    chave="super-sete",
    nome="Super Sete",
    menu_id="Super-Sete",
    hash_path="supersete",
    api_slug="supersete",
    min_dezenas=7,
    max_dezenas=21,
    dezena_min=0,
    dezena_max=9,
    largura_digitos=1,
    extra="colunas",
)

LOTECA = Modalidade(
    chave="loteca",
    nome="Loteca",
    menu_id="Loteca",
    hash_path="loteca",
    api_slug="loteca",
    min_dezenas=14,
    max_dezenas=14,
    dezena_min=1,
    dezena_max=2,
    largura_digitos=1,
    extra="loteca",
)

MEGA_DA_VIRADA = Modalidade(
    chave="mega-da-virada",
    nome="Mega da Virada",
    menu_id="data-jogo-mega-sena-especial",
    hash_path="mega-sena/especial",
    api_slug="megasena",
    min_dezenas=6,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=60,
    especial=True,
)

LOTOFACIL_INDEPENDENCIA = Modalidade(
    chave="lotofacil-independencia",
    nome="Lotofácil da Independência",
    menu_id="data-jogo-lotofacil-especial",
    hash_path="lotofacil/especial",
    api_slug="lotofacil",
    min_dezenas=15,
    max_dezenas=20,
    dezena_min=1,
    dezena_max=25,
    especial=True,
)

QUINA_SAO_JOAO = Modalidade(
    chave="quina-sao-joao",
    nome="Quina de São João",
    menu_id="data-jogo-quina-especial",
    hash_path="quina/especial",
    api_slug="quina",
    min_dezenas=5,
    max_dezenas=15,
    dezena_min=1,
    dezena_max=80,
    especial=True,
)

MODALIDADES: tuple[Modalidade, ...] = (
    MEGA_SENA,
    LOTOFACIL,
    QUINA,
    LOTOMANIA,
    DUPLA_SENA,
    DIA_DE_SORTE,
    TIMEMANIA,
    MAIS_MILIONARIA,
    SUPER_SETE,
    LOTECA,
    MEGA_DA_VIRADA,
    LOTOFACIL_INDEPENDENCIA,
    QUINA_SAO_JOAO,
)

_ALIASES = {
    "megasena": "mega-sena",
    "mega": "mega-sena",
    "mega sena": "mega-sena",
    "lotofacil": "lotofacil",
    "loto facil": "lotofacil",
    "loto-facil": "lotofacil",
    "quina": "quina",
    "lotomania": "lotomania",
    "duplasena": "dupla-sena",
    "dupla sena": "dupla-sena",
    "dia de sorte": "dia-de-sorte",
    "diadesorte": "dia-de-sorte",
    "timemania": "timemania",
    "mais milionaria": "mais-milionaria",
    "+milionaria": "mais-milionaria",
    "maismilionaria": "mais-milionaria",
    "milionaria": "mais-milionaria",
    "super sete": "super-sete",
    "supersete": "super-sete",
    "loteca": "loteca",
    "mega da virada": "mega-da-virada",
    "virada": "mega-da-virada",
    "lotofacil da independencia": "lotofacil-independencia",
    "independencia": "lotofacil-independencia",
    "quina de sao joao": "quina-sao-joao",
    "sao joao": "quina-sao-joao",
}


def _normalizar(texto: str) -> str:
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", texto.strip().lower())
    sem_acento = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(sem_acento.replace("_", " ").replace("/", " ").split())


def obter_modalidade(identificador: str) -> Modalidade:
    chave = _normalizar(identificador)
    chave = _ALIASES.get(chave, chave.replace(" ", "-"))
    for modalidade in MODALIDADES:
        if modalidade.chave == chave:
            return modalidade
        if _normalizar(modalidade.nome) == _normalizar(identificador):
            return modalidade
    opcoes = ", ".join(m.chave for m in MODALIDADES)
    raise ValueError(f"Modalidade desconhecida: {identificador!r}. Use uma de: {opcoes}")


def listar_modalidades() -> tuple[Modalidade, ...]:
    return MODALIDADES


MESES = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}
