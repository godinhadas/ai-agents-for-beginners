"use strict";

// ---------- utilitários ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const kz = (v) => (v == null ? "" : new Intl.NumberFormat("pt-AO", { maximumFractionDigits: 0 }).format(v) + " Kz");
const dataPT = (v) => (v ? new Date(v + "T00:00:00").toLocaleDateString("pt-PT") : "");
const ROTULOS = {
  prospeccao: "Prospecção", proposta: "Proposta", negociacao: "Negociação", ganha: "Ganha", perdida: "Perdida",
  participado: "Participado", em_analise: "Em análise", aprovado: "Aprovado", recusado: "Recusado", pago: "Pago",
  activa: "Activa", suspensa: "Suspensa", anulada: "Anulada", expirada: "Expirada",
  particular: "Particular", empresa: "Empresa",
  chamada: "Chamada", email: "Email", reuniao: "Reunião", nota: "Nota", tarefa: "Tarefa",
};
const rot = (v) => ROTULOS[v] ?? v;
const CLASSE_ESTADO = { em_analise: "alerta", participado: "alerta", recusado: "perigo", anulada: "perigo",
  expirada: "perigo", suspensa: "alerta", pago: "ok", activa: "ok", ganha: "ok", perdida: "perigo" };
const etiqueta = (v) => `<span class="etiqueta ${CLASSE_ESTADO[v] ?? ""}">${esc(rot(v))}</span>`;

async function api(caminho, opcoes = {}) {
  const r = await fetch(caminho, { headers: { "Content-Type": "application/json" }, ...opcoes });
  if (r.status === 204) return null;
  const corpo = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = corpo.detail;
    const msg = Array.isArray(d) ? d.map((e) => { const campo = (e.loc || []).slice(1).join("."); const m = String(e.msg).replace(/^Value error, /, ""); return campo ? `${campo}: ${m}` : m; }).join("; ") : d;
    throw new Error(msg || `Erro ${r.status}`);
  }
  return corpo;
}

// ---------- definição das entidades ----------
const RAMOS = ["Automóvel", "Saúde", "Vida", "Multirriscos", "Acidentes de Trabalho", "Viagem", "Responsabilidade Civil"];
const PROVINCIAS = ["Bengo", "Benguela", "Bié", "Cabinda", "Cuando", "Cubango", "Cuanza Norte", "Cuanza Sul", "Cunene",
  "Huambo", "Huíla", "Icolo e Bengo", "Luanda", "Lunda Norte", "Lunda Sul", "Malanje", "Moxico", "Moxico Leste",
  "Namibe", "Uíge", "Zaire"];

const ENTIDADES = {
  clientes: {
    titulo: "Clientes", singular: "cliente",
    campos: [
      { k: "tipo", l: "Tipo", t: "select", o: ["particular", "empresa"], req: true },
      { k: "nome", l: "Nome", req: true },
      { k: "nif", l: "NIF (número de identificação fiscal)", req: true },
      { k: "provincia", l: "Província", t: "select", o: PROVINCIAS },
      { k: "email", l: "Email", t: "email" },
      { k: "telefone", l: "Telefone" },
      { k: "mediador_id", l: "Mediador", t: "ref", ref: "mediadores" },
    ],
    colunas: [["nome", "Nome", (v, o) => `<button class="ligacao" data-360="${o.id}">${esc(v)}</button>`],
      ["tipo", "Tipo", rot], ["nif", "NIF"], ["provincia", "Província"], ["telefone", "Telefone"], ["email", "Email"]],
  },
  apolices: {
    titulo: "Apólices", singular: "apólice",
    campos: [
      { k: "numero", l: "Número", req: true },
      { k: "cliente_id", l: "Cliente", t: "ref", ref: "clientes", req: true },
      { k: "ramo", l: "Ramo", t: "select", o: RAMOS, req: true },
      { k: "estado", l: "Estado", t: "select", o: ["activa", "suspensa", "anulada", "expirada"] },
      { k: "premio_anual", l: "Prémio anual (Kz)", t: "number", req: true },
      { k: "capital_seguro", l: "Capital seguro (Kz)", t: "number" },
      { k: "data_inicio", l: "Início", t: "date", req: true },
      { k: "data_fim", l: "Fim", t: "date", req: true },
    ],
    colunas: [["numero", "Número"], ["cliente_id", "Cliente", (v) => nomeRef("clientes", v)], ["ramo", "Ramo"],
      ["premio_anual", "Prémio anual", kz, "num"], ["data_fim", "Fim", dataPT], ["estado", "Estado", etiqueta]],
  },
  sinistros: {
    titulo: "Sinistros", singular: "sinistro",
    campos: [
      { k: "numero", l: "Número", req: true },
      { k: "apolice_id", l: "Apólice", t: "ref", ref: "apolices", req: true },
      { k: "data_ocorrencia", l: "Data de ocorrência", t: "date", req: true },
      { k: "estado", l: "Estado", t: "select", o: ["participado", "em_analise", "aprovado", "recusado", "pago"] },
      { k: "valor_reclamado", l: "Valor reclamado (Kz)", t: "number" },
      { k: "valor_pago", l: "Valor pago (Kz)", t: "number" },
      { k: "descricao", l: "Descrição", t: "textarea", req: true },
    ],
    colunas: [["numero", "Número"], ["apolice_id", "Apólice", (v) => nomeRef("apolices", v)],
      ["data_ocorrencia", "Ocorrência", dataPT], ["valor_reclamado", "Reclamado", kz, "num"],
      ["valor_pago", "Pago", kz, "num"], ["estado", "Estado", etiqueta]],
  },
  oportunidades: {
    titulo: "Oportunidades", singular: "oportunidade",
    campos: [
      { k: "titulo", l: "Título", req: true, largo: true },
      { k: "cliente_id", l: "Cliente", t: "ref", ref: "clientes", req: true },
      { k: "ramo", l: "Ramo", t: "select", o: RAMOS, req: true },
      { k: "fase", l: "Fase", t: "select", o: ["prospeccao", "proposta", "negociacao", "ganha", "perdida"] },
      { k: "valor_estimado", l: "Prémio estimado (Kz)", t: "number" },
      { k: "data_prevista", l: "Fecho previsto", t: "date" },
    ],
    colunas: [["titulo", "Título"], ["cliente_id", "Cliente", (v) => nomeRef("clientes", v)], ["ramo", "Ramo"],
      ["valor_estimado", "Valor", kz, "num"], ["data_prevista", "Fecho previsto", dataPT], ["fase", "Fase", etiqueta]],
  },
  actividades: {
    titulo: "Actividades", singular: "actividade",
    campos: [
      { k: "cliente_id", l: "Cliente", t: "ref", ref: "clientes", req: true },
      { k: "tipo", l: "Tipo", t: "select", o: ["chamada", "email", "reuniao", "nota", "tarefa"], req: true },
      { k: "assunto", l: "Assunto", req: true, largo: true },
      { k: "data", l: "Data", t: "date" },
      { k: "concluida", l: "Concluída", t: "checkbox" },
      { k: "descricao", l: "Descrição", t: "textarea" },
    ],
    colunas: [["data", "Data", dataPT], ["tipo", "Tipo", rot], ["assunto", "Assunto"],
      ["cliente_id", "Cliente", (v) => nomeRef("clientes", v)], ["concluida", "Estado", (v) => (v ? etiqueta("Concluída") : etiqueta("Pendente"))]],
  },
  mediadores: {
    titulo: "Mediadores", singular: "mediador",
    campos: [
      { k: "codigo", l: "Código", req: true },
      { k: "nome", l: "Nome", req: true },
      { k: "email", l: "Email", t: "email" },
      { k: "telefone", l: "Telefone" },
      { k: "comissao_pct", l: "Comissão (%)", t: "number" },
    ],
    colunas: [["codigo", "Código"], ["nome", "Nome"], ["email", "Email"], ["telefone", "Telefone"],
      ["comissao_pct", "Comissão", (v) => `${v}%`, "num"]],
  },
};

// Cache de referências para mostrar nomes em vez de ids.
const cache = {};
async function carregarRef(ref) {
  cache[ref] = await api(`/api/${ref}?limit=1000`);
  return cache[ref];
}
function nomeRef(ref, id) {
  const o = (cache[ref] || []).find((x) => x.id === id);
  return esc(o ? o.nome ?? o.numero : id ?? "");
}

// ---------- navegação ----------
const SECCOES = [["painel", "Painel"], ["clientes", "Clientes"], ["apolices", "Apólices"], ["sinistros", "Sinistros"],
  ["oportunidades", "Oportunidades"], ["actividades", "Actividades"], ["mediadores", "Mediadores"], ["assistente", "Assistente IA"]];
const nav = document.getElementById("nav");
const conteudo = document.getElementById("conteudo");
nav.innerHTML = SECCOES.map(([id, l]) => `<button data-sec="${id}">${l}</button>`).join("");
nav.addEventListener("click", (e) => { if (e.target.dataset.sec) location.hash = e.target.dataset.sec; });
window.addEventListener("hashchange", mostrar);
conteudo.addEventListener("click", (e) => {
  const b = e.target.closest("[data-360]");
  if (b) abrir360(Number(b.dataset["360"]));
});

async function mostrar() {
  const sec = location.hash.slice(1) || "painel";
  nav.querySelectorAll("button").forEach((b) => b.classList.toggle("activo", b.dataset.sec === sec));
  try {
    if (sec === "painel") await vistaPainel();
    else if (sec === "assistente") vistaAssistente();
    else if (ENTIDADES[sec]) await vistaLista(sec);
  } catch (err) {
    conteudo.innerHTML = `<p class="erro">${esc(err.message)}</p>`;
  }
}

// ---------- painel ----------
async function vistaPainel() {
  const [p] = await Promise.all([api("/api/painel"), carregarRef("clientes")]);
  const maxPipe = Math.max(1, ...p.pipeline.map((x) => x.valor));
  const maxRamo = Math.max(1, ...p.por_ramo.map((x) => x.premio));
  conteudo.innerHTML = `
    <h1>Painel</h1>
    <div class="kpis">
      ${kpi("Clientes", p.clientes)}
      ${kpi("Apólices activas", p.apolices_activas)}
      ${kpi("Prémio anual em carteira", kz(p.premio_anual_activo))}
      ${kpi("Renovações em 30 dias", p.renovacoes_30, `${p.renovacoes_60} em 60 dias, ${p.renovacoes_90} em 90`)}
      ${kpi("Sinistros em aberto", p.sinistros_abertos, kz(p.valor_sinistros_abertos) + " reclamados")}
      ${kpi("Pipeline em aberto", kz(p.pipeline_aberto))}
    </div>
    <div class="grelha">
      <section class="cartao"><h2>Próximas renovações (90 dias)</h2>
        ${tabela(p.proximas_renovacoes, [["numero", "Apólice"], ["cliente", "Cliente", (v, o) => `<button class="ligacao" data-360="${o.cliente_id}">${esc(v)}</button>`],
          ["premio_anual", "Prémio", kz, "num"],
          ["dias_restantes", "Dias", (v) => `<span class="etiqueta ${v <= 30 ? "perigo" : v <= 60 ? "alerta" : ""}">${v}</span>`, "num"]])}
      </section>
      <section class="cartao"><h2>Pipeline comercial</h2>
        ${p.pipeline.map((x) => barra(`${rot(x.fase)} (${x.quantidade})`, x.valor / maxPipe, kz(x.valor))).join("")}
        <h2 style="margin-top:20px">Carteira por ramo</h2>
        ${p.por_ramo.map((x) => barra(`${x.ramo}`, x.premio / maxRamo, kz(x.premio))).join("") || '<p class="vazio">Sem apólices activas.</p>'}
      </section>
    </div>`;
}
const kpi = (r, v, nota = "") => `<div class="cartao kpi"><div class="rotulo">${esc(r)}</div><div class="valor">${esc(v)}</div><div class="nota">${esc(nota)}</div></div>`;
const barra = (r, frac, v) => `<div class="barra-h"><span>${esc(r)}</span><div class="trilho"><div class="enchimento" style="width:${(frac * 100).toFixed(1)}%"></div></div><span class="num" style="text-align:right">${esc(v)}</span></div>`;

function tabela(linhas, colunas, accoes = false) {
  if (!linhas.length) return '<p class="vazio">Sem registos.</p>';
  const cab = colunas.map(([, l, , c]) => `<th class="${c || ""}">${esc(l)}</th>`).join("") + (accoes ? "<th></th>" : "");
  const corpo = linhas.map((o) => "<tr>" + colunas.map(([k, , f, c]) => {
    const v = o[k];
    return `<td class="${c || ""}">${f ? f(v, o) : esc(v)}</td>`;
  }).join("") + (accoes ? `<td><div class="acoes"><button data-editar="${o.id}">Editar</button><button data-apagar="${o.id}">Apagar</button></div></td>` : "") + "</tr>").join("");
  return `<div class="tabela"><table><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table></div>`;
}

// ---------- listas genéricas ----------
async function vistaLista(nome, q = "") {
  const ent = ENTIDADES[nome];
  const refs = [...new Set(ent.campos.filter((c) => c.ref).map((c) => c.ref))];
  const [linhas] = await Promise.all([api(`/api/${nome}?q=${encodeURIComponent(q)}`), ...refs.map(carregarRef)]);
  conteudo.innerHTML = `
    <h1>${ent.titulo}</h1>
    <div class="barra">
      <input type="search" id="pesquisa" placeholder="Pesquisar ${ent.titulo.toLowerCase()}..." value="${esc(q)}">
      <button class="primario" id="novo">Novo ${ent.singular}</button>
    </div>
    <section class="cartao">${tabela(linhas, ent.colunas, true)}</section>`;
  const pesquisa = document.getElementById("pesquisa");
  let t;
  pesquisa.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => vistaLista(nome, pesquisa.value).then(() => {
    const p = document.getElementById("pesquisa"); p.focus(); p.setSelectionRange(p.value.length, p.value.length);
  }), 300); });
  document.getElementById("novo").onclick = () => abrirFormulario(nome, null, () => vistaLista(nome, q));
  conteudo.querySelectorAll("[data-editar]").forEach((b) => (b.onclick = () =>
    abrirFormulario(nome, linhas.find((x) => x.id === Number(b.dataset.editar)), () => vistaLista(nome, q))));
  conteudo.querySelectorAll("[data-apagar]").forEach((b) => (b.onclick = async () => {
    if (!confirm(`Apagar este registo de ${ent.singular}?`)) return;
    try { await api(`/api/${nome}/${b.dataset.apagar}`, { method: "DELETE" }); vistaLista(nome, q); }
    catch (err) { alert(err.message); }
  }));
}

// ---------- formulário ----------
const dialogo = document.getElementById("dialogo");
const formDialogo = document.getElementById("form-dialogo");

async function abrirFormulario(nome, obj, aoGravar) {
  const ent = ENTIDADES[nome];
  await Promise.all([...new Set(ent.campos.filter((c) => c.ref).map((c) => c.ref))].map(carregarRef));
  document.getElementById("dialogo-titulo").textContent = `${obj ? "Editar" : "Novo"} ${ent.singular}`;
  document.getElementById("dialogo-erro").textContent = "";
  document.getElementById("btn-gravar").hidden = false;
  document.getElementById("dialogo-corpo").innerHTML = ent.campos.map((c) => campoHTML(c, obj?.[c.k])).join("");
  dialogo.showModal();
  formDialogo.onsubmit = async (e) => {
    if (e.submitter?.value !== "gravar") return;
    e.preventDefault();
    const dados = {};
    for (const c of ent.campos) {
      const el = formDialogo.elements[c.k];
      let v = c.t === "checkbox" ? el.checked : el.value.trim();
      if (v === "") v = null;
      else if (c.t === "number" || c.t === "ref") v = Number(v);
      if (v !== null || obj) dados[c.k] = v;
    }
    try {
      await api(obj ? `/api/${nome}/${obj.id}` : `/api/${nome}`, { method: obj ? "PATCH" : "POST", body: JSON.stringify(dados) });
      dialogo.close();
      aoGravar?.();
    } catch (err) {
      document.getElementById("dialogo-erro").textContent = err.message;
    }
  };
}

function campoHTML(c, valor) {
  const req = c.req ? "required" : "";
  const v = valor ?? "";
  let input;
  if (c.t === "select") {
    input = `<select name="${c.k}" ${req}><option value=""></option>${c.o.map((o) => `<option value="${esc(o)}" ${o === v ? "selected" : ""}>${esc(rot(o))}</option>`).join("")}</select>`;
  } else if (c.t === "ref") {
    input = `<select name="${c.k}" ${req}><option value=""></option>${(cache[c.ref] || []).map((o) => `<option value="${o.id}" ${o.id === v ? "selected" : ""}>${esc(o.nome ?? o.numero)}</option>`).join("")}</select>`;
  } else if (c.t === "textarea") {
    input = `<textarea name="${c.k}" rows="3" ${req}>${esc(v)}</textarea>`;
  } else if (c.t === "checkbox") {
    input = `<input type="checkbox" name="${c.k}" style="width:auto" ${v ? "checked" : ""}>`;
  } else {
    input = `<input type="${c.t || "text"}" name="${c.k}" value="${esc(v)}" ${c.t === "number" ? 'step="any" min="0"' : ""} ${req}>`;
  }
  return `<label class="${c.largo || c.t === "textarea" ? "largo" : ""}">${esc(c.l)}${c.req ? " *" : ""}${input}</label>`;
}

// ---------- visão 360 do cliente ----------
async function abrir360(id) {
  try {
    const v = await api(`/api/clientes/${id}/360`);
    const c = v.cliente;
    document.getElementById("dialogo-titulo").textContent = c.nome;
    document.getElementById("dialogo-erro").textContent = "";
    document.getElementById("btn-gravar").hidden = true;
    formDialogo.onsubmit = null;
    document.getElementById("dialogo-corpo").innerHTML = `
      <div class="largo">${etiqueta(c.tipo)} NIF ${esc(c.nif)} · ${esc(c.provincia || "")} · ${esc(c.telefone || "")} · ${esc(c.email || "")}
        ${c.mediador ? `<br>Mediador: ${esc(c.mediador)}` : ""}<br><strong>Prémio activo: ${kz(v.premio_total_activo)}</strong></div>
      <div class="largo"><h2>Apólices</h2>${tabela(v.apolices, [["numero", "Número"], ["ramo", "Ramo"], ["premio_anual", "Prémio", kz, "num"], ["data_fim", "Fim", dataPT], ["estado", "Estado", etiqueta]])}</div>
      <div class="largo"><h2>Sinistros</h2>${tabela(v.sinistros, [["numero", "Número"], ["apolice", "Apólice"], ["data_ocorrencia", "Ocorrência", dataPT], ["valor_reclamado", "Reclamado", kz, "num"], ["estado", "Estado", etiqueta]])}</div>
      <div class="largo"><h2>Oportunidades</h2>${tabela(v.oportunidades, [["titulo", "Título"], ["ramo", "Ramo"], ["valor_estimado", "Valor", kz, "num"], ["fase", "Fase", etiqueta]])}</div>
      <div class="largo"><h2>Actividades</h2>${tabela(v.actividades, [["data", "Data", dataPT], ["tipo", "Tipo", rot], ["assunto", "Assunto"]])}</div>`;
    dialogo.showModal();
  } catch (err) {
    alert(err.message);
  }
}

// ---------- assistente IA ----------
const conversa = [];
function vistaAssistente() {
  conteudo.innerHTML = `
    <h1>Assistente IA</h1>
    <section class="cartao chat">
      <div class="historico" id="historico"></div>
      <div class="sugestoes">
        ${["Que apólices renovam nos próximos 30 dias?", "Resume a situação da Construções Kalandula.",
           "Que sinistros estão em aberto há mais de 30 dias?", "Como está o pipeline comercial?"]
          .map((s) => `<button type="button">${esc(s)}</button>`).join("")}
      </div>
      <form id="form-chat"><input id="pergunta" placeholder="Pergunta sobre clientes, apólices, sinistros, renovações..." autocomplete="off" required>
        <button class="primario">Enviar</button></form>
    </section>`;
  desenharConversa();
  const input = document.getElementById("pergunta");
  conteudo.querySelectorAll(".sugestoes button").forEach((b) => (b.onclick = () => { input.value = b.textContent; input.focus(); }));
  document.getElementById("form-chat").onsubmit = async (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    input.value = "";
    conversa.push({ role: "user", content: texto });
    desenharConversa(true);
    try {
      const r = await api("/api/agente/chat", { method: "POST", body: JSON.stringify({ mensagens: conversa.filter((m) => !m.erro).slice(-20).map(({ role, content }) => ({ role, content })) }) });
      conversa.push({ role: "assistant", content: r.resposta, accoes: r.accoes });
    } catch (err) {
      conversa.push({ role: "assistant", content: `Erro: ${err.message}`, erro: true });
    }
    desenharConversa();
  };
}
function desenharConversa(aPensar = false) {
  const h = document.getElementById("historico");
  if (!h) return;
  h.innerHTML = (conversa.length ? "" : '<p class="vazio">Faz uma pergunta. O assistente consulta os dados do CRM e pode registar actividades quando lhe pedes.</p>') +
    conversa.map((m) => `<div class="msg ${m.role}">${esc(m.content)}${m.accoes?.length ? `<div class="ferramentas">Consultou: ${m.accoes.map((a) => esc(a.ferramenta)).join(", ")}</div>` : ""}</div>`).join("") +
    (aPensar ? '<div class="msg assistant">A consultar o CRM...</div>' : "");
  h.scrollTop = h.scrollHeight;
}

mostrar();
