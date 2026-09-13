"""Automação do volante no Loterias Online da Caixa (Playwright)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from caixa_apostas.csv_parser import Jogo
from caixa_apostas.modalidades import Modalidade

URL_HOME = "https://www.loteriasonline.caixa.gov.br/silce-web/#/"

JS_CLICK_EL = r"""
(id) => {
  const clickEl = (el) => {
    if (!el) return false;
    try { el.scrollIntoView({block: "center", inline: "nearest"}); } catch (e) {}
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    try { el.click(); return true; } catch (e) {}
    return false;
  };
  const el = document.getElementById(id);
  return clickEl(el);
}
"""

JS_CLICK_NUMERO = r"""
(n) => {
  const clickEl = (el) => {
    if (!el) return false;
    try { el.scrollIntoView({block: "center", inline: "nearest"}); } catch (e) {}
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    try { el.click(); return true; } catch (e) {}
    return false;
  };
  const pad = String(n).padStart(2, "0");
  const ids = ["n" + pad, "n" + String(n), pad, String(n)];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el) return clickEl(el) ? id : false;
  }
  const textos = new Set([pad, String(n), String(n).padStart(2, "0")]);
  const candidatos = document.querySelectorAll("a, button, span, li, div, label");
  for (const el of candidatos) {
    const t = (el.textContent || "").trim();
    if (textos.has(t) && el.offsetParent !== null) {
      const id = el.id || t;
      if (clickEl(el)) return id;
    }
  }
  return false;
}
"""

JS_CLICK_NUMERO_COLUNA = r"""
({col, n}) => {
  const clickEl = (el) => {
    if (!el) return false;
    try { el.scrollIntoView({block: "center"}); } catch (e) {}
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    el.click();
    return true;
  };
  const pad = String(n).padStart(2, "0");
  const ids = [
    "n" + n + "c" + col,
    "n" + pad + "c" + col,
    "c" + col + "n" + n,
  ];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el && clickEl(el)) return id;
  }
  const colunas = document.querySelectorAll(
    ".coluna, [id^='coluna'], [class*='coluna'], [class*='coluna-super']"
  );
  if (colunas[col - 1]) {
    const raiz = colunas[col - 1];
    for (const id of ["n" + pad, "n" + String(n)]) {
      const el = raiz.querySelector("#" + id) || document.getElementById(id);
      if (el && raiz.contains(el) && clickEl(el)) return id;
    }
    const alvos = raiz.querySelectorAll("a, button, span, li, div");
    for (const el of alvos) {
      if ((el.textContent || "").trim() === String(n) && clickEl(el)) return "col-text";
    }
  }
  const el = document.getElementById("n" + pad) || document.getElementById("n" + n);
  if (el && clickEl(el)) return el.id;
  return false;
}
"""

JS_CLICK_MENU = r"""
(menuId) => {
  const clickEl = (el) => {
    if (!el) return false;
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    el.click();
    return true;
  };
  const direto = document.getElementById(menuId)
    || document.querySelector("#menuPrincipal a#" + menuId);
  if (direto && clickEl(direto)) return "id";
  const links = document.querySelectorAll("#menuPrincipal a, a[id], button");
  const alvo = menuId.replace(/-/g, " ").toLowerCase();
  for (const el of links) {
    const txt = (el.textContent || "").trim().toLowerCase();
    const id = (el.id || "").toLowerCase();
    if (id === menuId.toLowerCase() || txt === alvo || txt.includes(alvo)) {
      if (clickEl(el)) return "texto";
    }
  }
  return false;
}
"""

JS_DISMISS_DIALOGS = r"""
() => {
  const clickEl = (el) => {
    if (!el) return false;
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    el.click();
    return true;
  };
  const confirm = document.querySelector("#confirm-cancel .modal-footer button, #confirm-cancel .modal-footer a, #confirm-cancel .modal-footer :first-child");
  if (confirm && confirm.offsetParent !== null) {
    clickEl(confirm);
    return "confirm";
  }
  const botoes = Array.from(document.querySelectorAll("button, a, input[type='button']"));
  const padroes = [/tenho mais de 18/i, /^sim$/i, /aposte já/i, /aceito/i, /continuar/i, /fechar/i];
  for (const el of botoes) {
    const t = (el.innerText || el.value || "").trim();
    if (padroes.some((p) => p.test(t)) && el.offsetParent !== null) {
      clickEl(el);
      return t;
    }
  }
  return false;
}
"""

JS_GAME_LENGTH = r"""
() => {
  const el = document.querySelector(".input-mais-menos span");
  if (!el) return null;
  const n = parseInt((el.innerText || "").replace(/\D/g, ""), 10);
  return Number.isNaN(n) ? null : n;
}
"""

JS_LOGADO = r"""
() => {
  const txt = (document.body && document.body.innerText) || "";
  if (/sair|meus pedidos|carrinho/i.test(txt) && !/identifique-se/i.test(txt)) {
    return true;
  }
  const user = document.querySelector(".nome-usuario, .usuario-logado, [class*='logado']");
  return Boolean(user);
}
"""


@dataclass
class ResultadoJogo:
    identificador: str
    ok: bool
    detalhe: str


@dataclass
class Relatorio:
    ok: list[ResultadoJogo] = field(default_factory=list)
    falhas: list[ResultadoJogo] = field(default_factory=list)

    def registrar(self, identificador: str, ok: bool, detalhe: str) -> None:
        item = ResultadoJogo(identificador, ok, detalhe)
        (self.ok if ok else self.falhas).append(item)


class CaixaBrowser:
    def __init__(
        self,
        cookies: list[dict[str, Any]],
        modalidade: Modalidade,
        *,
        headless: bool = False,
        delay: float = 0.7,
        teimosinha: int = 0,
        screenshots: Path | None = None,
        log: Callable[[str], None] | None = None,
        manter_aberto: bool = True,
        timeout_ms: int = 25_000,
    ) -> None:
        self.cookies = cookies
        self.modalidade = modalidade
        self.headless = headless
        self.delay = delay
        self.teimosinha = teimosinha
        self.screenshots = screenshots
        self.log = log or (lambda _msg: None)
        self.manter_aberto = manter_aberto
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None

    def __enter__(self) -> "CaixaBrowser":
        self.abrir()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.fechar()

    def abrir(self) -> None:
        from playwright.sync_api import sync_playwright

        self.log("Abrindo o navegador…")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = self._browser.new_context(
            locale="pt-BR",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        if self.cookies:
            self._context.add_cookies(self.cookies)
            self.log(f"{len(self.cookies)} cookie(s) aplicados.")
        self.page = self._context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        self.page.goto(URL_HOME, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        self._dispensar_dialogs()

    def fechar(self) -> None:
        if self.manter_aberto and not self.headless and self._browser:
            self.log("Navegador permanece aberto para você conferir o carrinho e pagar.")
            return
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        finally:
            if self._playwright:
                self._playwright.stop()
            self._playwright = None
            self._browser = None
            self._context = None
            self.page = None

    def aguardar_login_manual(self, input_fn: Callable[[str], str] | None = None) -> None:
        if self.parece_logado():
            self.log("Sessão autenticada detectada.")
            return
        self.log(
            "Sessão não detectada. Faça login na janela do navegador "
            "(ou cole um cookie válido) e pressione Enter para continuar."
        )
        if self.headless:
            raise RuntimeError(
                "Não há sessão logada e o modo --headless não permite login manual. "
                "Passe --cookie / --cookie-arquivo ou rode sem --headless."
            )
        perguntar = input_fn or input
        perguntar("Pressione Enter depois de entrar na sua conta… ")
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_timeout(1200)
        self._dispensar_dialogs()

    def parece_logado(self) -> bool:
        try:
            return bool(self.page.evaluate(JS_LOGADO))
        except Exception:
            return False

    def abrir_modalidade(self) -> None:
        url = URL_HOME + self.modalidade.hash_path
        self.log(f"Abrindo {self.modalidade.nome}: {url}")
        clicou = False
        try:
            clicou = bool(self.page.evaluate(JS_CLICK_MENU, self.modalidade.menu_id))
        except Exception as exc:
            self.log(f"Menu não clicável ({exc}); navegando direto pelo endereço.")
        if not clicou:
            self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1800)
        self._dispensar_dialogs()
        self._esperar_volante()

    def preencher_jogos(self, jogos: list[Jogo]) -> Relatorio:
        relatorio = Relatorio()
        total = len(jogos)
        for i, jogo in enumerate(jogos, start=1):
            self.log(f"[{i}/{total}] {jogo.identificador} → {jogo.dezenas_formatadas(self.modalidade.largura_digitos)}")
            try:
                self._preencher_um(jogo)
                relatorio.registrar(jogo.identificador, True, "adicionado ao carrinho")
            except Exception as exc:
                detalhe = str(exc)
                self.log(f"  falhou: {detalhe}")
                self._screenshot(f"erro-{jogo.identificador}")
                relatorio.registrar(jogo.identificador, False, detalhe)
            time.sleep(self.delay)
        return relatorio

    def _preencher_um(self, jogo: Jogo) -> None:
        self._click_id("limparvolante", obrigatorio=False)
        self.page.wait_for_timeout(200)

        if jogo.extras.get("espelho"):
            self._click_id("apostaEspelho", obrigatorio=False)

        if self.modalidade.extra == "loteca":
            self._marcar_loteca(jogo.extras.get("loteca") or [])
        elif self.modalidade.extra == "colunas":
            self._ajustar_tamanho(len(jogo.dezenas))
            for col, n in enumerate(jogo.dezenas, start=1):
                ok = self.page.evaluate(JS_CLICK_NUMERO_COLUNA, {"col": col, "n": n})
                if not ok:
                    raise RuntimeError(f"não achei o dígito {n} na coluna {col}")
        else:
            self._ajustar_tamanho(len(jogo.dezenas))
            for n in jogo.dezenas:
                ok = self.page.evaluate(JS_CLICK_NUMERO, n)
                if not ok:
                    raise RuntimeError(f"não achei a dezena {n:02d} no volante")

        if self.teimosinha:
            for _ in range(self.teimosinha):
                self._click_id("aumentarteimosinha", obrigatorio=False)
                self.page.wait_for_timeout(80)

        if self.modalidade.extra == "mes":
            self._marcar_mes(int(jogo.extras["mes"]))
        if self.modalidade.extra == "time":
            self._marcar_time(int(jogo.extras["time"]))
        if self.modalidade.extra == "trevos":
            self._marcar_trevos(list(jogo.extras["trevos"]))

        self._click_id("colocarnocarrinho", obrigatorio=True)
        self.page.wait_for_timeout(500)
        self._dispensar_dialogs()

    def _ajustar_tamanho(self, desejado: int) -> None:
        atual = self.page.evaluate(JS_GAME_LENGTH)
        if atual is None:
            extra = max(0, desejado - self.modalidade.min_dezenas)
            for _ in range(extra):
                self._click_id("aumentarnumero", obrigatorio=False)
                self.page.wait_for_timeout(60)
            return
        guard = 0
        while atual < desejado and guard < 20:
            self._click_id("aumentarnumero", obrigatorio=True)
            self.page.wait_for_timeout(60)
            atual = self.page.evaluate(JS_GAME_LENGTH) or atual + 1
            guard += 1
        while atual > desejado and guard < 40:
            self._click_id("diminuirnumero", obrigatorio=False)
            self.page.wait_for_timeout(60)
            atual = self.page.evaluate(JS_GAME_LENGTH) or atual - 1
            guard += 1

    def _marcar_mes(self, mes: int) -> None:
        ok = self.page.evaluate(
            """(mes) => {
              const raiz = document.getElementById("carrossel_diadesorte");
              if (!raiz || !raiz.children[0] || !raiz.children[0].children[mes - 1]) return false;
              const el = raiz.children[0].children[mes - 1];
              if (window.angular) { try { angular.element(el).click(); } catch (e) {} }
              el.click();
              return true;
            }""",
            mes,
        )
        if not ok:
            raise RuntimeError(f"não achei o mês {mes} no carrossel do Dia de Sorte")

    def _marcar_time(self, time_n: int) -> None:
        ok = self.page.evaluate(
            """(n) => {
              const raiz = document.getElementById("carrossel_timemania");
              if (!raiz || !raiz.children[0] || !raiz.children[0].children[n - 1]) return false;
              const el = raiz.children[0].children[n - 1];
              const alvo = el.querySelector("a, button") || el;
              if (window.angular) { try { angular.element(alvo).click(); } catch (e) {} }
              alvo.click();
              return true;
            }""",
            time_n,
        )
        if not ok:
            raise RuntimeError(f"não achei o time {time_n} no carrossel da Timemania")

    def _marcar_trevos(self, trevos: list[int]) -> None:
        extra = max(0, len(trevos) - 2)
        for _ in range(extra):
            try:
                self.page.evaluate(
                    """() => {
                      const step = document.getElementById("step6");
                      if (!step) return false;
                      const btn = step.querySelector("button, a, [ng-click]");
                      if (!btn) return false;
                      if (window.angular) { try { angular.element(btn).click(); } catch (e) {} }
                      btn.click();
                      return true;
                    }"""
                )
            except Exception:
                pass
        for t in trevos:
            self._click_id(f"trevo{t}", obrigatorio=True)

    def _marcar_loteca(self, palpites: list[str]) -> None:
        self.page.evaluate(
            """(palpites) => {
              const links = document.querySelectorAll("a.loteca_palpite");
              for (let i = 0; i < palpites.length; i++) {
                const marca = palpites[i];
                for (let c = 0; c < 3; c++) {
                  if (marca[c] === "X") {
                    const el = links[(i * 3) + c];
                    if (!el) continue;
                    if (window.angular) { try { angular.element(el).click(); } catch (e) {} }
                    el.click();
                  }
                }
              }
            }""",
            palpites,
        )

    def _click_id(self, element_id: str, *, obrigatorio: bool) -> None:
        ok = False
        try:
            ok = bool(self.page.evaluate(JS_CLICK_EL, element_id))
        except Exception:
            ok = False
        if not ok and obrigatorio:
            raise RuntimeError(f"elemento #{element_id} não encontrado na página")

    def _dispensar_dialogs(self) -> None:
        try:
            self.page.evaluate(JS_DISMISS_DIALOGS)
        except Exception:
            pass

    def _esperar_volante(self) -> None:
        try:
            self.page.wait_for_function(
                """() => Boolean(
                    document.getElementById("colocarnocarrinho") ||
                    document.getElementById("n01") ||
                    document.getElementById("n1") ||
                    document.querySelector("a.loteca_palpite")
                )""",
                timeout=self.timeout_ms,
            )
        except Exception:
            self._screenshot("volante-nao-encontrado")
            raise RuntimeError(
                "Não encontrei o volante. Confira se a modalidade está disponível "
                "e se a sessão ainda está válida."
            )

    def _screenshot(self, nome: str) -> None:
        if not self.screenshots or not self.page:
            return
        self.screenshots.mkdir(parents=True, exist_ok=True)
        seguro = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nome)[:80]
        caminho = self.screenshots / f"{seguro}.png"
        try:
            self.page.screenshot(path=str(caminho), full_page=True)
            self.log(f"  captura salva em {caminho}")
        except Exception:
            pass
