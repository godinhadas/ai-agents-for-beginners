"use strict";

// ---------- utilitários ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const kz = (v) => (v == null ? "" : new Intl.NumberFormat("pt-AO", { maximumFractionDigits: 0 }).format(v) + " Kz");
const dataPT = (v) => (v ? new Date(v.length === 10 ? v + "T00:00:00" : v).toLocaleDateString("pt-PT") : "");
const dataHora = (v) => (v ? new Date(v).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" }) : "");
const ROTULOS = {
  em_aprovacao: "Em aprovação", novo: "Novo", em_curso: "Em curso", aguarda_colaborador: "A aguardar colaborador",
  resolvido: "Resolvido", fechado: "Fechado", recusado: "Recusado", cancelado: "Cancelado",
  critica: "Crítica", alta: "Alta", media: "Média", baixa: "Baixa",
  incidente: "Incidente", equipamento: "Equipamento", licenca: "Licença / software", acesso: "Acesso", informacao: "Informação",
  colaborador: "Colaborador", chefia: "Chefia", helpdesk: "Helpdesk", admin: "Administrador DSI",
  stock: "Em stock", atribuido: "Atribuído", reparacao: "Em reparação", abatido: "Abatido",
  ok: "No prazo", em_risco: "Em risco", violado: "Fora de prazo", cumprido: "Cumprido", pausado: "Pausado", "n/a": "",
  criado: "Pedido criado", aguarda_aprovacao: "A aguardar aprovação", aprovado: "Aprovado", atribuido_ev: "Atribuído",
  prioridade: "Prioridade alterada", reaberto: "Reaberto", equipamento_entregue: "Equipamento entregue",
  licenca_atribuida: "Licença atribuída", resposta_colaborador: "Resposta do colaborador",
};
const rot = (v) => ROTULOS[v] ?? v;
const CLASSE = { em_aprovacao: "alerta", aguarda_colaborador: "alerta", resolvido: "ok", fechado: "", recusado: "perigo",
  cancelado: "", critica: "perigo", alta: "alerta", violado: "perigo", em_risco: "alerta", ok: "ok", cumprido: "ok",
  stock: "ok", reparacao: "alerta", abatido: "perigo" };
const etiqueta = (v) => (v && rot(v) ? `<span class="etiqueta ${CLASSE[v] ?? ""}">${esc(rot(v))}</span>` : "");
const $ = (id) => document.getElementById(id);

async function api(caminho, opcoes = {}) {
  const r = await fetch(caminho, { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...opcoes });
  if (r.status === 401 && !caminho.startsWith("/api/auth")) { eu = null; mostrarLogin(); throw new Error("Sessão expirada."); }
  if (r.status === 204) return null;
  const corpo = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = corpo.detail;
    const msg = Array.isArray(d)
      ? d.map((e) => { const c = (e.loc || []).slice(1).join("."); const m = String(e.msg).replace(/^Value error, /, ""); return c ? `${c}: ${m}` : m; }).join("; ")
      : d;
    throw new Error(msg || `Erro ${r.status}`);
  }
  return corpo;
}

let eu = null;
const staff = () => eu && (eu.perfil === "helpdesk" || eu.perfil === "admin");
const cache = {};
async function carregar(ref, url) { cache[ref] = await api(url || `/api/${ref}?limit=2000`); return cache[ref]; }
const nomeDe = (ref, id) => { const o = (cache[ref] || []).find((x) => x.id === id); return o ? (o.nome ?? o.produto ?? o.etiqueta) : ""; };

// ---------- arranque e sessão ----------
const nav = $("nav"), conteudo = $("conteudo");

let cfg = { empresa: "MHAIS", nome: "Portal DSI", direccao: "", logo: "/static/marca/logo.svg" };
async function aplicarMarca() {
  try { cfg = await api("/api/config"); } catch { /* mantém os valores por omissão */ }
  $("logo").src = cfg.logo;
  $("logo").alt = cfg.empresa;
  $("nome-portal").textContent = cfg.nome;
  document.title = `${cfg.nome} · ${cfg.empresa}`;
  $("rodape").innerHTML = `${esc(cfg.empresa)} · ${esc(cfg.direccao)}${contactosHTML(" · ")}`;
}
const contactosHTML = (sep) => [
  cfg.contacto_email && `Helpdesk: <a href="mailto:${esc(cfg.contacto_email)}">${esc(cfg.contacto_email)}</a>`,
  cfg.contacto_telefone && `Tel. ${esc(cfg.contacto_telefone)}`,
  cfg.horario && esc(cfg.horario),
].filter(Boolean).map((x) => sep + x).join("");

async function arrancar() {
  if (!arrancar.feito) { arrancar.feito = true; await aplicarMarca(); }
  try { eu = await api("/api/eu"); } catch { eu = null; }
  if (!eu) return mostrarLogin();
  desenharNav();
  mostrar();
}

async function mostrarLogin() {
  nav.innerHTML = ""; $("utilizador").innerHTML = "";
  const { modo } = await api("/api/auth/modo");
  if (modo !== "dev") {
    conteudo.innerHTML = `<section class="cartao login">
      <img class="logo-grande" src="${esc(cfg.logo)}" alt="${esc(cfg.empresa)}">
      <h1>${esc(cfg.nome)}</h1>
      <p>Pedidos à ${esc(cfg.direccao || "DSI")}: incidentes, equipamentos, licenças e acessos.</p>
      <button class="primario" onclick="location.href='/auth/login'">Entrar com a conta Microsoft da ${esc(cfg.empresa)}</button>
      <div class="contactos">Sem acesso ao portal?${contactosHTML("<br>")}</div></section>`;
    return;
  }
  const us = await api("/api/auth/utilizadores-demo");
  const grupos = ["admin", "helpdesk", "chefia", "colaborador"].map((p) => [p, us.filter((u) => u.perfil === p)]);
  conteudo.innerHTML = `<section class="cartao login">
    <img class="logo-grande" src="${esc(cfg.logo)}" alt="${esc(cfg.empresa)}">
    <h1>${esc(cfg.nome)}</h1>
    <p class="vazio">Modo de demonstração: escolhe com que utilizador queres entrar. Em produção, o acesso será feito com a conta Microsoft da MHAIS.</p>
    ${grupos.map(([p, l]) => `<div class="grupo"><h2>${esc(rot(p))}</h2>${l.map((u) => `<button data-login="${u.id}">${esc(u.nome)}</button>`).join("")}</div>`).join("")}
  </section>`;
  conteudo.querySelectorAll("[data-login]").forEach((b) => (b.onclick = async () => {
    await api("/api/auth/login", { method: "POST", body: JSON.stringify({ utilizador_id: Number(b.dataset.login) }) });
    location.hash = "inicio";
    arrancar();
  }));
}

function desenharNav() {
  const itens = [["inicio", "Início"], ["pedidos", "Pedidos"]];
  if (staff()) itens.push(["painel", "Painel DSI"], ["equipamentos", "Equipamentos"], ["licencas", "Licenças"]);
  if (eu.perfil === "admin") itens.push(["admin", "Administração"]);
  nav.innerHTML = itens.map(([id, l]) => `<button data-sec="${id}">${l}</button>`).join("");
  $("utilizador").innerHTML = `<span>${esc(eu.nome)} · ${esc(rot(eu.perfil))}</span><button id="sair">Sair</button>`;
  $("sair").onclick = async () => { await api("/api/auth/logout", { method: "POST" }); eu = null; location.hash = ""; mostrarLogin(); };
}
nav.addEventListener("click", (e) => { if (e.target.dataset.sec) location.hash = e.target.dataset.sec; });
window.addEventListener("hashchange", () => eu && mostrar());
conteudo.addEventListener("click", (e) => {
  const b = e.target.closest("[data-pedido]");
  if (b) location.hash = `pedido/${b.dataset.pedido}`;
});

async function mostrar() {
  const [sec, arg] = (location.hash.slice(1) || "inicio").split("/");
  nav.querySelectorAll("button").forEach((b) => b.classList.toggle("activo", b.dataset.sec === (sec === "pedido" || sec === "novo" ? "pedidos" : sec)));
  try {
    const vistas = { inicio: vistaInicio, pedidos: vistaPedidos, pedido: () => vistaPedido(Number(arg)), novo: vistaNovo,
      painel: vistaPainel, equipamentos: () => vistaLista("equipamentos"), licencas: vistaLicencas, admin: () => vistaAdmin(arg || "utilizadores") };
    await (vistas[sec] || vistaInicio)();
  } catch (err) {
    if (eu) conteudo.innerHTML = `<p class="erro">${esc(err.message)}</p>`;
  }
}

// ---------- tabelas ----------
function tabela(linhas, colunas, { accoes = false, clicavel = false } = {}) {
  if (!linhas.length) return '<p class="vazio">Sem registos.</p>';
  const cab = colunas.map(([, l, , c]) => `<th class="${c || ""}">${esc(l)}</th>`).join("") + (accoes ? "<th></th>" : "");
  const corpo = linhas.map((o) => `<tr ${clicavel ? `data-pedido="${o.id}" style="cursor:pointer"` : ""}>` + colunas.map(([k, , f, c]) =>
    `<td class="${c || ""}">${f ? f(o[k], o) : esc(o[k])}</td>`).join("") +
    (accoes ? `<td><div class="acoes"><button data-editar="${o.id}">Editar</button></div></td>` : "") + "</tr>").join("");
  return `<div class="tabela"><table><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table></div>`;
}
const COLS_PEDIDO = [
  ["numero", "Nº", (v) => `<strong>${esc(v)}</strong>`], ["titulo", "Assunto"], ["beneficiario", "Para"],
  ["prioridade", "Prioridade", etiqueta], ["estado", "Estado", etiqueta], ["tecnico", "Técnico"],
  ["actualizado_em", "Actualizado", dataHora], ["sla", "SLA", etiqueta],
];
const kpi = (r, v, nota = "") => `<div class="cartao kpi"><div class="rotulo">${esc(r)}</div><div class="valor">${esc(v)}</div><div class="nota">${esc(nota)}</div></div>`;
const barra = (r, frac, v) => `<div class="barra-h"><span>${esc(r)}</span><div class="trilho"><div class="enchimento" style="width:${(frac * 100).toFixed(1)}%"></div></div><span style="text-align:right">${esc(v)}</span></div>`;

// ---------- início ----------
async function vistaInicio() {
  const d = await api("/api/inicio");
  conteudo.innerHTML = `
    <div class="cabecalho"><h1>Olá, ${esc(eu.nome.split(" ")[0])}</h1><button class="primario" onclick="location.hash='novo'">Novo pedido</button></div>
    ${d.para_aprovar.length ? `<section class="cartao" style="margin-bottom:16px"><h2>Pedidos à espera da tua aprovação (${d.para_aprovar.length})</h2>${tabela(d.para_aprovar, COLS_PEDIDO, { clicavel: true })}</section>` : ""}
    <section class="cartao" style="margin-bottom:16px"><h2>Os meus pedidos em curso</h2>${tabela(d.meus_pedidos, COLS_PEDIDO, { clicavel: true })}</section>
    <div class="grelha">
      <section class="cartao"><h2>O meu equipamento</h2>${tabela(d.equipamentos, [["etiqueta", "Etiqueta"], ["tipo", "Tipo"], ["marca", "Marca"], ["modelo", "Modelo"]])}</section>
      <section class="cartao"><h2>As minhas licenças</h2>${d.licencas.length ? `<ul>${d.licencas.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : '<p class="vazio">Sem licenças atribuídas.</p>'}</section>
    </div>`;
}

// ---------- lista de pedidos ----------
let filtroPedidos = null;
async function vistaPedidos() {
  const vistas = [["meus", "Os meus"]];
  if (eu.perfil === "chefia" || eu.perfil === "admin") vistas.push(["equipa", "Da minha equipa"]);
  vistas.push(["aprovar", "Para aprovar"]);
  if (staff()) vistas.push(["atribuidos", "Atribuídos a mim"], ["todos", "Todos"]);
  filtroPedidos ??= { vista: staff() ? "todos" : "meus", estado: "abertos", q: "" };
  const f = filtroPedidos;
  const params = new URLSearchParams({ vista: f.vista, estado: f.estado, q: f.q });
  const linhas = await api(`/api/pedidos?${params}`);
  conteudo.innerHTML = `
    <div class="cabecalho"><h1>Pedidos</h1><button class="primario" onclick="location.hash='novo'">Novo pedido</button></div>
    <div class="abas">${vistas.map(([v, l]) => `<button data-vista="${v}" class="${f.vista === v ? "activo" : ""}">${l}</button>`).join("")}</div>
    <div class="barra">
      <input type="search" id="pesquisa" placeholder="Pesquisar por assunto, descrição ou PED-000123" value="${esc(f.q)}">
      <select id="estado" style="max-width:220px">
        ${[["abertos", "Em aberto"], ["", "Todos os estados"], ["resolvido", "Resolvidos"], ["fechado", "Fechados"], ["recusado", "Recusados"], ["cancelado", "Cancelados"]]
          .map(([v, l]) => `<option value="${v}" ${f.estado === v ? "selected" : ""}>${l}</option>`).join("")}
      </select>
    </div>
    <section class="cartao">${tabela(linhas, COLS_PEDIDO, { clicavel: true })}</section>`;
  conteudo.querySelectorAll("[data-vista]").forEach((b) => (b.onclick = () => { f.vista = b.dataset.vista; vistaPedidos(); }));
  $("estado").onchange = (e) => { f.estado = e.target.value; vistaPedidos(); };
  let t;
  $("pesquisa").oninput = (e) => { clearTimeout(t); t = setTimeout(async () => { f.q = e.target.value; await vistaPedidos(); const p = $("pesquisa"); p.focus(); p.setSelectionRange(p.value.length, p.value.length); }, 300); };
}

// ---------- novo pedido ----------
async function vistaNovo() {
  const [catalogo, utilizadores] = await Promise.all([api("/api/catalogo?activo=true"), carregar("utilizadores", "/api/utilizadores?activo=true")]);
  const tipos = ["incidente", "equipamento", "licenca", "acesso", "informacao"];
  conteudo.innerHTML = `
    <h1>Novo pedido</h1>
    <form class="cartao" id="form-novo" style="max-width:760px;display:grid;gap:14px">
      <label>Para quem é o pedido?
        <select name="beneficiario_id">
          <option value="${eu.id}">Para mim (${esc(eu.nome)})</option>
          ${utilizadores.filter((u) => u.id !== eu.id).map((u) => `<option value="${u.id}">Em nome de ${esc(u.nome)}</option>`).join("")}
        </select></label>
      <label>O que precisas? *
        <select name="item_id" required><option value=""></option>
          ${tipos.map((t) => `<optgroup label="${esc(rot(t))}">${catalogo.filter((c) => c.tipo === t).map((c) =>
            `<option value="${c.id}">${esc(c.nome)}${c.requer_aprovacao ? " (requer aprovação da chefia)" : ""}</option>`).join("")}</optgroup>`).join("")}
        </select></label>
      <label>Assunto *<input name="titulo" required minlength="3" maxlength="200" placeholder="Resumo numa linha"></label>
      <label>Descrição *<textarea name="descricao" required minlength="3" rows="6" placeholder="O que se passa, desde quando, mensagens de erro, para que precisas..."></textarea></label>
      <label>Prioridade
        <select name="prioridade"><option value="">Definida pelo tipo de pedido</option>
          ${(staff() ? ["critica", "alta", "media", "baixa"] : ["alta", "media", "baixa"]).map((p) => `<option value="${p}">${rot(p)}</option>`).join("")}
        </select></label>
      <p class="erro" id="erro-novo"></p>
      <div><button class="primario">Submeter pedido</button> <button type="button" onclick="history.back()">Cancelar</button></div>
    </form>`;
  conteudo.querySelectorAll("#form-novo label").forEach((l) => { l.style.display = "flex"; l.style.flexDirection = "column"; l.style.gap = "4px"; l.style.fontSize = "13px"; l.style.color = "var(--suave)"; });
  $("form-novo").onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const corpo = { titulo: f.titulo.value, descricao: f.descricao.value, beneficiario_id: Number(f.beneficiario_id.value),
      item_id: Number(f.item_id.value), prioridade: f.prioridade.value || null };
    try {
      const r = await api("/api/pedidos", { method: "POST", body: JSON.stringify(corpo) });
      location.hash = `pedido/${r.id}`;
    } catch (err) { $("erro-novo").textContent = err.message; }
  };
}

// ---------- detalhe do pedido ----------
const ACCOES = {
  aprovar: { l: "Aprovar", primario: true, campos: [["motivo", "Observação (opcional)", "textarea"]] },
  recusar: { l: "Recusar", campos: [["motivo", "Motivo da recusa *", "textarea", true]] },
  assumir: { l: "Assumir", primario: true, directo: true },
  atribuir: { l: "Atribuir a técnico", campos: [["tecnico_id", "Técnico *", "tecnico", true]] },
  prioridade: { l: "Mudar prioridade", campos: [["prioridade", "Nova prioridade *", "prioridade", true]] },
  aguardar: { l: "Pedir informação", campos: [["motivo", "O que precisas do colaborador? *", "textarea", true]] },
  resolver: { l: "Resolver", primario: true, campos: [["motivo", "Solução aplicada *", "textarea", true]] },
  entregar_equipamento: { l: "Entregar equipamento", campos: [["equipamento_id", "Equipamento em stock *", "equipamento", true]] },
  atribuir_licenca: { l: "Atribuir licença", campos: [["licenca_id", "Licença *", "licenca", true]] },
  reabrir: { l: "Reabrir", campos: [["motivo", "Porque reabres? *", "textarea", true]] },
  fechar: { l: "Confirmar e fechar", primario: true, directo: true },
  cancelar: { l: "Cancelar pedido", campos: [["motivo", "Motivo (opcional)", "textarea"]] },
};
const EVENTOS = { atribuido: "Atribuído", aguarda_colaborador: "A aguardar colaborador", resolvido: "Resolvido", fechado: "Fechado", recusado: "Recusado", cancelado: "Cancelado" };

async function vistaPedido(id) {
  const p = await api(`/api/pedidos/${id}`);
  conteudo.innerHTML = `
    <div class="cabecalho">
      <div><h1>${esc(p.numero)} · ${esc(p.titulo)}</h1><div style="margin-top:6px">${etiqueta(p.estado)} ${etiqueta(p.prioridade)} ${etiqueta(p.sla)}</div></div>
      <div class="accoes-pedido">${p.accoes.map((a) => `<button data-accao="${a}" class="${ACCOES[a]?.primario ? "primario" : ""}">${esc(ACCOES[a]?.l ?? a)}</button>`).join("")}</div>
    </div>
    <div class="duas-colunas">
      <div>
        <section class="cartao" style="margin-bottom:16px">
          <div class="meta">
            <div><span>Para</span>${esc(p.beneficiario)}</div>
            <div><span>Criado por</span>${esc(p.criado_por)}</div>
            <div><span>Tipo</span>${esc(rot(p.tipo))}${p.item ? ` · ${esc(p.item)}` : ""}</div>
            <div><span>Técnico</span>${esc(p.tecnico || "Por atribuir")}</div>
            ${p.aprovador ? `<div><span>Aprovador</span>${esc(p.aprovador)}</div>` : ""}
            <div><span>Criado em</span>${dataHora(p.criado_em)}${p.origem === "email" ? " · por email" : ""}</div>
            <div><span>Prazo de resposta</span>${dataHora(p.prazo_resposta)}</div>
            <div><span>Prazo de resolução</span>${dataHora(p.prazo_resolucao)}</div>
          </div>
          <p class="descricao">${esc(p.descricao)}</p>
        </section>
        <section class="cartao">
          <h2>Comentários</h2>
          ${p.comentarios.map((c) => `<div class="comentario ${c.interno ? "interno" : ""}"><small>${esc(c.autor)} · ${dataHora(c.criado_em)}${c.interno ? " · nota interna DSI" : ""}</small><p>${esc(c.texto)}</p></div>`).join("") || '<p class="vazio">Sem comentários.</p>'}
          ${["fechado", "recusado", "cancelado"].includes(p.estado) ? "" : `
          <form id="form-comentario" style="display:grid;gap:8px;margin-top:8px">
            <textarea name="texto" rows="3" required placeholder="Escreve um comentário"></textarea>
            <div style="display:flex;gap:12px;align-items:center">
              ${staff() ? '<label style="display:flex;gap:6px;align-items:center;font-size:14px"><input type="checkbox" name="interno" style="width:auto"> Nota interna (só DSI)</label>' : ""}
              <button class="primario" style="margin-left:auto">Comentar</button>
            </div>
            <p class="erro" id="erro-comentario"></p>
          </form>`}
        </section>
      </div>
      <section class="cartao"><h2>Histórico</h2><ul class="linha-tempo">
        ${p.eventos.map((e) => `<li><strong>${esc(EVENTOS[e.accao] ?? rot(e.accao))}</strong>${e.detalhe ? `: ${esc(e.detalhe)}` : ""}<small>${esc(e.autor)} · ${dataHora(e.criado_em)}</small></li>`).join("")}
      </ul></section>
    </div>`;
  const fc = $("form-comentario");
  if (fc) fc.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api(`/api/pedidos/${id}/comentarios`, { method: "POST", body: JSON.stringify({ texto: fc.texto.value, interno: !!fc.interno?.checked }) });
      vistaPedido(id);
    } catch (err) { $("erro-comentario").textContent = err.message; }
  };
  conteudo.querySelectorAll("[data-accao]").forEach((b) => (b.onclick = () => abrirAccao(id, b.dataset.accao)));
}

async function abrirAccao(id, accao) {
  const def = ACCOES[accao];
  const executar = async (corpo) => api(`/api/pedidos/${id}/accoes/${accao}`, { method: "POST", body: JSON.stringify(corpo) });
  if (def.directo) {
    try { await executar({}); vistaPedido(id); } catch (err) { alert(err.message); }
    return;
  }
  const opcoes = {};
  for (const [, , t] of def.campos) {
    if (t === "tecnico") opcoes.tecnico = (await api("/api/utilizadores?activo=true")).filter((u) => u.perfil === "helpdesk" || u.perfil === "admin").map((u) => [u.id, u.nome]);
    if (t === "prioridade") opcoes.prioridade = ["critica", "alta", "media", "baixa"].map((p) => [p, rot(p)]);
    if (t === "equipamento") opcoes.equipamento = (await api("/api/equipamentos?estado=stock")).map((e) => [e.id, `${e.etiqueta} · ${e.tipo} ${e.marca || ""} ${e.modelo || ""}`]);
    if (t === "licenca") opcoes.licenca = (await api("/api/licencas")).map((l) => [l.id, `${l.produto} (${l.livres} livres)`]);
  }
  $("dialogo-titulo").textContent = def.l;
  $("dialogo-erro").textContent = "";
  $("btn-gravar").hidden = false;
  $("btn-gravar").textContent = def.l;
  $("dialogo-corpo").innerHTML = def.campos.map(([k, l, t, req]) => `<label class="largo">${esc(l)}${t === "textarea"
    ? `<textarea name="${k}" rows="4" ${req ? "required" : ""}></textarea>`
    : `<select name="${k}" ${req ? "required" : ""}><option value=""></option>${(opcoes[t] || []).map(([v, n]) => `<option value="${esc(v)}">${esc(n)}</option>`).join("")}</select>`}</label>`).join("");
  dialogo.showModal();
  formDialogo.onsubmit = async (e) => {
    if (e.submitter?.value !== "gravar") return;
    e.preventDefault();
    const corpo = {};
    for (const [k, , t] of def.campos) {
      const v = formDialogo.elements[k].value.trim();
      corpo[k] = v === "" ? null : (["tecnico", "equipamento", "licenca"].includes(t) ? Number(v) : v);
    }
    try { await executar(corpo); dialogo.close(); vistaPedido(id); } catch (err) { $("dialogo-erro").textContent = err.message; }
  };
}

// ---------- painel DSI ----------
async function vistaPainel() {
  const p = await api("/api/painel");
  const maxTec = Math.max(1, ...p.por_tecnico.map((x) => x.abertos));
  conteudo.innerHTML = `
    <h1>Painel DSI</h1>
    <div class="kpis">
      ${kpi("Pedidos em aberto", p.abertos, `${p.por_estado.em_aprovacao} em aprovação`)}
      ${kpi("Sem técnico", p.sem_tecnico)}
      ${kpi("Fora de prazo", p.sla_violado, `${p.sla_em_risco} em risco`)}
      ${kpi("Resolvidos em 7 dias", p.resolvidos_7d)}
      ${kpi("Equipamento em stock", p.equipamentos_por_estado.stock, `${p.equipamentos_por_estado.reparacao} em reparação`)}
    </div>
    <section class="cartao" style="margin-bottom:16px"><h2>Exigem atenção (fora de prazo ou em risco)</h2>${tabela(p.atencao, COLS_PEDIDO, { clicavel: true })}</section>
    <div class="grelha">
      <section class="cartao"><h2>Carga por técnico</h2>${p.por_tecnico.map((x) => barra(x.tecnico, x.abertos / maxTec, x.abertos)).join("") || '<p class="vazio">Sem pedidos em aberto.</p>'}
        <h2 style="margin-top:20px">Por estado</h2>${Object.entries(p.por_estado).map(([e, n]) => barra(rot(e), n / Math.max(1, p.abertos), n)).join("")}</section>
      <section class="cartao"><h2>Licenças</h2>${tabela(p.licencas, [["produto", "Produto"], ["quantidade", "Total", null, "num"], ["usadas", "Usadas", null, "num"],
        ["livres", "Livres", (v) => `<span class="etiqueta ${v === 0 ? "perigo" : v <= 2 ? "alerta" : "ok"}">${v}</span>`, "num"], ["renovacao_em", "Renovação", dataPT]])}
        <h2 style="margin-top:20px">Garantias a expirar (90 dias)</h2>${tabela(p.garantias_a_expirar, [["etiqueta", "Etiqueta"], ["tipo", "Tipo"], ["modelo", "Modelo"], ["garantia_ate", "Garantia até", dataPT]])}</section>
    </div>`;
}

// ---------- listas genéricas (equipamentos, administração) ----------
const ENTIDADES = {
  equipamentos: {
    titulo: "Equipamentos", singular: "equipamento",
    campos: [["etiqueta", "Etiqueta *", "text", true], ["tipo", "Tipo *", "select", true, ["Portátil", "Desktop", "Monitor", "Impressora", "Telemóvel", "Pen drive", "Periférico", "Rede", "Servidor", "Outro"]],
      ["marca", "Marca"], ["modelo", "Modelo"], ["numero_serie", "Nº de série"],
      ["estado", "Estado", "select", true, ["stock", "atribuido", "reparacao", "abatido"]], ["utilizador_id", "Atribuído a", "ref:utilizadores"],
      ["data_compra", "Data de compra", "date"], ["garantia_ate", "Garantia até", "date"], ["fornecedor", "Fornecedor"], ["notas", "Notas", "textarea"]],
    colunas: [["etiqueta", "Etiqueta"], ["tipo", "Tipo"], ["marca", "Marca"], ["modelo", "Modelo"], ["numero_serie", "Nº série"],
      ["estado", "Estado", etiqueta], ["utilizador_id", "Atribuído a", (v) => esc(nomeDe("utilizadores", v))], ["garantia_ate", "Garantia", dataPT]],
    refs: ["utilizadores"],
  },
  licencas: {
    titulo: "Licenças", singular: "licença",
    campos: [["produto", "Produto *", "text", true], ["fornecedor", "Fornecedor"], ["quantidade", "Quantidade *", "number", true],
      ["custo_anual", "Custo anual (Kz)", "number"], ["renovacao_em", "Renovação", "date"]],
  },
  utilizadores: {
    titulo: "Utilizadores", singular: "utilizador",
    campos: [["nome", "Nome *", "text", true], ["email", "Email *", "email", true], ["departamento_id", "Departamento", "ref:departamentos"],
      ["chefia_id", "Chefia directa (aprova os pedidos)", "ref:utilizadores"], ["perfil", "Perfil *", "select", true, ["colaborador", "chefia", "helpdesk", "admin"]],
      ["activo", "Activo", "checkbox"]],
    colunas: [["nome", "Nome"], ["email", "Email"], ["departamento_id", "Departamento", (v) => esc(nomeDe("departamentos", v))],
      ["chefia_id", "Chefia", (v) => esc(nomeDe("utilizadores", v))], ["perfil", "Perfil", rot], ["activo", "Activo", (v) => (v ? "Sim" : "Não")]],
    refs: ["departamentos", "utilizadores"],
  },
  catalogo: {
    titulo: "Catálogo de serviços", singular: "item",
    campos: [["nome", "Nome *", "text", true], ["tipo", "Tipo *", "select", true, ["incidente", "equipamento", "licenca", "acesso", "informacao"]],
      ["prioridade_padrao", "Prioridade por omissão", "select", true, ["critica", "alta", "media", "baixa"]],
      ["requer_aprovacao", "Requer aprovação da chefia", "checkbox"], ["activo", "Activo", "checkbox"]],
    colunas: [["nome", "Nome"], ["tipo", "Tipo", rot], ["prioridade_padrao", "Prioridade", etiqueta],
      ["requer_aprovacao", "Aprovação", (v) => (v ? "Sim" : "Não")], ["activo", "Activo", (v) => (v ? "Sim" : "Não")]],
  },
  departamentos: { titulo: "Departamentos", singular: "departamento", campos: [["nome", "Nome *", "text", true]], colunas: [["nome", "Nome"]] },
};

async function vistaLista(nome, alvo = conteudo, cabecalhoExtra = "") {
  const ent = ENTIDADES[nome];
  await Promise.all((ent.refs || []).map((r) => carregar(r)));
  const linhas = await api(`/api/${nome}?limit=2000`);
  alvo.innerHTML = `${cabecalhoExtra}
    <div class="cabecalho"><h1>${ent.titulo}</h1><button class="primario" id="novo-${nome}">Novo ${ent.singular}</button></div>
    <div class="barra"><input type="search" id="filtro-${nome}" placeholder="Filtrar..."></div>
    <section class="cartao" id="tabela-${nome}">${tabela(linhas, ent.colunas, { accoes: true })}</section>`;
  const redesenhar = () => vistaLista(nome, alvo, cabecalhoExtra);
  $(`novo-${nome}`).onclick = () => abrirFormulario(nome, null, redesenhar);
  const ligar = () => alvo.querySelectorAll("[data-editar]").forEach((b) => (b.onclick = () => abrirFormulario(nome, linhas.find((x) => x.id === Number(b.dataset.editar)), redesenhar)));
  ligar();
  $(`filtro-${nome}`).oninput = (e) => {
    const t = e.target.value.toLowerCase();
    const filtradas = linhas.filter((o) => ent.colunas.some(([k, , f]) => String(f ? f(o[k], o) : o[k] ?? "").toLowerCase().includes(t)));
    $(`tabela-${nome}`).innerHTML = tabela(filtradas, ent.colunas, { accoes: true });
    ligar();
  };
}

const dialogo = $("dialogo"), formDialogo = $("form-dialogo");
function abrirFormulario(nome, obj, aoGravar) {
  const ent = ENTIDADES[nome];
  $("dialogo-titulo").textContent = `${obj ? "Editar" : "Novo"} ${ent.singular}`;
  $("dialogo-erro").textContent = "";
  $("btn-gravar").hidden = false;
  $("btn-gravar").textContent = "Gravar";
  $("dialogo-corpo").innerHTML = ent.campos.map(([k, l, t = "text", req, opcoes]) => {
    const v = obj?.[k] ?? (t === "checkbox" && !obj ? true : "");
    let input;
    if (t === "select") input = `<select name="${k}" ${req ? "required" : ""}>${req ? "" : '<option value=""></option>'}${opcoes.map((o) => `<option value="${esc(o)}" ${o === v ? "selected" : ""}>${esc(rot(o))}</option>`).join("")}</select>`;
    else if (t.startsWith("ref:")) input = `<select name="${k}"><option value=""></option>${(cache[t.slice(4)] || []).filter((o) => o.id !== obj?.id).map((o) => `<option value="${o.id}" ${o.id === v ? "selected" : ""}>${esc(o.nome)}</option>`).join("")}</select>`;
    else if (t === "textarea") input = `<textarea name="${k}" rows="3">${esc(v)}</textarea>`;
    else if (t === "checkbox") input = `<input type="checkbox" name="${k}" style="width:auto" ${v ? "checked" : ""}>`;
    else input = `<input type="${t}" name="${k}" value="${esc(v)}" ${t === "number" ? 'step="any" min="0"' : ""} ${req ? "required" : ""}>`;
    return `<label class="${t === "textarea" ? "largo" : ""}">${esc(l)}${input}</label>`;
  }).join("");
  dialogo.showModal();
  formDialogo.onsubmit = async (e) => {
    if (e.submitter?.value !== "gravar") return;
    e.preventDefault();
    const dados = {};
    for (const [k, , t = "text"] of ent.campos) {
      const el = formDialogo.elements[k];
      let v = t === "checkbox" ? el.checked : el.value.trim();
      if (v === "") v = null;
      else if (t === "number" || t.startsWith("ref:")) v = Number(v);
      if (v !== null || obj) dados[k] = v;
    }
    try {
      await api(obj ? `/api/${nome}/${obj.id}` : `/api/${nome}`, { method: obj ? "PATCH" : "POST", body: JSON.stringify(dados) });
      dialogo.close();
      aoGravar();
    } catch (err) { $("dialogo-erro").textContent = err.message; }
  };
}

// ---------- licenças ----------
async function vistaLicencas() {
  const linhas = await api("/api/licencas");
  const admin = eu.perfil === "admin";
  conteudo.innerHTML = `
    <div class="cabecalho"><h1>Licenças</h1>${admin ? '<button class="primario" id="nova-licenca">Nova licença</button>' : ""}</div>
    <section class="cartao">${tabela(linhas, [["produto", "Produto", (v, o) => `<button class="ligacao" data-lic="${o.id}">${esc(v)}</button>`], ["fornecedor", "Fornecedor"],
      ["quantidade", "Total", null, "num"], ["usadas", "Usadas", null, "num"],
      ["livres", "Livres", (v) => `<span class="etiqueta ${v === 0 ? "perigo" : v <= 2 ? "alerta" : "ok"}">${v}</span>`, "num"],
      ["custo_anual", "Custo anual", kz, "num"], ["renovacao_em", "Renovação", dataPT]], { accoes: admin })}</section>`;
  if (admin) {
    $("nova-licenca").onclick = () => abrirFormulario("licencas", null, vistaLicencas);
    conteudo.querySelectorAll("[data-editar]").forEach((b) => (b.onclick = () => abrirFormulario("licencas", linhas.find((x) => x.id === Number(b.dataset.editar)), vistaLicencas)));
  }
  conteudo.querySelectorAll("[data-lic]").forEach((b) => (b.onclick = () => verAtribuicoes(linhas.find((x) => x.id === Number(b.dataset.lic)))));
}

async function verAtribuicoes(lic) {
  const at = await api(`/api/licencas/${lic.id}/atribuicoes`);
  $("dialogo-titulo").textContent = `${lic.produto}: ${at.length} de ${lic.quantidade} atribuídas`;
  $("dialogo-erro").textContent = "";
  $("btn-gravar").hidden = true;
  formDialogo.onsubmit = null;
  $("dialogo-corpo").innerHTML = `<div class="largo">${tabela(at, [["utilizador", "Utilizador"], ["atribuida_em", "Desde", dataPT],
    ["utilizador_id", "", (v) => `<button type="button" data-remover="${v}">Retirar</button>`]])}
    <p class="vazio">Novas atribuições fazem-se a partir de um pedido, para ficar registado quem pediu e quem aprovou.</p></div>`;
  $("dialogo-corpo").querySelectorAll("[data-remover]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Retirar esta licença ao utilizador?")) return;
    try { await api(`/api/licencas/${lic.id}/atribuicoes/${b.dataset.remover}`, { method: "DELETE" }); dialogo.close(); await vistaLicencas(); }
    catch (err) { $("dialogo-erro").textContent = err.message; }
  }));
  if (!dialogo.open) dialogo.showModal();
}

// ---------- administração ----------
async function vistaAdmin(sub) {
  const abas = [["utilizadores", "Utilizadores"], ["catalogo", "Catálogo"], ["departamentos", "Departamentos"], ["integracoes", "Integrações"]];
  const cab = `<div class="abas">${abas.map(([k, l]) => `<button onclick="location.hash='admin/${k}'" class="${sub === k ? "activo" : ""}">${l}</button>`).join("")}</div>`;
  if (sub === "integracoes") return vistaIntegracoes(cab);
  await vistaLista(ENTIDADES[sub] ? sub : "utilizadores", conteudo, cab);
}

async function vistaIntegracoes(cab) {
  const [e, ns] = await Promise.all([api("/api/admin/estado"), api("/api/admin/notificacoes")]);
  const sim = (v) => (v ? '<span class="etiqueta ok">Sim</span>' : '<span class="etiqueta alerta">Não</span>');
  conteudo.innerHTML = `${cab}
    <h1>Integrações Microsoft 365</h1>
    <section class="cartao" style="margin-bottom:16px">
      <div class="meta">
        <div><span>Início de sessão</span>${e.modo_autenticacao === "entra" ? "Conta Microsoft (Entra ID)" : "Demonstração (sem palavra-passe)"}</div>
        <div><span>Microsoft Graph configurado</span>${sim(e.graph_configurado)}</div>
        <div><span>Caixa do Helpdesk</span>${esc(e.caixa_helpdesk || "Não definida")}</div>
        <div><span>Pedidos por email</span>${sim(e.leitura_caixa)}</div>
        <div><span>Último ciclo</span>${dataHora(e.ultimo_ciclo) || "Ainda não correu"}</div>
        <div><span>Última sincronização</span>${dataHora(e.ultima_sincronizacao) || "Ainda não correu"}</div>
      </div>
      <div class="accoes-pedido" style="margin-top:16px">
        <button id="btn-ciclo">Correr tarefas agora</button>
        <button id="btn-sync" ${e.graph_configurado ? "" : "disabled"}>Sincronizar com o Entra ID</button>
      </div>
      <pre id="resultado" style="white-space:pre-wrap;font-size:13px;color:var(--suave)">${e.resultados && Object.keys(e.resultados).length ? esc(JSON.stringify(e.resultados, null, 2)) : ""}</pre>
    </section>
    <section class="cartao"><h2>Emails enviados pelo portal (últimos 200)</h2>
      ${tabela(ns, [["criado_em", "Data", dataHora], ["para", "Para"], ["assunto", "Assunto"],
        ["estado", "Estado", (v) => `<span class="etiqueta ${v === "enviada" ? "ok" : v === "erro" ? "perigo" : "alerta"}">${esc(v)}</span>`],
        ["erro", "Erro", (v) => esc((v || "").slice(0, 80))]])}
    </section>`;
  const correr = async (url) => {
    $("resultado").textContent = "A correr...";
    try { await api(url, { method: "POST" }); vistaIntegracoes(cab); } catch (err) { $("resultado").textContent = err.message; }
  };
  $("btn-ciclo").onclick = () => correr("/api/admin/ciclo");
  $("btn-sync").onclick = () => correr("/api/admin/ciclo?sincronizar=true");
}

arrancar();
