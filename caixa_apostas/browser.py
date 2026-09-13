"""Automação do volante no Loterias Online da Caixa (Playwright)."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from caixa_apostas.csv_parser import Jogo
from caixa_apostas.modalidades import Modalidade, especial_de

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

JS_ESPECIAL_LISTADO = r"""
({menuId, hashPath, nome}) => {
  const visivel = (el) => Boolean(el && el.offsetParent !== null);
  const direto = document.getElementById(menuId);
  if (visivel(direto)) return true;
  const alvoHash = String(hashPath || "").toLowerCase();
  const alvoNome = String(nome || "").toLowerCase();
  const els = document.querySelectorAll("#menuPrincipal a, a[id], a[href], button");
  for (const el of els) {
    if (!visivel(el)) continue;
    const id = (el.id || "").toLowerCase();
    const href = (el.getAttribute("href") || "").toLowerCase();
    const txt = (el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (id === String(menuId).toLowerCase()) return true;
    if (alvoHash && href.includes(alvoHash)) return true;
    if (alvoNome && txt && (txt === alvoNome || txt.includes(alvoNome))) return true;
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
  const visivel = (el) => {
    if (!el) return false;
    const st = window.getComputedStyle(el);
    if (st.display === "none" || st.visibility === "hidden") return false;
    return el.getClientRects().length > 0;
  };
  if (visivel(document.getElementById("salvarcarrinhofavorito"))) return true;
  const sairEl =
    document.getElementById("sair") ||
    document.querySelector("a[href*='sair'], a[ng-click*='sair'], a[href*='logout']");
  if (visivel(sairEl)) return true;
  const textos = Array.from(document.querySelectorAll("a, button")).map((el) => ({
    t: ((el.innerText || el.textContent || "") + "").replace(/\s+/g, " ").trim(),
    visivel: visivel(el),
  }));
  const tem = (re) => textos.some((x) => x.visivel && re.test(x.t));
  if (tem(/^sair\b/i) || tem(/meus pedidos/i)) return true;
  const user = document.querySelector(
    ".nome-usuario, .usuario-logado, [class*='usuario-logado']"
  );
  if (visivel(user) && (user.textContent || "").trim()) return true;
  if (tem(/^identifique-se$/i) || tem(/^acessar$/i) || tem(/^entrar$/i)) {
    return false;
  }
  return false;
}
"""

JS_CLICK_TEXTO = r"""
({ids, padroes, maxLen}) => {
  const clickEl = (el) => {
    if (!el) return false;
    try { el.scrollIntoView({block: "center", inline: "nearest"}); } catch (e) {}
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    try { el.click(); return true; } catch (e) {}
    return false;
  };
  for (const id of ids || []) {
    const el = document.getElementById(id);
    if (el && clickEl(el)) return id;
  }
  const re = (padroes || []).map((p) => new RegExp(p, "i"));
  const limite = maxLen || 80;
  const els = document.querySelectorAll("a, button, input[type='button'], [ng-click], span");
  for (const el of els) {
    if (el.offsetParent === null) continue;
    const t = ((el.innerText || el.value || el.getAttribute("title") || "") + "")
      .replace(/\s+/g, " ").trim();
    if (!t || t.length > limite) continue;
    if (re.some((r) => r.test(t)) && clickEl(el)) return t;
  }
  return false;
}
"""

JS_PREENCHER_NOME_FAVORITO = r"""
(nome) => {
  const visivel = (el) => Boolean(el && el.offsetParent !== null);
  const setValue = (el, value) => {
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    if (window.angular) {
      try {
        const ae = angular.element(el);
        ae.val(value);
        ae.triggerHandler("input");
        ae.triggerHandler("change");
      } catch (e) {}
    }
  };
  const raiz =
    document.querySelector(".modal.in, .modal.show, .modal[style*='display: block']") ||
    document.querySelector(".modal-dialog") ||
    document;
  const inputs = raiz.querySelectorAll(
    "input[type='text'], input:not([type]), input[type='search'], textarea"
  );
  for (const el of inputs) {
    if (!visivel(el) || el.disabled) continue;
    setValue(el, nome);
    return el.id || el.name || "input";
  }
  return false;
}
"""

JS_DISMISS_COOKIES = r"""
() => {
  const clickEl = (el) => {
    if (!el) return false;
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    el.click();
    return true;
  };
  const ids = ["onetrust-accept-btn-handler", "acceptAllButton", "onetrust-accept-btn"];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el && el.offsetParent !== null && clickEl(el)) return id;
  }
  const botoes = document.querySelectorAll("button, a");
  for (const el of botoes) {
    if (el.offsetParent === null) continue;
    const t = ((el.innerText || el.value || "") + "").replace(/\s+/g, " ").trim();
    if (/^aceitar$/i.test(t) && clickEl(el)) return t;
  }
  return false;
}
"""

JS_CARRINHO_TEM_APOSTA = r"""
() => {
  const txt = ((document.body && document.body.innerText) || "").replace(/\s+/g, " ");
  if (/n[aã]o\s+(fez\s+)?nenhuma\s+aposta|carrinho\s+(est[aá]\s+)?vazio/i.test(txt)) {
    return false;
  }
  const badge = document.querySelector(
    "#carrinho .badge, .carrinho-qtd, [class*='qtd-carrinho'], [class*='contador-carrinho'], a[href*='carrinho'] .badge"
  );
  if (badge) {
    const n = parseInt((badge.innerText || "").replace(/\D/g, ""), 10);
    if (!Number.isNaN(n)) return n > 0;
  }
  const itens = document.querySelectorAll(
    "[ng-repeat*='carrinho'], [ng-repeat*='aposta'], .item-carrinho, [id^='aposta'], [class*='item-carrinho']"
  );
  if (itens.length > 0) return true;
  const acoes = Array.from(document.querySelectorAll("a, button, [ng-click]"));
  for (const el of acoes) {
    if (el.offsetParent === null) continue;
    const t = ((el.innerText || "") + "").replace(/\s+/g, " ").trim();
    if (/excluir/i.test(t) || /salvar\s+carrinho\s+como\s+favorito/i.test(t)) {
      return true;
    }
  }
  return false;
}
"""

JS_CLICK_SALVAR_MODAL = r"""
() => {
  const clickEl = (el) => {
    if (!el) return false;
    if (window.angular) {
      try { angular.element(el).click(); return true; } catch (e) {}
    }
    try { el.click(); return true; } catch (e) {}
    return false;
  };
  const visivel = (el) => Boolean(el && el.offsetParent !== null);
  const raizes = document.querySelectorAll(
    ".modal.in, .modal.show, .modal[style*='display: block'], .modal-dialog"
  );
  const lista = raizes.length ? raizes : [document];
  for (const raiz of lista) {
    const botoes = raiz.querySelectorAll("button, a, input[type='button'], [ng-click]");
    for (const el of botoes) {
      if (!visivel(el)) continue;
      const t = ((el.innerText || el.value || "") + "").replace(/\s+/g, " ").trim();
      if (/^salvar$/i.test(t) && clickEl(el)) return t;
    }
  }
  return false;
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
            self.log(
                "Navegador permanece aberto para você conferir o carrinho e pagar.")
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
        if self._esperar_logado(tentativas=6, intervalo_ms=700):
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
        if input_fn is None and not sys.stdin.isatty():
            self.log("Sem terminal para confirmar; aguardando login na janela…")
            if self._esperar_logado(tentativas=40, intervalo_ms=1000):
                return
            self.log("Login não confirmado; seguindo com os cookies aplicados.")
            return
        perguntar = input_fn or input
        perguntar("Pressione Enter depois de entrar na sua conta… ")
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_timeout(1200)
        self._dispensar_dialogs()

    def aguardar_login_para_salvar(
        self,
        *,
        forcar: bool = False,
        input_fn: Callable[[str], str] | None = None,
    ) -> None:
        if self.parece_logado() and not forcar:
            return
        self.log(
            "Faça login na janela do navegador para salvar o carrinho como favorito."
        )
        if self.headless:
            raise RuntimeError(
                "Não há sessão logada e o modo --headless não permite login "
                "para salvar o carrinho. Rode sem --headless."
            )
        perguntar = input_fn or input
        while True:
            if input_fn is None and not sys.stdin.isatty():
                self.log("Aguardando login na janela…")
                if self._esperar_logado(tentativas=300, intervalo_ms=1000):
                    return
                raise RuntimeError(
                    "Login não confirmado; não foi possível salvar o carrinho."
                )
            perguntar("Pressione Enter depois de entrar na sua conta… ")
            self.page.wait_for_timeout(800)
            self._dispensar_dialogs()
            self._dispensar_cookies()
            if self.parece_logado() or self._tem_botao_salvar_favorito():
                self.log("Sessão autenticada detectada.")
                return
            self.log(
                "Ainda não detectei o login. Entre na conta e pressione Enter de novo."
            )

    def _esperar_logado(self, *, tentativas: int, intervalo_ms: int) -> bool:
        for _ in range(tentativas):
            if self.parece_logado():
                self.log("Sessão autenticada detectada.")
                return True
            self.page.wait_for_timeout(intervalo_ms)
            self._dispensar_dialogs()
        return False

    def parece_logado(self) -> bool:
        try:
            return bool(self.page.evaluate(JS_LOGADO))
        except Exception:
            return False

    def abrir_modalidade(self) -> None:
        original = self.modalidade
        especial = especial_de(original)
        if especial and self._especial_listado(especial):
            self.log(
                f"Concurso especial listado na tela: {especial.nome}. "
                f"Abrindo {especial.hash_path} em vez de {original.hash_path}."
            )
            candidatos = (especial, original)
        elif especial:
            candidatos = (original, especial)
        else:
            candidatos = (original,)

        for i, candidata in enumerate(candidatos):
            self.modalidade = candidata
            self._navegar_modalidade(candidata)
            espera = (
                self.timeout_ms
                if i == len(candidatos) - 1
                else min(8_000, self.timeout_ms)
            )
            if self._tem_volante(timeout_ms=espera):
                return
            if i < len(candidatos) - 1:
                proxima = candidatos[i + 1]
                self.log(
                    f"Volante de {candidata.nome} não apareceu; "
                    f"tentando {proxima.nome} em {proxima.hash_path}."
                )

        self._screenshot("volante-nao-encontrado")
        raise RuntimeError(
            "Não encontrei o volante. Confira se a modalidade está disponível "
            "e se a sessão ainda está válida."
        )

    def _navegar_modalidade(self, modalidade: Modalidade) -> None:
        url = URL_HOME + modalidade.hash_path
        self.log(f"Abrindo {modalidade.nome}: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1800)
        self._dispensar_dialogs()
        clicou = False
        try:
            clicou = bool(self.page.evaluate(
                JS_CLICK_MENU, modalidade.menu_id))
        except Exception as exc:
            self.log(
                f"Menu não clicável ({exc}); endereço direto já foi aberto.")
        if clicou:
            self.page.wait_for_timeout(800)
            self._dispensar_dialogs()

    def salvar_carrinho_favorito(self, nome: str) -> None:
        nome = (nome or "").strip()
        if not nome:
            raise RuntimeError("informe um nome para o carrinho favorito")
        self.log(f"Salvando carrinho como favorito '{nome}'.")
        self._abrir_carrinho()
        if not self._esperar_carrinho_com_aposta():
            self._screenshot("carrinho-vazio")
            raise RuntimeError(
                "O carrinho está vazio. Inclua pelo menos uma aposta "
                "antes de salvar como favorito."
            )

        if not self._clicar_salvar_carrinho_favorito():
            self.aguardar_login_para_salvar()
            self._abrir_carrinho()
            for tentativa in range(1, 6):
                if not self._esperar_carrinho_com_aposta():
                    self._screenshot("carrinho-vazio")
                    raise RuntimeError(
                        "O carrinho está vazio. Inclua pelo menos uma aposta "
                        "antes de salvar como favorito."
                    )
                if self._clicar_salvar_carrinho_favorito():
                    break
                self._screenshot("carrinho-salvar-favorito")
                self.log(
                    "Não achei o botão #salvarcarrinhofavorito. "
                    "Faça login na janela e pressione Enter para tentar de novo "
                    f"({tentativa}/5)."
                )
                self.aguardar_login_para_salvar(forcar=True)
                self._abrir_carrinho()
            else:
                raise RuntimeError(
                    "Não achei o botão #salvarcarrinhofavorito. "
                    "Confira se a sessão está logada."
                )

        self.page.wait_for_timeout(800)
        campo = self.page.evaluate(JS_PREENCHER_NOME_FAVORITO, nome)
        if not campo:
            self._screenshot("modal-favorito-nome")
            raise RuntimeError(
                "Não achei o campo de nome no modal de favorito.")

        self.page.wait_for_timeout(300)
        salvou = bool(self.page.evaluate(JS_CLICK_SALVAR_MODAL))
        if not salvou:
            self._screenshot("modal-favorito-salvar")
            raise RuntimeError(
                "Não achei o botão Salvar no modal de favorito.")

        self.page.wait_for_timeout(1500)
        self.log(f"Carrinho salvo como favorito: {nome}")

    def _abrir_carrinho(self) -> None:
        url = URL_HOME + "carrinho"
        self.log(f"Abrindo carrinho: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        self._dispensar_cookies()

    def preencher_jogos(self, jogos: list[Jogo]) -> Relatorio:
        relatorio = Relatorio()
        total = len(jogos)
        for i, jogo in enumerate(jogos, start=1):
            self.log(
                f"[{i}/{total}] {jogo.identificador} → {jogo.dezenas_formatadas(self.modalidade.largura_digitos)}")
            try:
                self._preencher_um(jogo)
                relatorio.registrar(jogo.identificador, True,
                                    "adicionado ao carrinho")
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
                ok = self.page.evaluate(
                    JS_CLICK_NUMERO_COLUNA, {"col": col, "n": n})
                if not ok:
                    raise RuntimeError(
                        f"não achei o dígito {n} na coluna {col}")
        else:
            self._ajustar_tamanho(len(jogo.dezenas))
            for n in jogo.dezenas:
                ok = self.page.evaluate(JS_CLICK_NUMERO, n)
                if not ok:
                    raise RuntimeError(
                        f"não achei a dezena {n:02d} no volante")

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
            raise RuntimeError(
                f"não achei o mês {mes} no carrossel do Dia de Sorte")

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
            raise RuntimeError(
                f"não achei o time {time_n} no carrossel da Timemania")

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
            raise RuntimeError(
                f"elemento #{element_id} não encontrado na página")

    def _dispensar_dialogs(self) -> None:
        try:
            self.page.evaluate(JS_DISMISS_DIALOGS)
        except Exception:
            pass
        self._dispensar_cookies()

    def _dispensar_cookies(self) -> None:
        try:
            self.page.evaluate(JS_DISMISS_COOKIES)
        except Exception:
            pass

    def _carrinho_tem_aposta(self) -> bool:
        try:
            return bool(self.page.evaluate(JS_CARRINHO_TEM_APOSTA))
        except Exception:
            return False

    def _esperar_carrinho_com_aposta(self, tentativas: int = 8) -> bool:
        for _ in range(tentativas):
            self._dispensar_cookies()
            if self._carrinho_tem_aposta():
                return True
            self.page.wait_for_timeout(400)
        return False

    def _tem_botao_salvar_favorito(self) -> bool:
        try:
            loc = self.page.locator("#salvarcarrinhofavorito")
            return loc.count() > 0 and loc.first.is_visible()
        except Exception:
            return False

    def _clicar_salvar_carrinho_favorito(self) -> bool:
        try:
            loc = self.page.locator("#salvarcarrinhofavorito")
            loc.first.wait_for(state="visible", timeout=2500)
            loc.first.scroll_into_view_if_needed()
            loc.first.click()
            return True
        except Exception:
            pass
        try:
            return bool(self.page.evaluate(JS_CLICK_EL, "salvarcarrinhofavorito"))
        except Exception:
            return False

    def _especial_listado(self, especial: Modalidade) -> bool:
        try:
            return bool(
                self.page.evaluate(
                    JS_ESPECIAL_LISTADO,
                    {
                        "menuId": especial.menu_id,
                        "hashPath": especial.hash_path,
                        "nome": especial.nome,
                    },
                )
            )
        except Exception:
            return False

    def _tem_volante(self, timeout_ms: int | None = None) -> bool:
        try:
            self.page.wait_for_function(
                """() => Boolean(
                    document.getElementById("colocarnocarrinho") ||
                    document.getElementById("n01") ||
                    document.getElementById("n1") ||
                    document.querySelector("a.loteca_palpite")
                )""",
                timeout=timeout_ms or self.timeout_ms,
            )
            return True
        except Exception:
            return False

    def _esperar_volante(self) -> None:
        if self._tem_volante():
            return
        self._screenshot("volante-nao-encontrado")
        raise RuntimeError(
            "Não encontrei o volante. Confira se a modalidade está disponível "
            "e se a sessão ainda está válida."
        )

    def _screenshot(self, nome: str) -> None:
        if not self.screenshots or not self.page:
            return
        self.screenshots.mkdir(parents=True, exist_ok=True)
        seguro = "".join(ch if ch.isalnum()
                         or ch in "-_" else "_" for ch in nome)[:80]
        caminho = self.screenshots / f"{seguro}.png"
        try:
            self.page.screenshot(path=str(caminho), full_page=True)
            self.log(f"  captura salva em {caminho}")
        except Exception:
            pass
