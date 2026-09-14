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
    btn.title = m.descricao_faixa;
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
    box.innerHTML = `<label class="rotulo">Mês da sorte</label>
      <select id="mes">${MESES.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("")}</select>
      <p class="ajuda">Obrigatório no Dia de Sorte, além das dezenas.</p>`;
  } else if (extra === "time") {
    box.innerHTML = `<label class="rotulo">Time do coração (1 a 80)</label>
      <input id="time" type="number" min="1" max="80" value="1">`;
  } else if (extra === "trevos") {
    box.innerHTML = `<p class="rotulo">Trevos (escolha 2)</p><div id="trevos" class="bolas"></div>`;
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
    box.innerHTML = `<p class="ajuda">Neste concurso não há volante de bolinhas. Importe uma planilha ou use Mais jogos.</p>`;
    return;
  }
  for (let n = m.dezena_min; n <= m.dezena_max; n += 1) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "bola";
    b.textContent = pad(n, m.largura_digitos);
    b.title = `Marcar ou desmarcar a dezena ${pad(n, m.largura_digitos)}`;
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

function manterAberto() {
  fetch("/api/vivo", { method: "POST", keepalive: true }).catch(() => {});
}

manterAberto();
setInterval(manterAberto, 2500);
window.addEventListener("pageshow", manterAberto);
window.addEventListener("pagehide", () => {
  navigator.sendBeacon("/api/sair");
});

carregar().catch((err) => {
  log(`Erro ao carregar: ${err}`);
});
