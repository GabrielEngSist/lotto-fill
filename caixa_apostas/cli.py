"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from caixa_apostas import __version__
from caixa_apostas.concurso import obter_info_concurso
from caixa_apostas.cookies import carregar_cookies
from caixa_apostas.csv_parser import Jogo, escrever_csv, ler_csv, validar_jogos
from caixa_apostas.favorito import nome_favorito_padrao
from caixa_apostas.gerador import (
    Configuracao,
    GeradorError,
    completar_ate_limite,
    parse_configs,
    pode_gerar,
)
from caixa_apostas.modalidades import Modalidade, listar_modalidades, obter_modalidade
from caixa_apostas.navegador_cookies import buscar_cookies_navegador, listar_sessoes
from caixa_apostas.simulador import (
    chance_conjunto,
    formatar_chance,
    formatar_reais,
    linha_simulacao,
    simular_jogos,
)


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
        help="arquivo CSV com colunas Jogo, D1, D2, …, DN, Numeros (opcional se --limite)",
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
        help="total de jogos (completa com aleatórios se a planilha tiver menos; sem CSV gera todos)",
    )
    parser.add_argument(
        "--config",
        nargs="+",
        action="append",
        default=[],
        metavar="DEZ:QTD",
        help="jogos na ordem informada (ex.: --config 18:2 20:1). O restante até o limite usa a aposta simples.",
    )
    parser.add_argument(
        "--saida",
        help="CSV gerado após o aceite (padrão: apostas_<modalidade>_<n>jogos.csv)",
    )
    parser.add_argument(
        "--aceitar",
        action="store_true",
        help="aceita a simulação sem perguntar",
    )
    parser.add_argument(
        "--enviar-site",
        action="store_true",
        help="depois da planilha, envia os jogos ao carrinho",
    )
    parser.add_argument(
        "--so-planilha",
        action="store_true",
        help="gera só a planilha, sem abrir o site",
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
        "--nome-favorito",
        help="nome ao salvar o carrinho como favorito (padrão: nome do arquivo CSV)",
    )
    parser.add_argument(
        "--sem-salvar-favorito",
        action="store_true",
        help="não salva o carrinho como favorito depois de incluir as apostas",
    )
    parser.add_argument(
        "--apenas-salvar-favorito",
        action="store_true",
        help="só salva o carrinho atual como favorito (precisa ter pelo menos uma aposta)",
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


def _perguntar_int(
    prompt: str,
    *,
    minimo: int,
    maximo: int,
    padrao: int | None = None,
    input_fn=input,
) -> int:
    sufixo = f" [{padrao}]" if padrao is not None else ""
    while True:
        bruto = input_fn(f"{prompt}{sufixo}: ").strip()
        if not bruto and padrao is not None:
            return padrao
        if not bruto.lstrip("-").isdigit():
            print(f"Informe um número entre {minimo} e {maximo}.")
            continue
        valor = int(bruto)
        if minimo <= valor <= maximo:
            return valor
        print(f"Informe um número entre {minimo} e {maximo}.")


def _perguntar_sim_nao(prompt: str, *, padrao: bool = False, input_fn=input) -> bool:
    dica = "S/n" if padrao else "s/N"
    bruto = input_fn(f"{prompt} [{dica}]: ").strip().lower()
    if not bruto:
        return padrao
    return bruto in {"s", "sim", "y", "yes"}


def _configs_da_flag(valores, modalidade: Modalidade) -> list[Configuracao]:
    configs = parse_configs(valores or [])
    for config in configs:
        if not modalidade.min_dezenas <= config.dezenas <= modalidade.max_dezenas:
            raise GeradorError(
                f"{modalidade.nome} aceita {modalidade.min_dezenas}–"
                f"{modalidade.max_dezenas} dezenas, veio {config.dezenas}"
            )
    return configs


def perguntar_configuracoes(
    modalidade: Modalidade,
    restante: int,
    input_fn=input,
) -> list[Configuracao]:
    configs: list[Configuracao] = []
    falta = restante
    while falta > 0:
        print()
        print(f"Faltam {falta} jogo(s) para completar o limite.")
        dezenas = _perguntar_int(
            f"Quantas dezenas ({modalidade.min_dezenas}–{modalidade.max_dezenas})",
            minimo=modalidade.min_dezenas,
            maximo=modalidade.max_dezenas,
            padrao=modalidade.min_dezenas,
            input_fn=input_fn,
        )
        qtd = _perguntar_int(
            "Quantos jogos nessa configuração",
            minimo=1,
            maximo=falta,
            padrao=falta,
            input_fn=input_fn,
        )
        configs.append(Configuracao(dezenas, qtd))
        falta -= qtd
        if falta <= 0:
            break
        if not _perguntar_sim_nao("Mais alguma configuração?", input_fn=input_fn):
            configs.append(Configuracao(dezenas, falta))
            break
    return configs


def _resolver_configs(
    modalidade: Modalidade,
    restante: int,
    args,
    input_fn=input,
) -> list[Configuracao]:
    if restante <= 0:
        return []
    if args.config:
        return _configs_da_flag(args.config, modalidade)
    if sys.stdin.isatty():
        return perguntar_configuracoes(modalidade, restante, input_fn=input_fn)
    return [Configuracao(modalidade.min_dezenas, restante)]


def _imprimir_simulacao(jogos: list[Jogo], modalidade: Modalidade) -> list:
    resultados = simular_jogos(jogos, modalidade)
    print()
    print("Simulação (preço e probabilidade de cada volante)")
    print("------------------------------------------------")
    for i, resultado in enumerate(resultados, start=1):
        print(linha_simulacao(i, resultado, modalidade))
    return resultados


def _imprimir_sumario(resultados, modalidade: Modalidade) -> None:
    total = sum(item.preco for item in resultados)
    p_premio = chance_conjunto([item.p_qualquer for item in resultados])
    p_max = chance_conjunto([item.p_maximo for item in resultados])
    print()
    print("Sumário do conjunto")
    print("-------------------")
    print(f"Modalidade: {modalidade.nome}")
    print(f"Jogos: {len(resultados)}")
    print(f"Custo total: {formatar_reais(total)}")
    print(f"Chance de pelo menos um prêmio: {formatar_chance(p_premio)}")
    if resultados:
        print(
            f"Chance de pelo menos um {resultados[0].acertos_maximo} acertos: "
            f"{formatar_chance(p_max)}"
        )


def _caminho_saida(args, modalidade: Modalidade, qtd: int, csv_path: Path | None) -> Path:
    if args.saida:
        return Path(args.saida)
    return Path(f"apostas_{modalidade.chave}_{qtd}jogos.csv")


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
        print(
            f"Usando {len(cookies)} cookie(s) informado(s) na linha de comando.")
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
        print(
            f"Encontrei o perfil {sessao.navegador}/{sessao.perfil}, mas não li os cookies.")
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

    csv_path = Path(args.csv) if args.csv else None
    if csv_path and not csv_path.is_file():
        print(f"CSV não encontrado: {csv_path}", file=sys.stderr)
        return 2
    if not csv_path and not args.limite and not args.apenas_salvar_favorito:
        parser.print_help()
        print("\nErro: informe o arquivo CSV ou --limite N.", file=sys.stderr)
        return 2
    if args.apenas_salvar_favorito and not csv_path:
        print("Para --apenas-salvar-favorito informe o CSV (usado no nome do favorito).", file=sys.stderr)
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

    validos: list[Jogo] = []
    erros_validacao: list[str] = []
    leitura_erros: list[str] = []
    if csv_path:
        leitura = ler_csv(csv_path, modalidade)
        for aviso in leitura.avisos:
            print(f"aviso: {aviso}")
        for erro in leitura.erros:
            print(f"erro de leitura: {erro}", file=sys.stderr)
            leitura_erros.append(erro)
        validos, erros_validacao = validar_jogos(leitura.jogos, modalidade)
        for erro in erros_validacao:
            print(f"jogo inválido: {erro}", file=sys.stderr)

    inicio = max(1, args.inicio)
    da_planilha = validos[inicio - 1:]
    if args.limite and args.limite > 0 and len(da_planilha) > args.limite:
        da_planilha = da_planilha[: args.limite]

    selecionados = list(da_planilha)
    precisa_aleatorio = bool(args.limite) and len(selecionados) < args.limite
    if not csv_path and args.limite:
        precisa_aleatorio = True

    if precisa_aleatorio:
        if not pode_gerar(modalidade):
            print(
                f"{modalidade.nome} não tem gerador aleatório. "
                "Informe um CSV completo.",
                file=sys.stderr,
            )
            return 2
        try:
            restante = args.limite - len(selecionados)
            configs = _resolver_configs(modalidade, restante, args)
            selecionados = completar_ate_limite(
                selecionados, modalidade, configs, args.limite
            )
        except GeradorError as exc:
            print(exc, file=sys.stderr)
            return 2

    if not selecionados and not args.apenas_salvar_favorito:
        print("Nenhum jogo válido para enviar.", file=sys.stderr)
        return 1

    if not args.apenas_salvar_favorito:
        _imprimir_preview(selecionados, modalidade)
        resultados = _imprimir_simulacao(selecionados, modalidade)
        aceitou = args.aceitar or not sys.stdin.isatty()
        if not aceitou:
            aceitou = _perguntar_sim_nao(
                "Aceita esta configuração e gera a planilha?", padrao=True
            )
        if not aceitou:
            print("Configuração recusada. Nada foi gravado.")
            return 1
        _imprimir_sumario(resultados, modalidade)
        gravar = bool(args.saida) or not args.dry_run or sys.stdin.isatty()
        saida = None
        if gravar:
            saida = _caminho_saida(
                args, modalidade, len(selecionados), csv_path)
            escrever_csv(saida, selecionados, modalidade)
            print(f"Planilha gravada em {saida}")
            csv_path = saida

    if args.dry_run:
        print()
        print("Dry-run: nada foi enviado ao site.")
        if erros_validacao or leitura_erros:
            return 1
        return 0

    enviar = False
    if args.apenas_salvar_favorito:
        enviar = True
    elif args.enviar_site:
        enviar = True
    elif args.so_planilha:
        enviar = False
    elif sys.stdin.isatty():
        enviar = _perguntar_sim_nao(
            "Enviar os jogos ao carrinho do site agora?", padrao=False
        )
    if not enviar:
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

    from caixa_apostas.browser import CaixaBrowser, Relatorio

    nome_favorito = nome_favorito_padrao(
        csv_path or "carrinho", args.nome_favorito)
    salvar_favorito = not args.sem_salvar_favorito
    relatorio = Relatorio()
    erro_favorito = None

    print()
    if args.apenas_salvar_favorito:
        print(f"Vou salvar o carrinho atual como favorito: {nome_favorito}")
    else:
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
            if not args.apenas_salvar_favorito:
                caixa.abrir_modalidade()
                relatorio = caixa.preencher_jogos(selecionados)
                salvar_favorito = salvar_favorito and bool(relatorio.ok)
            if salvar_favorito:
                try:
                    caixa.salvar_carrinho_favorito(nome_favorito)
                except Exception as exc:
                    erro_favorito = exc
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Falha na automação: {exc}", file=sys.stderr)
        return 1

    if not args.apenas_salvar_favorito:
        print()
        print("Relatório")
        print("---------")
        print(f"Incluídos no carrinho: {len(relatorio.ok)}")
        print(f"Falhas: {len(relatorio.falhas)}")
        for falha in relatorio.falhas:
            print(f"  - {falha.identificador}: {falha.detalhe}")
    if erro_favorito:
        print(
            f"Não consegui salvar o carrinho como favorito: {erro_favorito}",
            file=sys.stderr,
        )
    elif salvar_favorito:
        print(f"Carrinho favorito: {nome_favorito}")
    if relatorio.ok or args.apenas_salvar_favorito:
        print()
        print("Confira o carrinho no navegador antes de pagar.")
    if erro_favorito:
        return 1
    return 0 if not relatorio.falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
