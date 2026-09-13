"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from caixa_apostas import __version__
from caixa_apostas.concurso import obter_info_concurso
from caixa_apostas.cookies import carregar_cookies
from caixa_apostas.csv_parser import ler_csv, validar_jogos
from caixa_apostas.modalidades import Modalidade, listar_modalidades, obter_modalidade
from caixa_apostas.navegador_cookies import buscar_cookies_navegador, listar_sessoes


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="caixa-apostas",
        description=(
            "Lê um CSV de jogos e marca as dezenas no Loterias Online da Caixa, "
            "adicionando cada volante ao carrinho."
        ),
    )
    parser.add_argument(
        "csv",
        nargs="?",
        help="arquivo CSV com colunas Jogo, D1, D2, …, DN, Numeros",
    )
    parser.add_argument(
        "-m",
        "--modalidade",
        help="mega-sena, lotofacil, quina, lotomania, … (senão, pergunta no terminal)",
    )
    parser.add_argument(
        "--cookie",
        help="string Cookie copiada do DevTools (ex.: JSESSIONID=…; outro=…)",
    )
    parser.add_argument(
        "--cookie-arquivo",
        help="arquivo Netscape cookies.txt, JSON ou cabeçalho Cookie",
    )
    parser.add_argument(
        "--navegador",
        default="auto",
        help="de onde ler a sessão: auto, chrome, edge, firefox, brave, chromium",
    )
    parser.add_argument(
        "--sem-cookie-navegador",
        action="store_true",
        help="não tenta ler cookies automaticamente do Chrome/Edge/Firefox",
    )
    parser.add_argument(
        "--listar-sessoes",
        action="store_true",
        help="mostra as sessões da Caixa encontradas nos navegadores e sai",
    )
    parser.add_argument(
        "--teimosinha",
        type=int,
        default=0,
        help="quantas vezes clicar em + da Teimosinha (concursos seguintes)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.7,
        help="pausa em segundos entre um jogo e outro (padrão: 0.7)",
    )
    parser.add_argument(
        "--inicio",
        type=int,
        default=1,
        help="começar a partir deste jogo (1 = primeiro)",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="processar no máximo N jogos (0 = todos)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="navegador invisível (sem login manual)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="só valida o CSV e mostra o que seria marcado, sem abrir o site",
    )
    parser.add_argument(
        "--fechar",
        action="store_true",
        help="fecha o navegador ao terminar (por padrão ele fica aberto)",
    )
    parser.add_argument(
        "--screenshots",
        default="screenshots",
        help="pasta para capturas em caso de erro",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="lista as modalidades e sai",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"caixa-apostas {__version__}",
    )
    return parser


def perguntar_modalidade(input_fn=input) -> Modalidade:
    modalidades = listar_modalidades()
    print()
    print("Qual concurso você quer participar?")
    print()
    for i, m in enumerate(modalidades, start=1):
        marca = "  (especial)" if m.especial else ""
        print(f"  [{i:2d}] {m.nome:<28} {m.descricao_faixa}{marca}")
    print()
    while True:
        bruto = input_fn("Digite o número ou o nome da modalidade: ").strip()
        if not bruto:
            print("Informe uma modalidade.")
            continue
        if bruto.isdigit():
            idx = int(bruto)
            if 1 <= idx <= len(modalidades):
                return modalidades[idx - 1]
            print(f"Escolha um número entre 1 e {len(modalidades)}.")
            continue
        try:
            return obter_modalidade(bruto)
        except ValueError as exc:
            print(exc)


def perguntar_cookie(input_fn=input) -> str:
    print()
    print("Não achei uma sessão válida no navegador.")
    print("Cole o cookie (F12 → Rede → Cookie) ou deixe em branco para login manual.")
    print()
    try:
        return input_fn("Cookie: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _listar_sessoes(navegador: str) -> int:
    try:
        sessoes = listar_sessoes(navegador)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    if not sessoes:
        print(
            "Nenhuma sessão de loteriasonline.caixa.gov.br encontrada "
            "no Chrome, Edge ou Firefox."
        )
        print("Entre no site pelo navegador e rode de novo.")
        return 1
    print("Sessões encontradas (valores dos cookies não são exibidos):")
    print()
    for i, sessao in enumerate(sessoes, start=1):
        marca = " ← mais recente" if i == 1 and sessao.cookies else ""
        print(f"  {i}. {sessao.resumo()}{marca}")
        if sessao.aviso:
            print(f"     aviso: {sessao.aviso}")
    return 0


def _carregar_sessao(args) -> list:
    cookies = carregar_cookies(texto=args.cookie, arquivo=args.cookie_arquivo)
    if cookies:
        print(f"Usando {len(cookies)} cookie(s) informado(s) na linha de comando.")
        return cookies

    if args.sem_cookie_navegador:
        return []

    sessao = buscar_cookies_navegador(args.navegador)
    if sessao and sessao.cookies:
        print(f"Sessão lida automaticamente: {sessao.resumo()}")
        if not sessao.autenticada:
            print(
                "Não vi JSESSIONID nesse conjunto; se o site pedir login, "
                "entre na janela que vai abrir."
            )
        return sessao.cookies
    if sessao and sessao.aviso:
        print(f"Encontrei o perfil {sessao.navegador}/{sessao.perfil}, mas não li os cookies.")
        print(f"  {sessao.aviso}")
        print("Dica: feche o navegador e tente de novo, ou use o Firefox.")
    else:
        print(
            "Não achei cookie da Caixa nos navegadores instalados. "
            "Faça login em https://www.loteriasonline.caixa.gov.br e rode outra vez."
        )
    return []


def _imprimir_concurso(modalidade: Modalidade) -> None:
    print()
    print(f"Modalidade: {modalidade.nome}")
    print(f"Volante: {modalidade.descricao_faixa}")
    info = obter_info_concurso(modalidade)
    if info:
        print(f"Concurso: {info.resumo()}")
        print("As apostas entram no concurso em aberto no site (não é o último sorteado).")
    else:
        print(
            "Não consegui consultar o número do concurso agora. "
            "O site usa o concurso em aberto no momento da inclusão no carrinho."
        )


def _imprimir_preview(jogos, modalidade: Modalidade) -> None:
    print()
    print(f"{len(jogos)} jogo(s) prontos:")
    for jogo in jogos[:20]:
        extra = ""
        if "mes" in jogo.extras:
            extra = f"  mês={jogo.extras['mes']}"
        if "time" in jogo.extras:
            extra = f"  time={jogo.extras['time']}"
        if "trevos" in jogo.extras:
            extra = f"  trevos={jogo.extras['trevos']}"
        if "loteca" in jogo.extras:
            extra = f"  {jogo.extras['loteca']}"
        print(
            f"  • {jogo.identificador}: "
            f"{jogo.dezenas_formatadas(modalidade.largura_digitos)}{extra}"
        )
    if len(jogos) > 20:
        print(f"  … e mais {len(jogos) - 20}")


def main(argv: list[str] | None = None) -> int:
    parser = montar_parser()
    args = parser.parse_args(argv)

    if args.listar:
        for m in listar_modalidades():
            print(f"{m.chave:28} {m.nome} — {m.descricao_faixa}")
        return 0

    if args.listar_sessoes:
        return _listar_sessoes(args.navegador)

    if not args.csv:
        parser.print_help()
        print("\nErro: informe o arquivo CSV.", file=sys.stderr)
        return 2

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"CSV não encontrado: {csv_path}", file=sys.stderr)
        return 2

    try:
        if args.modalidade:
            modalidade = obter_modalidade(args.modalidade)
        elif sys.stdin.isatty():
            modalidade = perguntar_modalidade()
        else:
            print(
                "Informe --modalidade (ex.: --modalidade mega-sena) "
                "quando não houver terminal interativo.",
                file=sys.stderr,
            )
            return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    _imprimir_concurso(modalidade)

    leitura = ler_csv(csv_path, modalidade)
    for aviso in leitura.avisos:
        print(f"aviso: {aviso}")
    for erro in leitura.erros:
        print(f"erro de leitura: {erro}", file=sys.stderr)

    validos, erros_validacao = validar_jogos(leitura.jogos, modalidade)
    for erro in erros_validacao:
        print(f"jogo inválido: {erro}", file=sys.stderr)

    if not validos:
        print("Nenhum jogo válido para enviar.", file=sys.stderr)
        return 1

    inicio = max(1, args.inicio)
    selecionados = validos[inicio - 1 :]
    if args.limite and args.limite > 0:
        selecionados = selecionados[: args.limite]

    _imprimir_preview(selecionados, modalidade)

    if args.dry_run:
        print()
        print("Dry-run: nada foi enviado ao site.")
        if erros_validacao or leitura.erros:
            return 1
        return 0

    try:
        cookies = _carregar_sessao(args)
    except (OSError, ValueError) as exc:
        print(f"Cookie inválido: {exc}", file=sys.stderr)
        return 2

    if not cookies and sys.stdin.isatty() and not args.headless:
        texto = perguntar_cookie()
        if texto:
            try:
                cookies = carregar_cookies(texto=texto)
            except ValueError as exc:
                print(f"Cookie inválido: {exc}", file=sys.stderr)
                return 2

    from caixa_apostas.browser import CaixaBrowser

    print()
    print(
        "O script só coloca os jogos no carrinho. "
        "O pagamento você confirma no próprio site."
    )

    try:
        with CaixaBrowser(
            cookies=cookies,
            modalidade=modalidade,
            headless=args.headless,
            delay=args.delay,
            teimosinha=args.teimosinha,
            screenshots=Path(args.screenshots),
            log=print,
            manter_aberto=not args.fechar,
        ) as caixa:
            caixa.aguardar_login_manual()
            caixa.abrir_modalidade()
            relatorio = caixa.preencher_jogos(selecionados)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Falha na automação: {exc}", file=sys.stderr)
        return 1

    print()
    print("Relatório")
    print("---------")
    print(f"Incluídos no carrinho: {len(relatorio.ok)}")
    print(f"Falhas: {len(relatorio.falhas)}")
    for falha in relatorio.falhas:
        print(f"  - {falha.identificador}: {falha.detalhe}")
    if relatorio.ok:
        print()
        print("Confira o carrinho no navegador antes de pagar.")
    return 0 if not relatorio.falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
