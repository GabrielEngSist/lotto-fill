from caixa_apostas.cli import main, perguntar_modalidade
from caixa_apostas.favorito import nome_favorito_padrao


def test_listar_modalidades(capsys):
    assert main(["--listar"]) == 0
    saida = capsys.readouterr().out
    assert "mega-sena" in saida
    assert "lotofacil" in saida


def test_dry_run_megasena(capsys):
    codigo = main(
        [
            "exemplos/megasena.csv",
            "--modalidade",
            "mega-sena",
            "--dry-run",
        ]
    )
    assert codigo == 0
    saida = capsys.readouterr().out
    assert "3 jogo(s) prontos" in saida
    assert "Dry-run" in saida


def test_dry_run_lotofacil():
    assert (
        main(
            [
                "exemplos/lotofacil.csv",
                "--modalidade",
                "lotofacil",
                "--dry-run",
            ]
        )
        == 0
    )


def test_dry_run_dia_de_sorte():
    assert (
        main(
            [
                "exemplos/dia_de_sorte.csv",
                "--modalidade",
                "dia-de-sorte",
                "--dry-run",
            ]
        )
        == 0
    )


def test_nome_favorito_usa_planilha_ou_flag():
    assert (
        nome_favorito_padrao("~/Downloads/Lotofacil_163_apostas_otimizadas.csv")
        == "Lotofacil_163_apostas_otimizadas"
    )
    assert nome_favorito_padrao("jogos.csv", "  Meu Carrinho  ") == "Meu Carrinho"
    assert nome_favorito_padrao("jogos.csv", "") == "jogos"


def test_csv_ausente():
    assert main(["nao-existe.csv", "--modalidade", "quina", "--dry-run"]) == 2


def test_sem_csv_mostra_ajuda(capsys):
    assert main([]) == 2
    err = capsys.readouterr().err
    assert "CSV" in err


def test_prompt_escolhe_por_numero():
    respostas = iter(["1"])
    modalidade = perguntar_modalidade(input_fn=lambda _: next(respostas))
    assert modalidade.chave == "mega-sena"


def test_prompt_escolhe_por_nome():
    respostas = iter(["lotofacil"])
    modalidade = perguntar_modalidade(input_fn=lambda _: next(respostas))
    assert modalidade.nome == "Lotofácil"


def test_listar_sessoes(capsys):
    codigo = main(["--listar-sessoes"])
    assert codigo in (0, 1)
    saida = capsys.readouterr().out.lower()
    assert "sess" in saida or "nenhuma" in saida


def test_navegador_invalido(capsys):
    codigo = main(["--listar-sessoes", "--navegador", "safari"])
    assert codigo == 2
    err = capsys.readouterr().err
    assert "safari" in err.lower() or "desconhecido" in err.lower()
