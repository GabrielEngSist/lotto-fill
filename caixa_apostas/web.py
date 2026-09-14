"""Servidor local do Lotto Fill (interface web, só biblioteca padrão)."""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from caixa_apostas.csv_parser import Jogo, escrever_csv, validar_jogos
from caixa_apostas.favorito import nome_favorito_padrao
from caixa_apostas.gerador import Configuracao, GeradorError, chave_jogo, gerar_jogos, pode_gerar
from caixa_apostas.modalidades import Modalidade, listar_modalidades, obter_modalidade
from caixa_apostas.navegador_cookies import buscar_cookies_navegador
from caixa_apostas.simulador import (
    chance_conjunto,
    custo_com_teimosinha,
    formatar_chance,
    formatar_reais,
    linha_simulacao,
    simular_jogos,
    valor_por_cota,
)

WEBUI = Path(__file__).resolve().parent / "webui"
ROOT = Path(__file__).resolve().parent.parent
CORES = {
    "mega-sena": "#209869",
    "mega-da-virada": "#209869",
    "lotofacil": "#930089",
    "lotofacil-independencia": "#930089",
    "quina": "#260085",
    "quina-sao-joao": "#260085",
    "lotomania": "#F78100",
    "dupla-sena": "#A61324",
    "dia-de-sorte": "#CB852B",
    "timemania": "#3FA435",
    "mais-milionaria": "#2E3078",
    "super-sete": "#A88CD3",
    "loteca": "#FF1A13",
}
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


class ControleServidor:
    """Encerra o processo quando a aba do navegador some."""

    def __init__(self) -> None:
        self.servidor: ThreadingHTTPServer | None = None
        self.inicio = time.monotonic()
        self.ultimo = 0.0
        self.viu_pagina = False
        self._lock = threading.Lock()

    def vivo(self) -> None:
        with self._lock:
            self.viu_pagina = True
            self.ultimo = time.monotonic()

    def pedir_saida(self) -> None:
        threading.Timer(2.0, self._sair_se_sumiu).start()

    def _sair_se_sumiu(self) -> None:
        with self._lock:
            if self.viu_pagina and time.monotonic() - self.ultimo < 1.8:
                return
        self.parar()

    def parar(self) -> None:
        if self.servidor is None:
            return
        threading.Thread(target=self.servidor.shutdown, daemon=True).start()

    def vigiar(self) -> None:
        while True:
            time.sleep(2)
            agora = time.monotonic()
            with self._lock:
                if not self.viu_pagina:
                    if agora - self.inicio > 45:
                        self.parar()
                        return
                    continue
                if agora - self.ultimo > 12:
                    self.parar()
                    return


controle = ControleServidor()


def modalidade_json(m: Modalidade) -> dict[str, Any]:
    return {
        "chave": m.chave,
        "nome": m.nome,
        "min_dezenas": m.min_dezenas,
        "max_dezenas": m.max_dezenas,
        "dezena_min": m.dezena_min,
        "dezena_max": m.dezena_max,
        "largura_digitos": m.largura_digitos,
        "extra": m.extra,
        "especial": m.especial,
        "descricao_faixa": m.descricao_faixa,
        "cor": CORES.get(m.chave, "#005CA9"),
        "pode_gerar": pode_gerar(m),
    }


def jogo_de_json(item: dict[str, Any], linha: int = 0) -> Jogo:
    dezenas = [int(n) for n in item.get("dezenas") or []]
    extras = dict(item.get("extras") or {})
    ident = str(item.get("identificador") or "").strip()
    if not ident:
        ident = "".join(f"{n:02d}" for n in dezenas)
    return Jogo(
        identificador=ident,
        dezenas=dezenas,
        linha=int(item.get("linha") or linha),
        extras=extras,
        numeros_brutos=str(item.get("numeros_brutos") or ident),
    )


def jogo_json(jogo: Jogo) -> dict[str, Any]:
    return {
        "identificador": jogo.identificador,
        "dezenas": list(jogo.dezenas),
        "linha": jogo.linha,
        "extras": dict(jogo.extras),
        "numeros_brutos": jogo.numeros_brutos,
    }


def api_modalidades() -> dict[str, Any]:
    return {"ok": True, "dados": [modalidade_json(m) for m in listar_modalidades()]}


def api_parse_csv(dados: dict[str, Any]) -> dict[str, Any]:
    from caixa_apostas.csv_parser import ler_csv_texto

    modalidade = obter_modalidade(str(dados.get("modalidade") or "lotofacil"))
    texto = str(dados.get("csv") or "")
    if not texto.strip():
        raise ValueError("envie o conteúdo da planilha")
    origem = str(dados.get("nome") or "planilha.csv")
    leitura = ler_csv_texto(texto, modalidade, origem=origem)
    validos, erros = validar_jogos(leitura.jogos, modalidade)
    return {
        "ok": True,
        "jogos": [jogo_json(j) for j in validos],
        "avisos": list(leitura.avisos),
        "erros": list(leitura.erros) + erros,
    }


def api_surpresinha(dados: dict[str, Any]) -> dict[str, Any]:
    modalidade = obter_modalidade(str(dados.get("modalidade") or "lotofacil"))
    dez = int(dados.get("dezenas") or modalidade.min_dezenas)
    qtd = int(dados.get("quantidade") or 1)
    existentes = [
        jogo_de_json(item, i) for i, item in enumerate(dados.get("existentes") or [], start=1)
    ]
    usados = {chave_jogo(j, modalidade) for j in existentes}
    novos = gerar_jogos(modalidade, [Configuracao(dez, qtd)], vistos=usados)
    return {"ok": True, "jogos": [jogo_json(j) for j in novos]}


def api_simular(dados: dict[str, Any]) -> dict[str, Any]:
    modalidade = obter_modalidade(str(dados.get("modalidade") or "lotofacil"))
    jogos = [jogo_de_json(item, i) for i, item in enumerate(
        dados.get("jogos") or [], start=1)]
    if not jogos:
        raise ValueError("o carrinho está vazio")
    resultados = simular_jogos(jogos, modalidade)
    teimosinha = int(dados.get("teimosinha") or 0)
    cotas = max(1, int(dados.get("cotas") or 1))
    preco = sum(item.preco for item in resultados)
    total = custo_com_teimosinha(preco, teimosinha)
    por_pessoa = valor_por_cota(total, cotas)
    return {
        "ok": True,
        "linhas": [linha_simulacao(i, item, modalidade).strip() for i, item in enumerate(resultados, start=1)],
        "subtotal": formatar_reais(preco),
        "total": formatar_reais(total),
        "cotas": cotas,
        "por_cota": formatar_reais(por_pessoa),
        "chance_premio": formatar_chance(chance_conjunto([i.p_qualquer for i in resultados])),
        "chance_max": formatar_chance(chance_conjunto([i.p_maximo for i in resultados])),
        "acertos_maximo": resultados[0].acertos_maximo,
        "teimosinha": teimosinha,
        "quantidade": len(jogos),
    }


def api_csv(dados: dict[str, Any]) -> tuple[bytes, str]:
    modalidade = obter_modalidade(str(dados.get("modalidade") or "lotofacil"))
    jogos = [jogo_de_json(item, i) for i, item in enumerate(
        dados.get("jogos") or [], start=1)]
    if not jogos:
        raise ValueError("o carrinho está vazio")
    tmp = ROOT / "planilhas" / \
        f"apostas_{modalidade.chave}_{len(jogos)}jogos.csv"
    escrever_csv(tmp, jogos, modalidade)
    return tmp.read_bytes(), tmp.name


def api_enviar(dados: dict[str, Any]) -> dict[str, Any]:
    modalidade = obter_modalidade(str(dados.get("modalidade") or "lotofacil"))
    jogos = [jogo_de_json(item, i) for i, item in enumerate(
        dados.get("jogos") or [], start=1)]
    if not jogos:
        raise ValueError("o carrinho está vazio")
    teimosinha = int(dados.get("teimosinha") or 0)
    nome = str(dados.get("nome") or "").strip()
    salvar_fav = bool(dados.get("salvar_favorito", True))
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"done": False, "logs": [],
                         "ok": 0, "falhas": 0, "erro": None}
    threading.Thread(
        target=_rodar_envio,
        args=(job_id, modalidade, jogos, teimosinha, nome, salvar_fav),
        daemon=True,
    ).start()
    return {"ok": True, "job_id": job_id}


def api_job(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise KeyError("envio não encontrado")
        return {"ok": True, **job}


def _log_job(job_id: str, msg: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is not None:
            job["logs"].append(msg)


def _rodar_envio(
    job_id: str,
    modalidade: Modalidade,
    jogos: list[Jogo],
    teimosinha: int,
    nome: str,
    salvar_fav: bool,
) -> None:
    try:
        from caixa_apostas.browser import CaixaBrowser

        saida = ROOT / "planilhas" / \
            f"apostas_{modalidade.chave}_{len(jogos)}jogos.csv"
        escrever_csv(saida, jogos, modalidade)
        _log_job(job_id, f"Planilha gravada em {saida}")
        sessao = buscar_cookies_navegador("auto")
        cookies = sessao.cookies if sessao else []
        favorito = nome_favorito_padrao(saida, nome or None)
        with CaixaBrowser(
            cookies=cookies,
            modalidade=modalidade,
            teimosinha=teimosinha,
            screenshots=ROOT / "screenshots",
            log=lambda msg: _log_job(job_id, msg),
            manter_aberto=True,
        ) as caixa:
            caixa.aguardar_login_manual()
            caixa.abrir_modalidade()
            relatorio = caixa.preencher_jogos(jogos)
            if relatorio.ok and salvar_fav:
                caixa.salvar_carrinho_favorito(favorito)
        with _jobs_lock:
            _jobs[job_id]["ok"] = len(relatorio.ok)
            _jobs[job_id]["falhas"] = len(relatorio.falhas)
            _jobs[job_id]["done"] = True
        _log_job(
            job_id, "Pronto. Confira o carrinho no navegador da Caixa antes de pagar.")
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["erro"] = str(exc)
            _jobs[job_id]["done"] = True
        _log_job(job_id, f"Erro: {exc}")


class LottoFillHandler(BaseHTTPRequestHandler):
    def log_message(self, formato: str, *args: Any) -> None:
        print(f"  {self.address_string()} {formato % args}")

    def _ler_corpo(self) -> bytes:
        tamanho = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(tamanho) if tamanho else b""

    def _corpo(self) -> dict[str, Any]:
        bruto = self._ler_corpo()
        if not bruto:
            return {}
        return json.loads(bruto.decode("utf-8"))

    def _json(self, codigo: int, dados: dict[str, Any]) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _arquivo(self, caminho: Path) -> None:
        alvo = (WEBUI / caminho.name).resolve()
        if alvo.parent != WEBUI.resolve() or not alvo.is_file():
            self._json(404, {"erro": "não encontrado"})
            return
        dados = alvo.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", TIPOS.get(alvo.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            controle.vivo()
            self._arquivo(WEBUI / "index.html")
            return
        if path.startswith("/static/"):
            self._arquivo(WEBUI / Path(path).name)
            return
        if path == "/api/vivo":
            controle.vivo()
            self._json(200, {"ok": True})
            return
        if path == "/api/modalidades":
            self._json(200, [modalidade_json(m) for m in listar_modalidades()])
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            try:
                self._json(200, api_job(job_id))
            except KeyError as exc:
                self._json(404, {"erro": str(exc)})
            return
        self._json(404, {"erro": "não encontrado"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/vivo":
            self._ler_corpo()
            controle.vivo()
            self._json(200, {"ok": True})
            return
        if path == "/api/sair":
            self._ler_corpo()
            controle.pedir_saida()
            self._json(200, {"ok": True})
            return
        try:
            dados = self._corpo()
            if path == "/api/parse-csv":
                self._json(200, api_parse_csv(dados))
                return
            if path == "/api/surpresinha":
                self._json(200, api_surpresinha(dados))
                return
            if path == "/api/simular":
                self._json(200, api_simular(dados))
                return
            if path == "/api/csv":
                conteudo, nome = api_csv(dados)
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{nome}"')
                self.send_header("Content-Length", str(len(conteudo)))
                self.end_headers()
                self.wfile.write(conteudo)
                return
            if path == "/api/enviar":
                self._json(200, api_enviar(dados))
                return
            self._json(404, {"erro": "não encontrado"})
        except (ValueError, GeradorError, json.JSONDecodeError, KeyError) as exc:
            self._json(400, {"erro": str(exc)})
        except Exception as exc:
            self._json(500, {"erro": str(exc)})


def _porta_ocupada(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def main(host: str = "127.0.0.1", port: int = 8765) -> None:
    url = f"http://{host}:{port}/"
    if _porta_ocupada(host, port):
        webbrowser.open(url)
        print(f"Lotto Fill já estava aberto: {url}")
        return
    servidor = ThreadingHTTPServer((host, port), LottoFillHandler)
    controle.servidor = servidor
    threading.Thread(target=controle.vigiar, daemon=True).start()
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print(f"Lotto Fill aberto em {url}")
    print("Feche a aba do navegador para encerrar o aplicativo.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    servidor.server_close()
    print("Encerrado.")


if __name__ == "__main__":
    main()
