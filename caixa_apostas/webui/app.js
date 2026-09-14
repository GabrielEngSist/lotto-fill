const MESES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const estado = {
  modalidades: [],
  modalidade: null,
  selecionados: new Set(),
  trevos: new Set(),
  jogos: [],
  selecionadoLista: null,
};

const $ = (id) => document.getElementById(id);

function log(msg) {
  const el = $("log");
  el.textContent = el.textContent ? `${el.textContent}\n${msg}` : msg;
  el.scrollTop = el.scrollHeight;
}

function pad(n, largura) {
  return String(n).padStart(largura, "0");
}

async function carregar() {
  const res = await fetch("/api/modalidades");
  estado.modalidades = await res.json();
  const nav = $("concursos");
  nav.innerHTML = "";
  for (const m of estado.modalidades) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill";
    btn.textContent = m.nome;
    btn.dataset.chave = m.chave;
    btn.dataset.cor = m.cor;
    btn.style.borderColor = m.cor;
    btn.style.color = m.cor;
    btn.style.background = "#fff";
    btn.setAttribute(
      "data-tip",
      `${m.nome}: ${m.descricao_faixa}. Clique para escolher. Trocar de concurso esvazia o carrinho.`,
    );
    btn.addEventListener("click", () => escolher(m.chave));
    nav.appendChild(btn);
  }
  escolher("lotofacil");
}

function escolher(chave) {
  const m = estado.modalidades.find((x) => x.chave === chave);
  if (!m) return;
  if (estado.jogos.length && estado.modalidade && estado.modalidade.chave !== chave) {
    if (!confirm("O carrinho desta modalidade será esvaziado. Continuar?")) return;
    estado.jogos = [];
  }
  estado.modalidade = m;
  estado.selecionados.clear();
  estado.trevos.clear();
  $("titulo-modalidade").textContent = m.nome;
  $("titulo-modalidade").style.color = m.cor;
  $("faixa-modalidade").textContent = m.descricao_faixa + (m.pode_gerar ? "" : ". Importe uma planilha; este concurso não gera Surpresinha.");
  $("dez-volante").min = m.min_dezenas;
  $("dez-volante").max = m.max_dezenas;
  $("dez-volante").value = m.min_dezenas;
  $("dez-lote").min = m.min_dezenas;
  $("dez-lote").max = m.max_dezenas;
  $("dez-lote").value = m.min_dezenas;
  if (!$("nome-carrinho").value || $("nome-carrinho").value === "Meu carrinho" ||
      estado.modalidades.some((x) => x.nome === $("nome-carrinho").value)) {
    $("nome-carrinho").value = m.nome;
  }
  for (const btn of document.querySelectorAll(".pill")) {
    const cor = btn.dataset.cor;
    const ativa = btn.dataset.chave === m.chave;
    btn.classList.toggle("ativa", ativa);
    btn.style.borderColor = cor;
    btn.style.background = ativa ? cor : "#fff";
    btn.style.color = ativa ? "#fff" : cor;
  }
  desenharExtras();
  desenharBolas();
  atualizarStatus();
  atualizarCarrinho();
}

function desenharExtras() {
  const box = $("extras");
  box.innerHTML = "";
  const extra = estado.modalidade.extra;
  if (extra === "mes") {
    box.innerHTML = `<label class="rotulo">Mês da sorte
        <span class="tip" tabindex="0" data-tip="Obrigatório no Dia de Sorte, além das 7 dezenas. Escolha o mês que vai no volante.">?</span></label>
      <select id="mes">${MESES.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("")}</select>
      <p class="ajuda">Obrigatório no Dia de Sorte, além das dezenas.</p>`;
  } else if (extra === "time") {
    box.innerHTML = `<label class="rotulo">Time do coração (1 a 80)
        <span class="tip" tabindex="0" data-tip="Número do time na tabela oficial da Timemania, de 1 a 80. Vai junto com as 10 dezenas.">?</span></label>
      <input id="time" type="number" min="1" max="80" value="1" data-tip="Use o código do time (1 a 80), não o nome.">`;
  } else if (extra === "trevos") {
    box.innerHTML = `<p class="rotulo">Trevos (escolha 2)
      <span class="tip" tabindex="0" data-tip="A +Milionária pede 2 trevos de 1 a 6, além das 6 dezenas. Clique em dois números.">?</span></p>
      <div id="trevos" class="bolas"></div>`;
    const t = $("trevos");
    for (let n = 1; n <= 6; n += 1) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bola";
      b.textContent = String(n);
      b.addEventListener("click", () => {
        if (estado.trevos.has(n)) estado.trevos.delete(n);
        else if (estado.trevos.size < 2) estado.trevos.add(n);
        pintarTrevos();
      });
      t.appendChild(b);
    }
  }
}

function pintarTrevos() {
  const cor = estado.modalidade.cor;
  $("trevos")?.querySelectorAll(".bola").forEach((b, i) => {
    const n = i + 1;
    b.classList.toggle("marcada", estado.trevos.has(n));
    b.style.background = estado.trevos.has(n) ? cor : "";
  });
}

function desenharBolas() {
  const box = $("bolas");
  box.innerHTML = "";
  const m = estado.modalidade;
  if (m.extra === "colunas" || m.extra === "loteca") {
    box.innerHTML = `<p class="ajuda">Neste concurso não há volante de bolinhas. Importe uma planilha CSV ou use Mais jogos, se a Surpresinha estiver disponível.
      <span class="tip" tabindex="0" data-tip="Super Sete usa colunas de dígitos e Loteca usa 1, X ou 2. O jeito mais simples é importar um CSV no formato do programa.">?</span></p>`;
    return;
  }
  for (let n = m.dezena_min; n <= m.dezena_max; n += 1) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "bola";
    b.textContent = pad(n, m.largura_digitos);
    b.addEventListener("click", () => toggle(n));
    box.appendChild(b);
  }
  pintarBolas();
}

function toggle(n) {
  const m = estado.modalidade;
  if (estado.selecionados.has(n)) estado.selecionados.delete(n);
  else if (estado.selecionados.size >= m.max_dezenas) {
    alert(`${m.nome} aceita no máximo ${m.max_dezenas} dezenas.`);
    return;
  } else estado.selecionados.add(n);
  pintarBolas();
  atualizarStatus();
}

function pintarBolas() {
  const cor = estado.modalidade.cor;
  const min = estado.modalidade.dezena_min;
  $("bolas").querySelectorAll(".bola").forEach((b, i) => {
    const n = min + i;
    const on = estado.selecionados.has(n);
    b.classList.toggle("marcada", on);
    b.style.background = on ? cor : "";
  });
}

function atualizarStatus() {
  const m = estado.modalidade;
  const alvo = Number($("dez-volante").value) || m.min_dezenas;
  const marcas = [...estado.selecionados].sort((a, b) => a - b).map((n) => pad(n, m.largura_digitos)).join("  ") || "nenhuma ainda";
  $("status-volante").textContent =
    `Você marcou ${estado.selecionados.size} de ${alvo} (pode de ${m.min_dezenas} a ${m.max_dezenas}):  ${marcas}`;
}

function extrasAtuais() {
  const extra = estado.modalidade.extra;
  if (extra === "mes") return { mes: Number($("mes").value) };
  if (extra === "time") return { time: Number($("time").value) };
  if (extra === "trevos") {
    if (estado.trevos.size !== 2) throw new Error("Escolha 2 trevos para a +Milionária.");
    return { trevos: [...estado.trevos].sort((a, b) => a - b) };
  }
  return {};
}

function limparVolante() {
  estado.selecionados.clear();
  $("digitados").value = "";
  pintarBolas();
  atualizarStatus();
}

function marcarDigitados() {
  const partes = $("digitados").value.replace(/[,;]/g, " ").trim().split(/\s+/).filter(Boolean);
  const nums = partes.map((p) => Number(p));
  if (nums.some((n) => Number.isNaN(n))) {
    alert("Use só números, separados por espaço. Ex.: 01 05 12");
    return;
  }
  estado.selecionados.clear();
  const m = estado.modalidade;
  for (const n of nums) {
    if (n >= m.dezena_min && n <= m.dezena_max && estado.selecionados.size < m.max_dezenas) {
      estado.selecionados.add(n);
    }
  }
  pintarBolas();
  atualizarStatus();
}

async function surpresinha() {
  const m = estado.modalidade;
  if (!m.pode_gerar || m.extra === "colunas" || m.extra === "loteca") {
    alert("Neste concurso use Mais jogos ou importe uma planilha.");
    return;
  }
  const res = await fetch("/api/surpresinha", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      modalidade: m.chave,
      dezenas: Number($("dez-volante").value),
      quantidade: 1,
      existentes: estado.jogos,
    }),
  });
  const dados = await res.json();
  if (!res.ok) {
    alert(dados.erro || "Não consegui gerar o jogo.");
    return;
  }
  const jogo = dados.jogos[0];
  estado.selecionados = new Set(jogo.dezenas);
  if (jogo.extras.mes) $("mes").value = String(jogo.extras.mes);
  if (jogo.extras.time) $("time").value = String(jogo.extras.time);
  if (jogo.extras.trevos) {
    estado.trevos = new Set(jogo.extras.trevos);
    pintarTrevos();
  }
  pintarBolas();
  atualizarStatus();
}

function colocarCarrinho() {
  const m = estado.modalidade;
  if (m.extra === "colunas" || m.extra === "loteca") {
    alert("Importe uma planilha ou use Mais jogos.");
    return;
  }
  if (estado.selecionados.size < m.min_dezenas) {
    alert(`Marque pelo menos ${m.min_dezenas} dezenas (estão ${estado.selecionados.size}).`);
    return;
  }
  let extras;
  try {
    extras = extrasAtuais();
  } catch (err) {
    alert(err.message);
    return;
  }
  const dezenas = [...estado.selecionados].sort((a, b) => a - b);
  estado.jogos.push({
    identificador: dezenas.map((n) => pad(n, m.largura_digitos)).join(""),
    dezenas,
    extras,
  });
  limparVolante();
  atualizarCarrinho();
  log(`Jogo adicionado. Total no carrinho: ${estado.jogos.length}.`);
}

function textoJogo(jogo, i) {
  const m = estado.modalidade;
  const nums = jogo.dezenas.map((n) => pad(n, m.largura_digitos)).join(" ");
  let extra = "";
  if (jogo.extras?.mes) extra = `  ·  ${MESES[jogo.extras.mes - 1]}`;
  if (jogo.extras?.time) extra = `  ·  time ${jogo.extras.time}`;
  if (jogo.extras?.trevos) extra = `  ·  trevos ${jogo.extras.trevos.join(" ")}`;
  return `${String(i).padStart(2, "0")}  ${nums}${extra}`;
}

function atualizarCarrinho() {
  $("qtd-carrinho").textContent = `${estado.jogos.length} jogo(s)`;
  const lista = $("lista-jogos");
  lista.innerHTML = "";
  estado.jogos.forEach((jogo, i) => {
    const li = document.createElement("li");
    li.textContent = textoJogo(jogo, i + 1);
    if (estado.selecionadoLista === i) li.className = "sel";
    li.addEventListener("click", () => {
      estado.selecionadoLista = i;
      atualizarCarrinho();
    });
    lista.appendChild(li);
  });
  simularSilencioso();
}

function mostrarTotais(dados) {
  $("total").textContent = dados.total;
  const n = dados.cotas || 1;
  $("por-cota").textContent = n === 1
    ? `1 cota · ${dados.por_cota} (só você)`
    : `${n} cotas · ${dados.por_cota} por pessoa`;
}

async function simularSilencioso() {
  if (!estado.jogos.length) {
    $("total").textContent = "R$ 0,00";
    $("por-cota").textContent = `${Math.max(1, Number($("cotas").value) || 1)} cota(s) · R$ 0,00 por pessoa`;
    return;
  }
  const res = await fetch("/api/simular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload()),
  });
  const dados = await res.json();
  if (res.ok) mostrarTotais(dados);
}

function payload() {
  return {
    modalidade: estado.modalidade.chave,
    teimosinha: Number($("teimosinha").value) || 0,
    cotas: Math.max(1, Number($("cotas").value) || 1),
    nome: $("nome-carrinho").value,
    salvar_favorito: $("salvar-fav").checked,
    jogos: estado.jogos,
  };
}

async function surpresinhaLote(qtd, dez) {
  const res = await fetch("/api/surpresinha", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      modalidade: estado.modalidade.chave,
      dezenas: dez,
      quantidade: qtd,
      existentes: estado.jogos,
    }),
  });
  const dados = await res.json();
  if (!res.ok) {
    alert(dados.erro || "Não consegui gerar os jogos.");
    return;
  }
  estado.jogos.push(...dados.jogos);
  atualizarCarrinho();
  log(`Surpresinha em lote: +${dados.jogos.length} jogo(s).`);
}

async function importarCsv(arquivo) {
  const csv = await arquivo.text();
  const res = await fetch("/api/parse-csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      modalidade: estado.modalidade.chave,
      csv,
      nome: arquivo.name,
    }),
  });
  const dados = await res.json();
  if (!res.ok) {
    alert(dados.erro || "Não li a planilha.");
    return;
  }
  if (dados.erros?.length) alert(dados.erros.slice(0, 8).join("\n"));
  estado.jogos.push(...dados.jogos);
  atualizarCarrinho();
  log(`Importados ${dados.jogos.length} jogo(s) de ${arquivo.name}`);
}

async function simular() {
  if (!estado.jogos.length) {
    alert("O carrinho está vazio.");
    return;
  }
  const res = await fetch("/api/simular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload()),
  });
  const dados = await res.json();
  if (!res.ok) {
    alert(dados.erro || "Falha na simulação.");
    return;
  }
  mostrarTotais(dados);
  $("log").textContent = [
    `${dados.quantidade} jogo(s) · subtotal ${dados.subtotal}`,
    dados.teimosinha
      ? `Teimosinha +${dados.teimosinha} · total ${dados.total}`
      : `Total ${dados.total}`,
    `${dados.cotas} cota(s) · ${dados.por_cota} por pessoa`,
    `Chance de pelo menos um prêmio: ${dados.chance_premio}`,
    `Chance de ${dados.acertos_maximo} acertos: ${dados.chance_max}`,
    "",
    ...dados.linhas,
  ].join("\n");
}

async function baixarPlanilha() {
  if (!estado.jogos.length) {
    alert("O carrinho está vazio.");
    return;
  }
  const res = await fetch("/api/csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload()),
  });
  if (!res.ok) {
    const dados = await res.json();
    alert(dados.erro || "Não gerei a planilha.");
    return;
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `apostas_${estado.modalidade.chave}_${estado.jogos.length}jogos.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
  log("Planilha baixada.");
}

async function enviar() {
  if (!estado.jogos.length) {
    alert("O carrinho está vazio.");
    return;
  }
  if (!confirm(`Enviar ${estado.jogos.length} jogo(s) ao site da Caixa?\nO pagamento continua no site oficial.`)) {
    return;
  }
  const res = await fetch("/api/enviar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload()),
  });
  const dados = await res.json();
  if (!res.ok) {
    alert(dados.erro || "Não comecei o envio.");
    return;
  }
  log("Enviando ao site… o navegador da Caixa vai abrir.");
  acompanhar(dados.job_id);
}

async function acompanhar(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`);
  const job = await res.json();
  if (job.logs?.length) $("log").textContent = job.logs.join("\n");
  if (!job.done) {
    setTimeout(() => acompanhar(jobId), 1000);
    return;
  }
  if (job.erro) alert(job.erro);
  else alert(`Incluídos: ${job.ok}  ·  Falhas: ${job.falhas}\nConfira o carrinho no navegador antes de pagar.`);
}

$("dez-volante").addEventListener("input", atualizarStatus);
$("btn-marcar").addEventListener("click", marcarDigitados);
$("btn-surpresa").addEventListener("click", () => surpresinha().catch((e) => alert(e)));
$("btn-limpar").addEventListener("click", limparVolante);
$("btn-cart").addEventListener("click", colocarCarrinho);
$("btn-remover").addEventListener("click", () => {
  if (estado.selecionadoLista == null) {
    alert("Selecione um jogo na lista.");
    return;
  }
  estado.jogos.splice(estado.selecionadoLista, 1);
  estado.selecionadoLista = null;
  atualizarCarrinho();
});
$("btn-esvaziar").addEventListener("click", () => {
  if (estado.jogos.length && confirm("Esvaziar todos os jogos?")) {
    estado.jogos = [];
    estado.selecionadoLista = null;
    atualizarCarrinho();
  }
});
$("btn-lote").addEventListener("click", () => {
  surpresinhaLote(Number($("qtd-lote").value), Number($("dez-lote").value));
});
$("btn-completar").addEventListener("click", () => {
  const alvo = Number($("completar").value);
  if (estado.jogos.length >= alvo) {
    alert(`Já existem ${estado.jogos.length} jogo(s).`);
    return;
  }
  surpresinhaLote(alvo - estado.jogos.length, estado.modalidade.min_dezenas);
});
$("arquivo-csv").addEventListener("change", (ev) => {
  const arquivo = ev.target.files?.[0];
  if (arquivo) importarCsv(arquivo);
  ev.target.value = "";
});
$("cotas").addEventListener("input", () => simularSilencioso());
$("teimosinha").addEventListener("input", () => simularSilencioso());
$("btn-simular").addEventListener("click", () => simular().catch((e) => alert(e)));
$("btn-planilha").addEventListener("click", () => baixarPlanilha().catch((e) => alert(e)));
$("btn-enviar").addEventListener("click", () => enviar().catch((e) => alert(e)));

const TUTORIAL_PASSOS = [
  {
    titulo: "Escolha o concurso",
    html: `
      <p>As bolinhas coloridas no topo são os concursos da Caixa. Clique em um: Lotofácil, Mega-Sena, Quina…</p>
      <p>A escolhida inverte as cores (fundo colorido, texto branco). As outras ficam com fundo branco e a cor da própria borda.</p>
      <div class="tutorial-exemplo">
        <strong>Exemplo</strong>
        Clique em <b>Lotofácil</b> para marcar 15 números de 01 a 25. Se mudar para Mega-Sena, o carrinho some — os números de um concurso não valem no outro.
      </div>`,
  },
  {
    titulo: "Monte um jogo",
    html: `
      <p>Três jeitos de preencher o volante:</p>
      <ul>
        <li>Clique nas bolinhas até completar a quantidade.</li>
        <li>Digite os números e aperte <b>Marcar</b>.</li>
        <li><b>Surpresinha</b> escolhe ao acaso. Confira e só depois coloque no carrinho.</li>
      </ul>
      <div class="tutorial-exemplo">
        <strong>Exemplo Lotofácil</strong>
        Campo “Dezenas neste jogo” = 15.<br>
        Digite: <code>01 05 07 09 11 12 15 16 18 20 21 22 23 24 25</code> e clique em Marcar.
      </div>
      <p>No Dia de Sorte escolha o mês; na Timemania, o time; na +Milionária, 2 trevos.</p>`,
  },
  {
    titulo: "Coloque no carrinho",
    html: `
      <p>Com o volante completo, clique em <b>Colocar no carrinho</b>. As bolinhas limpam para o próximo jogo. Repita quantas vezes quiser.</p>
      <p>Já tem planilha? Use <b>Importar CSV</b>. O cabeçalho esperado é <code>Jogo, D1, D2, …, Numeros</code> (vírgula ou ponto e vírgula do Excel).</p>
      <div class="tutorial-exemplo">
        <strong>Super Sete e Loteca</strong>
        Não há volante de bolinhas. Importe um CSV ou, se aparecer, use <b>Mais jogos</b>.
      </div>`,
  },
  {
    titulo: "Nome, Teimosinha e cotas",
    html: `
      <ul>
        <li><b>Nome do carrinho</b> — como o favorito aparece no site da Caixa.</li>
        <li><b>Teimosinha</b> — 0 = só este sorteio. 2 = este e os dois seguintes (o preço × 3).</li>
        <li><b>Cotas</b> — só divide o valor na tela. A Caixa cobra o total do grupo.</li>
      </ul>
      <div class="tutorial-exemplo">
        <strong>Exemplo de bolão</strong>
        Dois jogos de Lotofácil (R$ 3,50 cada) = R$ 7,00. Com 2 cotas, cada pessoa fica com <b>R$ 3,50</b>.<br>
        Se Teimosinha = 2, o total vira R$ 21,00 e cada cota R$ 10,50.
      </div>`,
  },
  {
    titulo: "Simule ou baixe a planilha",
    html: `
      <p><b>Simular chances</b> mostra no rodapé o preço e a probabilidade de algum prêmio. Não envia nada à Caixa.</p>
      <p><b>Gerar planilha</b> baixa um CSV para guardar ou reimportar depois.</p>
      <div class="tutorial-exemplo">
        <strong>Opcional: Mais jogos</strong>
        “Gerar e colocar” com 5 jogos de 15 dezenas cria 5 Surpresinhas de uma vez. “Completar até 10” enche o carrinho até essa quantidade.
      </div>`,
  },
  {
    titulo: "Envie ao site da Caixa",
    html: `
      <p><b>Enviar ao site da Caixa</b> abre o Loterias Online e marca os jogos no carrinho oficial.</p>
      <ul>
        <li>Faça login no site da Caixa no seu Chrome, Edge ou Firefox antes.</li>
        <li>O pagamento (Pix, cartão) é só no site oficial. Este programa não cobra.</li>
        <li>Confira o carrinho no navegador que abrir antes de pagar.</li>
      </ul>
      <div class="tutorial-exemplo">
        <strong>Se algo falhar</strong>
        A caixa preta no rodapé mostra o andamento. Você pode gerar a planilha e tentar de novo.
      </div>`,
  },
  {
    titulo: "Como encerrar",
    html: `
      <p><b>Feche esta aba</b> para desligar o aplicativo. Trocar de aba ou atualizar a página (F5) não fecha.</p>
      <p>Passe o mouse (ou toque no <b>?</b>) em qualquer campo para ver a dica daquela função. Este tutorial reabre no botão amarelo <b>Como usar</b>.</p>
      <div class="tutorial-exemplo">
        <strong>Resumo</strong>
        Concurso → volante ou CSV → carrinho → cotas/Teimosinha → simular → enviar → pagar no site da Caixa.
      </div>`,
  },
];

let tutorialIndice = 0;

function posicionarDica(el) {
  const bolha = $("dica-bolha");
  const r = el.getBoundingClientRect();
  const b = bolha.getBoundingClientRect();
  let top = r.top - b.height - 10;
  if (top < 8) top = r.bottom + 10;
  let left = r.left + r.width / 2 - b.width / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - b.width - 8));
  bolha.style.top = `${top}px`;
  bolha.style.left = `${left}px`;
}

function mostrarDica(el) {
  const texto = el.getAttribute("data-tip");
  if (!texto || !$("tutorial").hidden) return;
  const bolha = $("dica-bolha");
  bolha.textContent = texto;
  bolha.hidden = false;
  posicionarDica(el);
}

function esconderDica() {
  $("dica-bolha").hidden = true;
}

function alvoDica(ev) {
  return ev.target.closest?.("[data-tip]") || null;
}

document.addEventListener("pointerover", (ev) => {
  const el = alvoDica(ev);
  if (el) mostrarDica(el);
});
document.addEventListener("pointerout", (ev) => {
  const el = alvoDica(ev);
  if (!el) return;
  if (el.contains(ev.relatedTarget)) return;
  esconderDica();
});
document.addEventListener("focusin", (ev) => {
  if (ev.target.classList.contains("tip")) mostrarDica(ev.target);
});
document.addEventListener("focusout", () => esconderDica());
window.addEventListener("scroll", esconderDica, true);

function pintarTutorial() {
  const passo = TUTORIAL_PASSOS[tutorialIndice];
  $("tutorial-indice").textContent = `Passo ${tutorialIndice + 1} de ${TUTORIAL_PASSOS.length}`;
  $("tutorial-titulo").textContent = passo.titulo;
  $("tutorial-corpo").innerHTML = passo.html;
  $("tutorial-voltar").disabled = tutorialIndice === 0;
  $("tutorial-seguir").textContent =
    tutorialIndice === TUTORIAL_PASSOS.length - 1 ? "Concluir" : "Próximo";
}

function abrirTutorial(inicio = 0) {
  tutorialIndice = inicio;
  esconderDica();
  $("tutorial").hidden = false;
  pintarTutorial();
  $("tutorial-seguir").focus();
}

function fecharTutorial() {
  $("tutorial").hidden = true;
  try {
    localStorage.setItem("lottofill-viu-tutorial", "1");
  } catch (_err) {
    /* modo privado */
  }
  $("btn-tutorial").focus();
}

$("btn-tutorial").addEventListener("click", () => abrirTutorial(0));
$("tutorial-pular").addEventListener("click", fecharTutorial);
$("tutorial-voltar").addEventListener("click", () => {
  if (tutorialIndice > 0) {
    tutorialIndice -= 1;
    pintarTutorial();
  }
});
$("tutorial-seguir").addEventListener("click", () => {
  if (tutorialIndice >= TUTORIAL_PASSOS.length - 1) {
    fecharTutorial();
    return;
  }
  tutorialIndice += 1;
  pintarTutorial();
});
$("tutorial").addEventListener("click", (ev) => {
  if (ev.target.id === "tutorial") fecharTutorial();
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && !$("tutorial").hidden) fecharTutorial();
});

function manterAberto() {
  fetch("/api/vivo", { method: "POST", keepalive: true }).catch(() => {});
}

manterAberto();
setInterval(manterAberto, 2500);
window.addEventListener("pageshow", manterAberto);
window.addEventListener("pagehide", () => {
  navigator.sendBeacon("/api/sair");
});

carregar().then(() => {
  try {
    if (!localStorage.getItem("lottofill-viu-tutorial")) abrirTutorial(0);
  } catch (_err) {
    /* modo privado */
  }
}).catch((err) => {
  log(`Erro ao carregar: ${err}`);
});
