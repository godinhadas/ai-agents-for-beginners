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
  acesso: "Acessos", anywhere: "Anywhere", equipamento: "Equipamento e gadgets", licenca: "Licenças e software",
  intervencao: "Intervenção técnica", outro: "Outros",
  colaborador: "Colaborador", helpdesk: "Helpdesk", admin: "Administrador DSI",
  stock: "Em stock", atribuido: "Atribuído", reparacao: "Em reparação", abatido: "Abatido",
  ok: "No prazo", em_risco: "Em risco", violado: "Fora de prazo", cumprido: "Cumprido", pausado: "Pausado", "n/a": "",
  criado: "Pedido criado", aguarda_aprovacao: "A aguardar aprovação da DSI", aprovado: "Aprovado",
  prioridade: "Prioridade alterada", reaberto: "Reaberto", equipamento_entregue: "Equipamento entregue",
  licenca_atribuida: "Licença atribuída", resposta_colaborador: "Resposta do colaborador",
};
const rot = (v) => ROTULOS[v] ?? v;
const CLASSE = { em_aprovacao: "alerta", aguarda_colaborador: "alerta", resolvido: "ok", fechado: "", recusado: "perigo",
  cancelado: "", critica: "perigo", alta: "alerta", violado: "perigo", em_risco: "alerta", ok: "ok", cumprido: "ok",
  stock: "ok", reparacao: "alerta", abatido: "perigo", novo: "marca", em_curso: "marca" };
const etiqueta = (v) => (v && rot(v) ? `<span class="etiqueta ${CLASSE[v] ?? ""}">${esc(rot(v))}</span>` : "");
const TIPOS = ["acesso", "anywhere", "equipamento", "licenca", "intervencao", "outro"];

// Ícones de traço simples (24x24), desenhados para o portal.
const ICONES = {
  cadeado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  utilizador: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  pasta: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  globo: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  email: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  chave: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3M15 8l2 2"/>',
  alerta: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  escudo: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  portatil: '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/>',
  rato: '<rect x="7" y="3" width="10" height="18" rx="5"/><path d="M12 7v3"/>',
  pen: '<rect x="8" y="9" width="8" height="12" rx="1.5"/><path d="M10 9V4h4v5M11 6h.01M13 6h.01"/>',
  telemovel: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
  nuvem: '<path d="M7 18a5 5 0 0 1-.6-10A6 6 0 0 1 18 9a4.5 4.5 0 0 1-.5 9z"/>',
  descarregar: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
  insignia: '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 7 5-3 5 3-1.5-7"/>',
  ferramenta: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
  definicoes: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
  wifi: '<path d="M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01"/>',
  impressora: '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
  ajuda: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 1-1 1.7M12 17h.01"/>',
  caixa: '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  sair: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H3"/>',
  microsoft: '<path d="M3 3h8.5v8.5H3zM12.5 3H21v8.5h-8.5zM3 12.5h8.5V21H3zM12.5 12.5H21V21h-8.5z"/>',
};
const icone = (nome) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nome] || ICONES.caixa}</svg>`;
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

let cfg = { empresa: "MHAIS", nome: "Gestor de Pedidos DSI", direccao: "", logo: "/static/marca/logo.png", logo_cabecalho: "/static/marca/logo-branco.png" };
async function aplicarMarca() {
  try { cfg = await api("/api/config"); } catch { /* mantém os valores por omissão */ }
  $("logo").src = cfg.logo_cabecalho || cfg.logo;
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
  document.body.classList.add("ecra-entrada");
  const { modo } = await api("/api/auth/modo");
  const topo = `<img class="logo-grande" src="${esc(cfg.logo)}" alt="${esc(cfg.empresa)}"><h1>${esc(cfg.nome)}</h1>
    <p>Acessos, Anywhere, equipamento, licenças e intervenções técnicas, num só sítio.</p>`;
  if (modo !== "dev") {
    conteudo.innerHTML = `<section class="cartao login">${topo}
      <button class="primario entrar" onclick="location.href='/auth/login'">${icone("microsoft")} Entrar com a conta Microsoft</button>
      <div class="contactos">Sem acesso?${contactosHTML("<br>")}</div></section>`;
    return;
  }
  const us = await api("/api/auth/utilizadores-demo");
  conteudo.innerHTML = `<section class="cartao login">${topo}
    <p class="vazio">Modo de teste, sem login Microsoft. Escolhe o utilizador:</p>
    <div class="lista">${us.map((u) => `<button data-login="${u.id}"><span>${esc(u.nome)}</span><span class="etiqueta marca">${esc(rot(u.perfil))}</span></button>`).join("")}</div>
  </section>`;
  conteudo.querySelectorAll("[data-login]").forEach((b) => (b.onclick = async () => {
    await api("/api/auth/login", { method: "POST", body: JSON.stringify({ utilizador_id: Number(b.dataset.login) }) });
    location.hash = "inicio";
    arrancar();
  }));
}

function desenharNav() {
  document.body.classList.remove("ecra-entrada");
  const itens = [["inicio", "Início"], ["pedidos", staff() ? "Pedidos" : "Os meus pedidos"]];
  if (staff()) itens.push(["painel", "Painel"]);
  if (staff() && cfg.inventario) itens.push(["equipamentos", "Equipamentos"], ["licencas", "Licenças"]);
  if (eu.perfil === "admin") itens.push(["admin", "Administração"]);
  nav.innerHTML = itens.map(([id, l]) => `<button data-sec="${id}">${l}</button>`).join("");
  $("utilizador").innerHTML = `<span>${esc(eu.nome)}</span><button id="sair" class="botao" title="Sair">${icone("sair")} Sair</button>`;
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
  nav.querySelectorAll("button").forEach((b) => b.classList.toggle("activo", b.dataset.sec === (sec === "pedido" ? "pedidos" : sec === "novo" ? "inicio" : sec)));
  try {
    const vistas = { inicio: vistaInicio, pedidos: vistaPedidos, pedido: () => vistaPedido(Number(arg)), novo: () => vistaNovo(Number(arg)),
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
let catInicio = "acesso";
async function vistaInicio() {
  const [d, catalogo] = await Promise.all([api("/api/inicio"), api("/api/catalogo?activo=true")]);
  const cats = TIPOS.filter((t) => catalogo.some((c) => c.tipo === t));
  if (!cats.includes(catInicio)) catInicio = cats[0];
  const meus = d.meus_pedidos.slice(0, 5);
  conteudo.innerHTML = `
    <div class="saudacao">
      <div><h1>Olá, ${esc(eu.nome.split(" ")[0])}</h1><p>O que precisas hoje?</p></div>
      <input type="search" id="procurar" placeholder="Procurar: monitor, VPN, Anywhere, impressora..." autocomplete="off">
    </div>
    ${d.para_aprovar.length ? `<section class="cartao aviso-aprovacao"><h2>${icone("alerta")} ${d.para_aprovar.length} pedido(s) à espera da tua aprovação</h2>${tabela(d.para_aprovar, COLS_PEDIDO, { clicavel: true })}</section>` : ""}
    <section class="cartao catalogo">
      <div class="abas" id="cats">${cats.map((t) => `<button data-cat="${t}" class="${t === catInicio ? "activo" : ""}">${esc(rot(t))}</button>`).join("")}</div>
      <div class="mosaicos" id="itens"></div>
    </section>
    ${meus.length ? `<section class="cartao" style="margin-top:20px"><div class="cabecalho" style="margin-bottom:8px"><h2 style="margin:0">Os meus pedidos em curso</h2><button class="ligacao" onclick="location.hash='pedidos'">Ver todos</button></div>${tabela(meus, COLS_PEDIDO, { clicavel: true })}</section>` : ""}`;
  const desenhar = () => {
    const q = $("procurar").value.trim().toLowerCase();
    const lista = q ? catalogo.filter((c) => `${c.nome} ${c.descricao || ""} ${rot(c.tipo)}`.toLowerCase().includes(q))
                    : catalogo.filter((c) => c.tipo === catInicio);
    $("cats").style.display = q ? "none" : "";
    $("itens").innerHTML = lista.map((c) => `
      <button class="mosaico" data-item="${c.id}" title="${esc(c.descricao || "")}">
        <span class="icone">${icone(c.icone)}</span>
        <span class="texto"><strong>${esc(c.nome)}</strong><small>${esc(c.descricao || "")}</small>
          ${c.requer_aprovacao ? '<span class="aprov">Requer aprovação DSI</span>' : ""}</span>
      </button>`).join("") || '<p class="vazio">Nada encontrado. Usa "Outro pedido" na categoria Outros.</p>';
    $("itens").querySelectorAll("[data-item]").forEach((b) => (b.onclick = () => (location.hash = `novo/${b.dataset.item}`)));
  };
  $("cats").querySelectorAll("[data-cat]").forEach((b) => (b.onclick = () => {
    catInicio = b.dataset.cat;
    $("cats").querySelectorAll("button").forEach((x) => x.classList.toggle("activo", x === b));
    desenhar();
  }));
  $("procurar").oninput = desenhar;
  desenhar();
}

// ---------- lista de pedidos ----------
let filtroPedidos = null;
async function vistaPedidos() {
  const vistas = [["meus", "Os meus"]];
  if (eu.perfil === "admin") vistas.push(["aprovar", "Para aprovar"]);
  if (staff()) vistas.push(["atribuidos", "Atribuídos a mim"], ["todos", "Todos"]);
  filtroPedidos ??= { vista: staff() ? "todos" : "meus", estado: "abertos", q: "" };
  const f = filtroPedidos;
  const params = new URLSearchParams({ vista: f.vista, estado: f.estado, q: f.q });
  const linhas = await api(`/api/pedidos?${params}`);
  conteudo.innerHTML = `
    <div class="cabecalho"><h1>${staff() ? "Pedidos" : "Os meus pedidos"}</h1><button class="primario" onclick="location.hash='inicio'">${icone("mais")} Novo pedido</button></div>
    ${vistas.length > 1 ? `<div class="abas">${vistas.map(([v, l]) => `<button data-vista="${v}" class="${f.vista === v ? "activo" : ""}">${l}</button>`).join("")}</div>` : ""}
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
async function vistaNovo(itemId) {
  const [catalogo, utilizadores] = await Promise.all([api("/api/catalogo?activo=true"), carregar("utilizadores", "/api/utilizadores?activo=true")]);
  const item = catalogo.find((c) => c.id === itemId);
  if (!item) { location.hash = "inicio"; return; }
  conteudo.innerHTML = `
    <form class="cartao" id="form-novo" style="max-width:760px;margin:0 auto;display:grid;gap:16px">
      <div class="item-escolhido">
        <span class="icone">${icone(item.icone)}</span>
        <div style="flex:1"><strong>${esc(item.nome)}</strong><br><small style="color:var(--suave)">${esc(rot(item.tipo))}${item.requer_aprovacao ? " · requer aprovação da DSI" : ""}</small></div>
        <button type="button" class="ligacao" onclick="location.hash='inicio'">Mudar</button>
      </div>
      <label class="campo">Para quem é?
        <select name="beneficiario_id">
          <option value="${eu.id}">Para mim</option>
          ${utilizadores.filter((u) => u.id !== eu.id).map((u) => `<option value="${u.id}">Em nome de ${esc(u.nome)}</option>`).join("")}
        </select></label>
      <label class="campo">Assunto *<input name="titulo" required minlength="3" maxlength="200" value="${esc(item.nome)}"></label>
      <label class="campo">Descreve o pedido *<textarea name="descricao" required minlength="3" rows="6" placeholder="O que precisas ou o que se passa, desde quando, mensagens de erro, para que é necessário..."></textarea></label>
      <label class="campo">Urgência
        <select name="prioridade"><option value="">Normal (${esc(rot(item.prioridade_padrao))})</option>
          ${(staff() ? ["critica", "alta", "media", "baixa"] : ["alta", "media", "baixa"]).map((p) => `<option value="${p}">${rot(p)}</option>`).join("")}
        </select></label>
      <p class="erro" id="erro-novo"></p>
      <div style="display:flex;gap:8px"><button class="primario">Enviar pedido</button><button type="button" onclick="location.hash='inicio'">Cancelar</button></div>
    </form>`;
  $("form-novo").onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const corpo = { titulo: f.titulo.value, descricao: f.descricao.value, beneficiario_id: Number(f.beneficiario_id.value),
      item_id: item.id, prioridade: f.prioridade.value || null };
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
  const maxTipo = Math.max(1, ...Object.values(p.por_tipo));
  const inv = cfg.inventario;
  conteudo.innerHTML = `
    <h1>Painel DSI</h1>
    <div class="kpis">
      ${kpi("Pedidos em aberto", p.abertos, `${p.por_estado.em_aprovacao} em aprovação`)}
      ${kpi("Sem técnico", p.sem_tecnico)}
      ${kpi("Fora de prazo", p.sla_violado, `${p.sla_em_risco} em risco`)}
      ${kpi("Resolvidos em 7 dias", p.resolvidos_7d)}
      ${inv ? kpi("Equipamento em stock", p.equipamentos_por_estado.stock, `${p.equipamentos_por_estado.reparacao} em reparação`) : ""}
    </div>
    <section class="cartao" style="margin-bottom:16px"><h2>Exigem atenção (fora de prazo ou em risco)</h2>${tabela(p.atencao, COLS_PEDIDO, { clicavel: true })}</section>
    <div class="grelha">
      <section class="cartao"><h2>Carga por técnico</h2>${p.por_tecnico.map((x) => barra(x.tecnico, x.abertos / maxTec, x.abertos)).join("") || '<p class="vazio">Sem pedidos em aberto.</p>'}
        <h2 style="margin-top:20px">Por estado</h2>${Object.entries(p.por_estado).map(([e, n]) => barra(rot(e), n / Math.max(1, p.abertos), n)).join("")}</section>
      <section class="cartao"><h2>Em aberto por categoria</h2>${Object.entries(p.por_tipo).map(([t, n]) => barra(rot(t), n / maxTipo, n)).join("")}
      ${inv ? `<h2 style="margin-top:20px">Licenças</h2>${tabela(p.licencas, [["produto", "Produto"], ["quantidade", "Total", null, "num"], ["usadas", "Usadas", null, "num"],
        ["livres", "Livres", (v) => `<span class="etiqueta ${v === 0 ? "perigo" : v <= 2 ? "alerta" : "ok"}">${v}</span>`, "num"], ["renovacao_em", "Renovação", dataPT]])}` : ""}</section>
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
      ["perfil", "Perfil *", "select", true, ["colaborador", "helpdesk", "admin"]],
      ["activo", "Activo", "checkbox"]],
    colunas: [["nome", "Nome"], ["email", "Email"], ["departamento_id", "Departamento", (v) => esc(nomeDe("departamentos", v))],
      ["perfil", "Perfil", rot], ["activo", "Activo", (v) => (v ? "Sim" : "Não")]],
    refs: ["departamentos", "utilizadores"],
  },
  catalogo: {
    titulo: "Catálogo de serviços", singular: "item",
    campos: [["nome", "Nome *", "text", true], ["tipo", "Categoria *", "select", true, ["acesso", "anywhere", "equipamento", "licenca", "intervencao", "outro"]],
      ["descricao", "Descrição curta (aparece no mosaico)"], ["icone", "Ícone", "select", true, Object.keys(ICONES)], ["ordem", "Ordem", "number"],
      ["prioridade_padrao", "Prioridade por omissão", "select", true, ["critica", "alta", "media", "baixa"]],
      ["requer_aprovacao", "Requer aprovação da DSI", "checkbox"], ["activo", "Activo", "checkbox"]],
    colunas: [["icone", "", (v) => `<span style="display:inline-block;width:20px;height:20px;color:var(--primaria)">${icone(v)}</span>`],
      ["nome", "Nome"], ["tipo", "Categoria", rot], ["prioridade_padrao", "Prioridade", etiqueta],
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
