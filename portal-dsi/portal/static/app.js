"use strict";

/* =====================================================================
   Gestor de Pedidos DSI · interface
   Convenções de interface (iguais em todas as páginas):
   - cabeçalho de página: título, subtítulo e acção principal à direita;
   - filtros: separadores (vista) + estado + pesquisa, sempre na mesma ordem;
   - botões: primário (roxo) para a acção principal, contorno para as restantes,
     vermelho para recusar/cancelar; confirmações e mensagens dentro do portal.
   ===================================================================== */

// ---------- utilitários ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const kz = (v) => (v == null ? "" : new Intl.NumberFormat("pt-AO", { maximumFractionDigits: 0 }).format(v) + " Kz");
const dataPT = (v) => (v ? new Date(v.length === 10 ? v + "T00:00:00" : v).toLocaleDateString("pt-PT") : "");
const dataHora = (v) => (v ? new Date(v).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" }) : "");
const semAcentos = (t) => String(t).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const $ = (id) => document.getElementById(id);

const ROTULOS = {
  em_aprovacao: "Em aprovação", novo: "Registado", em_curso: "Em tratamento", aguarda_colaborador: "Aguarda resposta",
  resolvido: "Resolvido", fechado: "Fechado", recusado: "Recusado", cancelado: "Cancelado",
  critica: "Crítica", alta: "Urgente", media: "Normal", baixa: "Baixa",
  acesso: "Acessos", anywhere: "Anywhere", equipamento: "Equipamento e gadgets", licenca: "Licenças e software",
  intervencao: "Intervenção técnica", outro: "Outros",
  colaborador: "Colaborador", helpdesk: "Helpdesk", admin: "Administrador DSI",
  stock: "Em stock", atribuido: "Atribuído", reparacao: "Em reparação", abatido: "Abatido",
  ok: "No prazo", em_risco: "Em risco", violado: "Fora de prazo", cumprido: "Cumprido", pausado: "Em pausa", "n/a": "",
  desbloquear_ad: "Desbloquear conta no Active Directory",
};
const rot = (v) => ROTULOS[v] ?? v;
const CLASSE = { em_aprovacao: "alerta", aguarda_colaborador: "alerta", resolvido: "ok", fechado: "", recusado: "perigo",
  cancelado: "", critica: "perigo", alta: "alerta", violado: "perigo", em_risco: "alerta", ok: "ok", cumprido: "ok",
  stock: "ok", reparacao: "alerta", abatido: "perigo", novo: "marca", em_curso: "marca" };
const etiqueta = (v) => (v && rot(v) ? `<span class="etiqueta ${CLASSE[v] ?? ""}">${esc(rot(v))}</span>` : "");
const simNao = (v) => (v ? '<span class="etiqueta ok">Sim</span>' : '<span class="etiqueta">Não</span>');
const TIPOS = ["acesso", "anywhere", "equipamento", "licenca", "intervencao", "outro"];
const ICONE_TIPO = { acesso: "chave", anywhere: "escudo", equipamento: "portatil", licenca: "descarregar", intervencao: "ferramenta", outro: "ajuda" };

// Ícones de traço simples (24x24), desenhados para o portal.
const ICONES = {
  cadeado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  utilizador: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  utilizadores: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 13.5a7 7 0 0 1 4 6.5"/>',
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
  lista: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  painel: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  voltar: '<path d="M15 18l-6-6 6-6"/>',
  lapis: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>',
  certo: '<path d="M5 12l5 5L20 7"/>',
  cruz: '<path d="M6 6l12 12M18 6 6 18"/>',
  relogio: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mensagem: '<path d="M4 5h16v11H8l-4 4z"/>',
  pessoa_mais: '<circle cx="10" cy="8" r="4"/><path d="M3 21a7 7 0 0 1 14 0M19 8v6M16 11h6"/>',
  setas: '<path d="M7 4v16M7 4 3 8M7 4l4 4M17 20V4M17 20l-4-4M17 20l4-4"/>',
  lixo: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  sino: '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
  cima: '<path d="M6 15l6-6 6 6"/>', baixo: '<path d="M6 9l6 6 6-6"/>',
};
// Ícones disponíveis para os itens do catálogo (os restantes são da própria interface).
const ICONES_CATALOGO = ["cadeado", "utilizador", "utilizadores", "pasta", "globo", "email", "chave", "alerta", "escudo", "portatil",
  "monitor", "rato", "pen", "telemovel", "nuvem", "descarregar", "insignia", "ferramenta", "definicoes", "wifi", "impressora", "ajuda", "caixa", "mensagem", "relogio"];
const icone = (nome) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nome] || ICONES.caixa}</svg>`;

// ---------- comunicação com o servidor ----------
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
    throw new Error(msg || "Ocorreu um erro inesperado. Tenta de novo ou contacta a DSI.");
  }
  return corpo;
}

let eu = null;
const staff = () => eu && (eu.perfil === "helpdesk" || eu.perfil === "admin");
const admin = () => eu && eu.perfil === "admin";
const cache = {};
async function carregar(ref, url) { cache[ref] = await api(url || `/api/${ref}?limit=2000`); return cache[ref]; }
const nomeDe = (ref, id) => { const o = (cache[ref] || []).find((x) => x.id === id); return o ? (o.nome ?? o.produto ?? o.etiqueta) : ""; };

// ---------- componentes comuns ----------
const nav = $("nav"), conteudo = $("conteudo"), dialogo = $("dialogo"), formDialogo = $("form-dialogo");

function cabecalhoPagina(titulo, subtitulo = "", accoes = "") {
  return `<div class="pagina-cab"><div><h1>${esc(titulo)}</h1>${subtitulo ? `<p>${esc(subtitulo)}</p>` : ""}</div>${accoes ? `<div class="pagina-accoes">${accoes}</div>` : ""}</div>`;
}
const botao = (id, texto, { classe = "", ic = "" } = {}) => `<button id="${id}" class="${classe}">${ic ? icone(ic) : ""}${esc(texto)}</button>`;
const vazio = (texto, ic = "caixa", accao = "") => `<div class="estado-vazio">${icone(ic)}<p>${esc(texto)}</p>${accao}</div>`;

function aviso(texto, tipo = "ok") {
  const el = document.createElement("div");
  el.className = `aviso ${tipo}`;
  el.innerHTML = `${icone(tipo === "ok" ? "certo" : tipo === "info" ? "sino" : "alerta")}<span>${esc(texto)}</span>`;
  $("avisos").appendChild(el);
  setTimeout(() => el.classList.add("sair"), 3200);
  setTimeout(() => el.remove(), 3700);
}

// Diálogo único do portal: formulários, confirmações e listas.
function abrirDialogo({ titulo, corpo, botaoTexto = "Gravar", perigo = false, aoGravar = null }) {
  $("dialogo-titulo").textContent = titulo;
  $("dialogo-erro").textContent = "";
  $("dialogo-corpo").innerHTML = corpo;
  const b = $("btn-gravar");
  b.hidden = !aoGravar;
  b.textContent = botaoTexto;
  b.className = perigo ? "perigo-cheio" : "primario";
  formDialogo.onsubmit = async (e) => {
    if (e.submitter?.value !== "gravar") return;
    e.preventDefault();
    b.disabled = true;
    try { await aoGravar(); dialogo.close(); } catch (err) { $("dialogo-erro").textContent = err.message; } finally { b.disabled = false; }
  };
  if (!dialogo.open) dialogo.showModal();
  setTimeout(() => dialogo.querySelector("#dialogo-corpo input, #dialogo-corpo textarea, #dialogo-corpo select")?.focus(), 30);
}
const confirmar = (titulo, texto, botaoTexto = "Confirmar", perigo = false) => new Promise((ok) => {
  abrirDialogo({ titulo, corpo: `<p class="largo" style="margin:0">${esc(texto)}</p>`, botaoTexto, perigo, aoGravar: async () => ok(true) });
  dialogo.addEventListener("close", () => ok(false), { once: true });
});

function tabela(linhas, colunas, { editar = false, clicavel = false, vazioTexto = "Sem registos." } = {}) {
  if (!linhas.length) return vazio(vazioTexto);
  const cab = colunas.map(([, l, , c]) => `<th class="${c || ""}">${esc(l)}</th>`).join("") + (editar ? "<th></th>" : "");
  const corpo = linhas.map((o) => `<tr ${clicavel ? `data-pedido="${o.id}" class="clicavel"` : ""}>` + colunas.map(([k, , f, c]) =>
    `<td class="${c || ""}">${f ? f(o[k], o) : esc(o[k])}</td>`).join("") +
    (editar ? `<td><div class="acoes"><button class="pequeno" data-editar="${o.id}">${icone("lapis")}Editar</button></div></td>` : "") + "</tr>").join("");
  return `<div class="tabela"><table><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table></div>`;
}
const assuntoPedido = (v, o) => `<div class="assunto${o.novidade ? " por-ler" : ""}"><span class="mini-icone">${icone(ICONE_TIPO[o.tipo])}${o.novidade ? '<i class="ponto" title="Novidades por ler"></i>' : ""}</span><div><strong>${esc(o.numero)}</strong> ${esc(v)}${o.beneficiario !== eu.nome ? `<small>Para ${esc(o.beneficiario)}</small>` : ""}</div></div>`;
function colunasPedido() {
  const c = [["titulo", "Pedido", assuntoPedido], ["estado", "Estado", etiqueta]];
  if (staff()) c.push(["prioridade", "Urgência", (v) => (v === "alta" || v === "critica" ? etiqueta(v) : "")], ["tecnico", "Técnico", (v) => esc(v || "Por atribuir")]);
  c.push(["actualizado_em", "Actualizado", dataHora], ["prazo_resolucao", "Prazo", prazoCelula]);
  return c;
}
// Prazo de resolução (SLA) com o estado: no prazo, em risco, fora de prazo, cumprido.
function prazoCelula(v, o) {
  if (o.estado === "em_aprovacao") return '<span class="prazo"><small>Conta após aprovação</small></span>';
  if (["recusado", "cancelado"].includes(o.estado)) return "";
  const data = o.resolvido_em ? `Resolvido ${dataHora(o.resolvido_em)}` : `Até ${dataHora(v)}`;
  return `<span class="prazo">${etiqueta(o.sla)}<small>${esc(data)}</small></span>`;
}
const kpi = (r, v, nota = "", ic = "lista") => `<div class="cartao kpi"><span class="kpi-icone">${icone(ic)}</span><div><div class="rotulo">${esc(r)}</div><div class="valor">${esc(v)}</div><div class="nota">${esc(nota)}</div></div></div>`;
const barra = (r, frac, v) => `<div class="barra-h"><span>${esc(r)}</span><div class="trilho"><div class="enchimento" style="width:${(frac * 100).toFixed(1)}%"></div></div><span style="text-align:right">${esc(v)}</span></div>`;

// ---------- marca, sessão e navegação ----------
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

const paginaInicial = () => (admin() ? "painel" : staff() ? "pedidos" : "inicio");

async function arrancar() {
  if (!arrancar.feito) { arrancar.feito = true; await aplicarMarca(); }
  try { eu = await api("/api/eu"); } catch { eu = null; }
  if (!eu) return mostrarLogin();
  desenharNav();
  if (!location.hash) location.hash = paginaInicial(); else mostrar();
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
    location.hash = "";
    arrancar();
  }));
}

function itensNav() {
  const i = [];
  if (admin()) i.push(["painel", "Painel", "painel"]);
  if (staff()) i.push(["pedidos", "Fila de pedidos", "lista"]);
  i.push(["inicio", "Novo pedido", "mais"]);
  if (!staff()) i.push(["pedidos", "Os meus pedidos", "lista"]);
  if (eu.perfil === "helpdesk") i.push(["painel", "Painel", "painel"]);
  if (staff() && cfg.inventario) i.push(["equipamentos", "Equipamentos", "portatil"], ["licencas", "Licenças", "insignia"]);
  if (admin()) i.push(["admin", "Administração", "definicoes"]);
  return i;
}
function desenharNav() {
  document.body.classList.remove("ecra-entrada");
  nav.innerHTML = itensNav().map(([id, l, ic]) => `<button data-sec="${id}">${icone(ic)}<span>${l}</span><span class="contador" data-contador="${id}" hidden></span></button>`).join("");
  $("utilizador").innerHTML = `<div class="sino-caixa"><button id="sino" class="botao sino" title="Novidades">${icone("sino")}<span class="contador" id="sino-total" hidden></span></button><div id="sino-painel" class="sino-painel" hidden></div></div><span class="quem"><strong>${esc(eu.nome)}</strong><small>${esc(rot(eu.perfil))}</small></span><button id="sair" class="botao" title="Sair">${icone("sair")}<span>Sair</span></button>`;
  $("sair").onclick = async () => { await api("/api/auth/logout", { method: "POST" }); eu = null; location.hash = ""; mostrarLogin(); };
  $("sino").onclick = (e) => { e.stopPropagation(); alternarSino(); };
  novidadesVistas = null;
  actualizarNovidades();
}

// ---------- novidades (sino) ----------
// Verifica de 30 em 30 segundos; avisa dentro do portal e, se o browser permitir, com notificação do Windows.
let novidades = { total: 0, pedidos: [], itens: [] }, novidadesVistas = null;
async function actualizarNovidades() {
  if (!eu) return;
  try { novidades = await api("/api/novidades"); } catch { return; }
  const t = $("sino-total");
  if (t) { t.hidden = !novidades.total; t.textContent = novidades.total > 99 ? "99+" : novidades.total || ""; }
  document.title = `${novidades.total ? `(${novidades.total}) ` : ""}${cfg.nome} · ${cfg.empresa}`;
  const chaves = novidades.itens.map((i) => `${i.pedido_id}|${i.criado_em}|${i.texto}`);
  if (novidadesVistas) {
    const novas = novidades.itens.filter((i, k) => !novidadesVistas.has(chaves[k]));
    if (novas.length) avisarNovidades(novas);
  }
  novidadesVistas = new Set(chaves);
  if (!$("sino-painel")?.hidden) desenharSino();
}
function avisarNovidades(novas) {
  const [sec, arg] = location.hash.slice(1).split("/");
  const aberto = sec === "pedido" ? Number(arg) : null;
  const deOutros = novas.filter((i) => i.pedido_id !== aberto);
  if (aberto && novas.some((i) => i.pedido_id === aberto)) vistaPedido(aberto, { manterRascunho: true });
  if (!deOutros.length) return;
  const i = deOutros[0];
  const texto = deOutros.length === 1 ? `${i.numero}: ${i.tipo === "mensagem" ? `mensagem de ${i.autor}` : i.texto}` : `${deOutros.length} novidades nos teus pedidos`;
  aviso(texto, "info");
  if ("Notification" in window && Notification.permission === "granted" && document.hidden) {
    const n = new Notification(cfg.nome, { body: texto, icon: cfg.logo, tag: "gpd" });
    n.onclick = () => { window.focus(); location.hash = `pedido/${i.pedido_id}`; n.close(); };
  }
  actualizarContadores();
}
setInterval(actualizarNovidades, 30000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) actualizarNovidades(); });

function alternarSino() {
  const painel = $("sino-painel");
  painel.hidden = !painel.hidden;
  if (!painel.hidden) {
    desenharSino();
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
  }
}
function desenharSino() {
  const painel = $("sino-painel");
  painel.innerHTML = `<div class="sino-cab"><strong>Novidades</strong>${novidades.total ? '<button class="ligacao" id="sino-lidas">Marcar tudo como lido</button>' : ""}</div>
    ${novidades.itens.length ? `<ul>${novidades.itens.map((i) => `<li><button data-novidade="${i.pedido_id}">
      <span class="mini-icone">${icone(i.tipo === "mensagem" ? "mensagem" : "relogio")}</span>
      <span><strong>${esc(i.numero)}</strong> ${esc(i.titulo)}<small>${i.tipo === "mensagem" ? `<b>${esc(i.autor)}:</b> ` : ""}${esc(i.texto)}</small><small class="quando">${dataHora(i.criado_em)}</small></span>
    </button></li>`).join("")}</ul>` : '<p class="vazio">Sem novidades. Avisamos-te aqui quando houver mensagens ou mudanças nos teus pedidos.</p>'}`;
  painel.querySelectorAll("[data-novidade]").forEach((b) => (b.onclick = () => { painel.hidden = true; location.hash = `pedido/${b.dataset.novidade}`; }));
  const l = $("sino-lidas");
  if (l) l.onclick = async () => { await api("/api/novidades/lidas", { method: "POST" }); await actualizarNovidades(); desenharSino(); if (location.hash.startsWith("#pedidos") || location.hash.startsWith("#inicio")) mostrar(); };
}
document.addEventListener("click", (e) => { const p = $("sino-painel"); if (p && !p.hidden && !e.target.closest(".sino-caixa")) p.hidden = true; });
async function actualizarContadores() {
  try {
    const c = await api("/api/contadores");
    const valores = { pedidos: staff() ? (admin() ? (c.aprovar || 0) + (c.sem_tecnico || 0) : (c.sem_tecnico || 0) + (c.atribuidos || 0)) : c.aguardam_resposta };
    nav.querySelectorAll("[data-contador]").forEach((el) => {
      const v = valores[el.dataset.contador];
      el.hidden = !v; el.textContent = v || "";
    });
    return c;
  } catch { return {}; }
}
nav.addEventListener("click", (e) => { const b = e.target.closest("[data-sec]"); if (b) location.hash = b.dataset.sec; });
window.addEventListener("hashchange", () => eu && mostrar());
conteudo.addEventListener("click", (e) => {
  const b = e.target.closest("[data-pedido]");
  if (b) location.hash = `pedido/${b.dataset.pedido}`;
});

async function mostrar() {
  const [sec, arg] = (location.hash.slice(1) || paginaInicial()).split("/");
  const activo = sec === "pedido" ? "pedidos" : sec === "novo" ? "inicio" : sec;
  nav.querySelectorAll("button").forEach((b) => b.classList.toggle("activo", b.dataset.sec === activo));
  actualizarContadores();
  try {
    const vistas = { inicio: vistaInicio, pedidos: vistaPedidos, pedido: () => vistaPedido(Number(arg)), novo: () => vistaNovo(Number(arg)),
      painel: vistaPainel, equipamentos: () => vistaLista("equipamentos"), licencas: vistaLicencas, admin: () => vistaAdmin(arg || "utilizadores") };
    await (vistas[sec] || vistaInicio)();
    window.scrollTo(0, 0);
  } catch (err) {
    if (eu) conteudo.innerHTML = `${cabecalhoPagina("Não foi possível abrir esta página")}${vazio(err.message, "alerta", `<button onclick="location.hash='${paginaInicial()}'">Voltar ao início</button>`)}`;
  }
}

// ---------- novo pedido: catálogo ----------
let catInicio = "acesso";
async function vistaInicio() {
  const [d, catalogo] = await Promise.all([api("/api/inicio"), api("/api/catalogo?activo=true")]);
  const cats = TIPOS.filter((t) => catalogo.some((c) => c.tipo === t));
  if (!cats.includes(catInicio)) catInicio = cats[0];
  const aguardam = d.meus_pedidos.filter((p) => p.estado === "aguarda_colaborador");
  conteudo.innerHTML = `
    <div class="saudacao">
      <div><h1>Olá, ${esc(eu.nome.split(" ")[0])}</h1><p>O que precisas hoje?</p></div>
      <input type="search" id="procurar" placeholder="Procurar: monitor, VPN, Anywhere, impressora..." autocomplete="off">
    </div>
    ${aguardam.length ? `<section class="cartao destaque"><h2>${icone("mensagem")} A DSI precisa da tua resposta</h2>${tabela(aguardam, colunasPedido(), { clicavel: true })}</section>` : ""}
    ${d.para_aprovar.length ? `<section class="cartao destaque"><h2>${icone("alerta")} ${d.para_aprovar.length} pedido(s) à espera da tua aprovação</h2>${tabela(d.para_aprovar, colunasPedido(), { clicavel: true })}</section>` : ""}
    <section class="cartao catalogo">
      <div class="abas" id="cats">${cats.map((t) => `<button data-cat="${t}" class="${t === catInicio ? "activo" : ""}">${icone(ICONE_TIPO[t])}${esc(rot(t))}</button>`).join("")}</div>
      <div class="mosaicos" id="itens"></div>
    </section>
    ${d.meus_pedidos.length ? `<section class="cartao" style="margin-top:20px"><div class="seccao-cab"><h2>Os meus pedidos em curso</h2><button class="ligacao" onclick="location.hash='pedidos'">Ver todos</button></div>${tabela(d.meus_pedidos.slice(0, 5), colunasPedido(), { clicavel: true })}</section>` : ""}`;
  const desenhar = () => {
    const q = semAcentos($("procurar").value.trim());
    const lista = q ? catalogo.filter((c) => semAcentos(`${c.nome} ${c.descricao || ""} ${rot(c.tipo)}`).includes(q))
                    : catalogo.filter((c) => c.tipo === catInicio);
    $("cats").style.display = q ? "none" : "";
    $("itens").innerHTML = lista.map((c) => `
      <button class="mosaico" data-item="${c.id}">
        <span class="icone">${icone(c.icone)}</span>
        <span class="texto"><strong>${esc(c.nome)}</strong><small>${esc(c.descricao || "")}</small>
          ${c.requer_aprovacao ? '<span class="aprov">Requer aprovação DSI</span>' : ""}</span>
      </button>`).join("") || vazio('Nada encontrado. Experimenta outra palavra ou usa "Outro pedido".', "ajuda");
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
  const cont = await actualizarContadores();
  const vistas = staff()
    ? [["todos", "Todos", cont.todos], ["atribuidos", "Atribuídos a mim", cont.atribuidos], ...(admin() ? [["aprovar", "Para aprovar", cont.aprovar]] : []), ["meus", "Os meus", cont.meus]]
    : [];
  filtroPedidos ??= { vista: staff() ? "todos" : "meus", estado: "abertos", q: "" };
  const f = filtroPedidos;
  const estados = [["abertos", "Em aberto"], ["resolvido", "Resolvidos"], ["fechado", "Fechados"], ["", "Todos"]];
  const linhas = await api(`/api/pedidos?${new URLSearchParams({ vista: f.vista, estado: f.estado, q: f.q })}`);
  const titulo = staff() ? "Fila de pedidos" : "Os meus pedidos";
  const sub = staff() ? "Todos os pedidos dos colaboradores. Clica num pedido para o tratar." : "Pedidos feitos por ti ou em teu nome.";
  conteudo.innerHTML = `
    ${cabecalhoPagina(titulo, sub, botao("novo-pedido", "Novo pedido", { classe: "primario", ic: "mais" }))}
    <div class="filtros">
      ${vistas.length ? `<div class="abas">${vistas.map(([v, l, n]) => `<button data-vista="${v}" class="${f.vista === v ? "activo" : ""}">${l}${n ? `<span class="contador">${n}</span>` : ""}</button>`).join("")}</div>` : ""}
      <div class="barra">
        <div class="segmentos">${estados.map(([v, l]) => `<button data-estado="${v}" class="${f.estado === v ? "activo" : ""}">${l}</button>`).join("")}</div>
        <input type="search" id="pesquisa" placeholder="Pesquisar por nº (ex.: 12), assunto ou colega" value="${esc(f.q)}">
      </div>
    </div>
    <section class="cartao">${linhas.length ? tabela(linhas, colunasPedido(), { clicavel: true })
      : vazio(f.q ? "Nenhum pedido corresponde à pesquisa." : f.estado === "abertos" ? "Não há pedidos em aberto." : "Sem pedidos.", "lista",
        staff() ? "" : `<button class="primario" onclick="location.hash='inicio'">${icone("mais")}Fazer um pedido</button>`)}</section>`;
  $("novo-pedido").onclick = () => (location.hash = "inicio");
  conteudo.querySelectorAll("[data-vista]").forEach((b) => (b.onclick = () => { f.vista = b.dataset.vista; vistaPedidos(); }));
  conteudo.querySelectorAll("[data-estado]").forEach((b) => (b.onclick = () => { f.estado = b.dataset.estado; vistaPedidos(); }));
  let t;
  $("pesquisa").oninput = (e) => { clearTimeout(t); t = setTimeout(async () => { f.q = e.target.value; await vistaPedidos(); const p = $("pesquisa"); p.focus(); p.setSelectionRange(p.value.length, p.value.length); }, 300); };
}

// ---------- novo pedido: formulário ----------
function campoGuiado(c) {
  const obrig = c.obrigatorio ? ' <span class="obrig">*</span>' : "";
  let corpo;
  if (c.tipo === "opcoes" || c.tipo === "multi") {
    corpo = `<div class="pilulas" data-campo="${esc(c.id)}" data-tipo="${c.tipo}">${c.opcoes.map((o) =>
      `<button type="button" class="pilula" data-valor="${esc(o)}">${esc(o)}</button>`).join("")}</div>
      ${c.tipo === "multi" ? '<small class="ajuda">Podes escolher várias.</small>' : ""}
      ${c.tipo === "multi" && c.outro ? `<input class="outro" data-outro="${esc(c.id)}" placeholder="Não está na lista? Escreve aqui (separa por vírgulas)">` : ""}`;
  } else if (c.tipo === "data") {
    corpo = `<input type="date" data-campo="${esc(c.id)}" data-tipo="data" style="max-width:220px">`;
  } else {
    corpo = `<input data-campo="${esc(c.id)}" data-tipo="texto" placeholder="${esc(c.ajuda || "")}">`;
  }
  return `<div class="campo-guiado"><div class="rotulo">${esc(c.rotulo)}${obrig}</div>${corpo}</div>`;
}

function lerGuiado(form, campos) {
  const dados = {};
  for (const c of campos) {
    if (c.tipo === "opcoes" || c.tipo === "multi") {
      const sel = [...form.querySelectorAll(`[data-campo="${CSS.escape(c.id)}"] .pilula.activo`)].map((b) => b.dataset.valor);
      if (c.tipo === "multi") {
        const outro = form.querySelector(`[data-outro="${CSS.escape(c.id)}"]`);
        if (outro) sel.push(...outro.value.split(",").map((x) => x.trim()).filter(Boolean));
        if (sel.length) dados[c.id] = sel;
      } else if (sel[0]) dados[c.id] = sel[0];
    } else {
      const v = form.querySelector(`[data-campo="${CSS.escape(c.id)}"]`).value.trim();
      if (v) dados[c.id] = v;
    }
  }
  return dados;
}

async function vistaNovo(itemId) {
  const [catalogo, utilizadores] = await Promise.all([api("/api/catalogo?activo=true"), carregar("utilizadores", "/api/utilizadores?activo=true")]);
  const item = catalogo.find((c) => c.id === itemId);
  if (!item) { location.hash = "inicio"; return; }
  let campos = [];
  try { campos = item.campos ? JSON.parse(item.campos) : []; } catch { campos = []; }
  const colegas = utilizadores.filter((u) => u.id !== eu.id);
  conteudo.innerHTML = `
    <button class="voltar" onclick="location.hash='inicio'">${icone("voltar")}Escolher outro pedido</button>
    <form class="cartao formulario" id="form-novo">
      <div class="item-escolhido">
        <span class="icone">${icone(item.icone)}</span>
        <div><strong>${esc(item.nome)}</strong><small>${esc(rot(item.tipo))}${item.requer_aprovacao ? " · requer aprovação da DSI" : ""}</small></div>
      </div>
      <div class="campo-guiado"><div class="rotulo">Para quem é?</div>
        <div class="pilulas" id="para"><button type="button" class="pilula activo" data-valor="eu">Para mim</button><button type="button" class="pilula" data-valor="outro">Para outra pessoa</button></div>
        <div id="escolher-pessoa" class="seletor-pessoa" hidden>
          ${colegas.length ? `<input id="pessoa" placeholder="Escreve parte do nome ou do email" autocomplete="off">
          <div id="sugestoes" class="sugestoes"></div><div id="escolhido"></div>`
          : `<p class="dica">${icone("ajuda")} Ainda não há outros colaboradores no portal. Entram automaticamente com a sincronização do Entra ID${admin() ? ', ou podes criá-los em <a href="#admin/utilizadores">Administração &gt; Utilizadores</a>' : ""}.</p>`}
        </div>
      </div>
      ${campos.map(campoGuiado).join("")}
      <div class="campo-guiado"><div class="rotulo">${campos.length ? "Detalhes (opcional)" : 'Descreve o pedido <span class="obrig">*</span>'}</div>
        <textarea name="descricao" rows="${campos.length ? 3 : 6}" placeholder="${campos.length ? "Algo mais que a DSI deva saber?" : "O que precisas ou o que se passa, desde quando, mensagens de erro..."}"></textarea></div>
      <div class="campo-guiado"><div class="rotulo">Urgência</div>
        <div class="pilulas" id="urgencia"><button type="button" class="pilula activo" data-valor="">Normal</button>
          <button type="button" class="pilula" data-valor="alta">Urgente</button>${staff() ? '<button type="button" class="pilula" data-valor="critica">Crítico (serviço parado)</button>' : ""}</div></div>
      <p class="erro" id="erro-novo"></p>
      <div class="rodape-form"><button type="button" onclick="location.hash='inicio'">Cancelar</button><button class="primario" id="enviar">${icone("certo")}Enviar pedido</button></div>
    </form>`;
  const form = $("form-novo");
  let pessoaEscolhida = null;
  const mostrarEscolhido = () => {
    $("escolhido").innerHTML = pessoaEscolhida ? `<span class="pessoa-escolhida">${icone("utilizador")} ${esc(pessoaEscolhida.nome)}
      <small>${esc(pessoaEscolhida.email)}</small><button type="button" class="ligacao" id="trocar">Trocar</button></span>` : "";
    $("pessoa").hidden = !!pessoaEscolhida;
    if (pessoaEscolhida) $("trocar").onclick = () => { pessoaEscolhida = null; $("pessoa").value = ""; mostrarEscolhido(); $("pessoa").focus(); };
  };
  if ($("pessoa")) {
    $("pessoa").oninput = () => {
      const q = semAcentos($("pessoa").value.trim());
      const res = q ? colegas.filter((u) => semAcentos(`${u.nome} ${u.email}`).includes(q)).slice(0, 8) : [];
      $("sugestoes").innerHTML = res.map((u) => `<button type="button" data-pessoa="${u.id}">${esc(u.nome)} <small>${esc(u.email)}</small></button>`).join("")
        || (q ? '<div class="vazio">Nenhum colaborador com esse nome.</div>' : "");
      $("sugestoes").querySelectorAll("[data-pessoa]").forEach((b) => (b.onclick = () => {
        pessoaEscolhida = colegas.find((u) => u.id === Number(b.dataset.pessoa));
        $("sugestoes").innerHTML = ""; mostrarEscolhido();
      }));
    };
  }
  form.querySelectorAll(".pilulas").forEach((g) => g.addEventListener("click", (e) => {
    const b = e.target.closest(".pilula");
    if (!b) return;
    if (g.dataset.tipo === "multi") b.classList.toggle("activo");
    else { g.querySelectorAll(".pilula").forEach((x) => x.classList.toggle("activo", x === b)); }
    if (g.id === "para") { $("escolher-pessoa").hidden = b.dataset.valor !== "outro"; if ($("pessoa") && !pessoaEscolhida) $("pessoa").focus(); }
  }));
  form.onsubmit = async (e) => {
    e.preventDefault();
    let beneficiario_id = eu.id;
    if (form.querySelector("#para .activo").dataset.valor === "outro") {
      if (!pessoaEscolhida) { $("erro-novo").textContent = colegas.length ? "Escreve o nome e escolhe o colega na lista." : "Ainda não há outros colaboradores no portal."; return; }
      beneficiario_id = pessoaEscolhida.id;
    }
    const corpo = { item_id: item.id, beneficiario_id, dados: lerGuiado(form, campos),
      descricao: form.elements.descricao.value, prioridade: form.querySelector("#urgencia .activo").dataset.valor || null };
    $("enviar").disabled = true;
    try {
      const r = await api("/api/pedidos", { method: "POST", body: JSON.stringify(corpo) });
      aviso(`Pedido ${r.numero} enviado.`);
      location.hash = `pedido/${r.id}`;
    } catch (err) { $("erro-novo").textContent = err.message; $("enviar").disabled = false; }
  };
}

// ---------- detalhe do pedido ----------
// tipo: primario (acção principal), normal, perigo (vermelho). aviso: mensagem depois de executar.
const ACCOES = {
  automatizar: { l: "Executar automaticamente", tipo: "primario", ic: "definicoes", aviso: "Automação executada." },
  aprovar: { l: "Aprovar", tipo: "primario", ic: "certo", campos: [["motivo", "Observação (opcional)", "textarea"]], aviso: "Pedido aprovado." },
  assumir: { l: "Assumir pedido", tipo: "primario", ic: "utilizador", aviso: "Pedido atribuído a ti." },
  resolver: { l: "Resolver", tipo: "primario", ic: "certo", campos: [["motivo", "O que foi feito? *", "textarea", true]], aviso: "Pedido resolvido." },
  fechar: { l: "Sim, ficou resolvido", tipo: "primario", ic: "certo", confirmar: "O pedido fica fechado. Se o problema voltar nos próximos 5 dias, ainda o podes reabrir.", aviso: "Obrigado pela confirmação. Pedido fechado." },
  aguardar: { l: "Pedir informação", ic: "mensagem", campos: [["motivo", "O que precisas de saber? *", "textarea", true]], aviso: "Pedido de informação enviado." },
  atribuir: { l: "Atribuir", ic: "pessoa_mais", campos: [["tecnico_id", "Técnico *", "tecnico", true]], aviso: "Técnico atribuído." },
  prioridade: { l: "Alterar urgência", ic: "setas", campos: [["prioridade", "Nova urgência *", "prioridade", true]], aviso: "Urgência alterada." },
  entregar_equipamento: { l: "Entregar equipamento", ic: "portatil", campos: [["equipamento_id", "Equipamento em stock *", "equipamento", true]], aviso: "Equipamento entregue." },
  atribuir_licenca: { l: "Atribuir licença", ic: "insignia", campos: [["licenca_id", "Licença *", "licenca", true]], aviso: "Licença atribuída." },
  reabrir: { l: "Reabrir", ic: "relogio", campos: [["motivo", "O que ainda não está resolvido? *", "textarea", true]], aviso: "Pedido reaberto. O técnico foi avisado." },
  recusar: { l: "Recusar", tipo: "perigo", ic: "cruz", campos: [["motivo", "Motivo da recusa *", "textarea", true]], aviso: "Pedido recusado." },
  cancelar: { l: "Cancelar pedido", tipo: "perigo", ic: "cruz", campos: [["motivo", "Motivo (opcional)", "textarea"]], aviso: "Pedido cancelado." },
};
const ORDEM_ACCOES = ["automatizar", "aprovar", "assumir", "resolver", "fechar", "aguardar", "atribuir", "prioridade", "entregar_equipamento", "atribuir_licenca", "reabrir", "recusar", "cancelar"];
const EVENTOS = { criado: "Pedido registado", aguarda_aprovacao: "A aguardar aprovação da DSI", aprovado: "Aprovado", recusado: "Recusado",
  atribuido: "Atribuído", aguarda_colaborador: "Pedido de informação", resposta_colaborador: "Resposta do colaborador", prioridade: "Urgência alterada",
  resolvido: "Resolvido", reaberto: "Reaberto", fechado: "Fechado", cancelado: "Cancelado", automacao: "Automação",
  equipamento_entregue: "Equipamento entregue", licenca_atribuida: "Licença atribuída" };

function etapas(p) {
  if (["recusado", "cancelado"].includes(p.estado)) return `<div class="etapas fim">${etiqueta(p.estado)}</div>`;
  const passos = [["registado", "Registado"], ...(p.aprovador || p.estado === "em_aprovacao" ? [["aprovacao", "Aprovação DSI"]] : []), ["tratamento", "Em tratamento"], ["resolvido", "Resolvido"], ["fechado", "Fechado"]];
  const actual = { em_aprovacao: "aprovacao", novo: "tratamento", em_curso: "tratamento", aguarda_colaborador: "tratamento", resolvido: "resolvido", fechado: "fechado" }[p.estado];
  const idx = passos.findIndex(([k]) => k === actual);
  return `<ol class="etapas">${passos.map(([k, l], i) => `<li class="${i < idx || p.estado === "fechado" ? "feito" : i === idx ? "actual" : ""}">${l}</li>`).join("")}</ol>`;
}

// Etiqueta curta das mensagens que vêm de acções (pergunta, solução, motivo).
const NA_CONVERSA = { aguarda_colaborador: "Pedido de informação", resolvido: "Solução aplicada", reaberto: "Pedido reaberto",
  recusado: "Motivo da recusa", aprovado: "Aprovação", cancelado: "Motivo do cancelamento", fechado: "Fecho" };
let separadorPedido = "conversa";

function bolha(m, p) {
  const minha = m.autor_id === eu.id;
  const rotulo = m.tipo === "evento" ? `<span class="rotulo-accao">${esc(NA_CONVERSA[m.accao] || m.accao)}</span>` : "";
  const nova = m.nova && !minha;
  return `<div class="msg ${minha ? "minha" : "outra"} ${m.interno ? "interna" : ""} ${m.tipo === "evento" ? "accao" : ""} ${nova ? "nova" : ""}">
    <div class="msg-cab"><strong>${esc(minha ? "Tu" : m.autor)}</strong>${m.dsi && !minha ? '<span class="etiqueta marca">DSI</span>' : ""}${m.interno ? '<span class="etiqueta alerta">Nota interna</span>' : ""}<small>${dataHora(m.criado_em)}</small></div>
    ${rotulo}<p>${esc(m.texto)}</p></div>`;
}

async function vistaPedido(id, { manterRascunho = false } = {}) {
  const rascunho = manterRascunho ? $("form-comentario")?.texto.value : "";
  const p = await api(`/api/pedidos/${id}`);
  actualizarNovidades();
  const meuPedido = p.criado_por_id === eu.id || p.beneficiario_id === eu.id || [p.beneficiario, p.criado_por].includes(eu.nome);
  const confirmarResolucao = p.estado === "resolvido" && p.accoes.includes("fechar");
  const accoes = ORDEM_ACCOES.filter((a) => p.accoes.includes(a) && !(confirmarResolucao && (a === "fechar" || a === "reabrir")));
  const btn = (a) => `<button data-accao="${a}" class="${ACCOES[a].tipo === "primario" ? "primario" : ACCOES[a].tipo === "perigo" ? "perigo" : ""}">${icone(ACCOES[a].ic)}${esc(ACCOES[a].l)}</button>`;
  const encerrado = ["fechado", "recusado", "cancelado"].includes(p.estado);
  const novas = p.conversa.filter((m) => m.nova && m.autor_id !== eu.id).length;
  conteudo.innerHTML = `
    <button class="voltar" onclick="history.length > 1 ? history.back() : (location.hash='pedidos')">${icone("voltar")}Voltar</button>
    <div class="pagina-cab pedido-cab">
      <div><small class="numero">${esc(p.numero)} · ${esc(rot(p.tipo))}</small><h1>${esc(p.titulo)}</h1>
        <div class="etiquetas">${etiqueta(p.estado)}${p.prioridade === "alta" || p.prioridade === "critica" ? etiqueta(p.prioridade) : ""}${etiqueta(p.sla)}</div></div>
    </div>
    ${etapas(p)}
    ${confirmarResolucao ? `<section class="cartao confirmar-resolucao">
        <h2>${icone("certo")} O técnico deu este pedido como resolvido</h2>
        ${p.solucao ? `<p class="solucao"><span>O que foi feito</span>${esc(p.solucao)}</p>` : ""}
        <p>Ficou mesmo resolvido? Se não responderes, o pedido fecha automaticamente a ${dataHora(p.fecho_automatico_em)}.</p>
        <div class="barra-accoes"><button class="primario" data-accao="fechar">${icone("certo")}Sim, ficou resolvido</button>
          <button class="perigo" data-accao="reabrir">${icone("cruz")}Não ficou resolvido</button></div>
      </section>` : ""}
    ${p.estado === "aguarda_colaborador" && meuPedido && !staff() ? `<div class="dica">${icone("mensagem")} A DSI precisa de mais informação. Responde na conversa abaixo.</div>` : ""}
    ${p.estado === "fechado" && p.accoes.includes("reabrir") ? `<div class="dica">${icone("relogio")} O problema voltou? Ainda podes reabrir este pedido.</div>` : ""}
    ${accoes.length ? `<div class="barra-accoes">${accoes.map(btn).join("")}</div>` : ""}
    <div class="duas-colunas">
      <section class="cartao conversa-cartao">
        <div class="abas abas-pedido">
          <button data-sep="conversa" class="${separadorPedido === "conversa" ? "activo" : ""}">${icone("mensagem")}Conversa${novas ? `<span class="contador">${novas}</span>` : ""}</button>
          <button data-sep="historico" class="${separadorPedido === "historico" ? "activo" : ""}">${icone("relogio")}Histórico</button>
        </div>
        <div id="sep-conversa" ${separadorPedido === "conversa" ? "" : "hidden"}>
          <div class="chat" id="chat">${p.conversa.map((m) => bolha(m, p)).join("") || `<p class="vazio">Ainda sem mensagens. ${staff() ? "Escreve ao colaborador abaixo." : "Se precisares de acrescentar algo, escreve à DSI abaixo."}</p>`}</div>
          ${encerrado ? '<p class="vazio">Pedido encerrado: a conversa está fechada.</p>' : `
          <form id="form-comentario" class="form-comentario">
            <textarea name="texto" rows="2" required placeholder="${staff() ? "Mensagem para o colaborador" : "Mensagem para a DSI"} (Enter envia, Shift+Enter muda de linha)"></textarea>
            <div class="linha">
              ${staff() ? '<label class="interruptor"><input type="checkbox" name="interno"><span></span>Nota interna (só DSI)</label>' : ""}
              <button class="primario">${icone("mensagem")}Enviar</button>
            </div>
            <p class="erro" id="erro-comentario"></p>
          </form>`}
        </div>
        <div id="sep-historico" ${separadorPedido === "historico" ? "" : "hidden"}>
          <ul class="linha-tempo">
            ${p.eventos.map((e) => `<li><strong>${esc(EVENTOS[e.accao] ?? e.accao)}</strong>${e.detalhe ? `<span>${esc(e.detalhe)}</span>` : ""}<small>${esc(e.autor)} · ${dataHora(e.criado_em)}</small></li>`).join("")}
          </ul>
        </div>
      </section>
      <section class="cartao">
        <h2>Detalhes</h2>
        <div class="meta meta-coluna">
          <div><span>Para</span>${esc(p.beneficiario)}</div>
          <div><span>Pedido por</span>${esc(p.criado_por)}</div>
          <div><span>Técnico</span>${esc(p.tecnico || "Por atribuir")}</div>
          ${p.aprovador ? `<div><span>Aprovado por</span>${esc(p.aprovador)}</div>` : ""}
          <div><span>Registado em</span>${dataHora(p.criado_em)}${p.origem === "email" ? " · por email" : ""}</div>
        </div>
        <div class="prazos">
          <h3>${icone("relogio")}Prazos</h3>
          ${p.estado === "em_aprovacao" ? '<p class="vazio">Os prazos começam a contar quando a DSI aprovar o pedido.</p>' : `
          <div><span>Primeira resposta até</span>${dataHora(p.prazo_resposta)}${p.primeira_resposta_em ? ` <small>Respondido ${dataHora(p.primeira_resposta_em)}</small>` : ""}</div>
          <div><span>Resolução até</span>${dataHora(p.prazo_resolucao)} ${etiqueta(p.sla)}${p.resolvido_em ? ` <small>Resolvido ${dataHora(p.resolvido_em)}</small>` : ""}</div>
          <p class="nota-prazo">Urgência ${esc(rot(p.prioridade).toLowerCase())}. Horas úteis: segunda a sexta, das 08:00 às 17:00.</p>`}
        </div>
        ${p.respostas.length ? `<dl class="respostas">${p.respostas.map((r) => `<dt>${esc(r.campo)}</dt><dd>${esc(r.valor)}</dd>`).join("")}</dl>` : ""}
        ${p.descricao ? `<p class="descricao">${esc(p.descricao)}</p>` : ""}
        ${p.automacao && accoes.includes("automatizar") ? `<p class="dica">${icone("definicoes")} Pode ser resolvido automaticamente: ${esc(p.automacao)}.</p>` : ""}
      </section>
    </div>`;
  const chat = $("chat");
  if (chat) chat.scrollTop = chat.scrollHeight;
  conteudo.querySelectorAll("[data-sep]").forEach((b) => (b.onclick = () => {
    separadorPedido = b.dataset.sep;
    conteudo.querySelectorAll("[data-sep]").forEach((x) => x.classList.toggle("activo", x === b));
    $("sep-conversa").hidden = separadorPedido !== "conversa";
    $("sep-historico").hidden = separadorPedido !== "historico";
    if (separadorPedido === "conversa") chat.scrollTop = chat.scrollHeight;
  }));
  const fc = $("form-comentario");
  if (fc) {
    if (rascunho) fc.texto.value = rascunho;
    fc.texto.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); fc.requestSubmit(); } };
    fc.onsubmit = async (e) => {
      e.preventDefault();
      if (!fc.texto.value.trim()) return;
      try {
        await api(`/api/pedidos/${id}/comentarios`, { method: "POST", body: JSON.stringify({ texto: fc.texto.value, interno: !!fc.interno?.checked }) });
        await vistaPedido(id);
        $("form-comentario")?.texto.focus();
      } catch (err) { $("erro-comentario").textContent = err.message; }
    };
  }
  conteudo.querySelectorAll("[data-accao]").forEach((b) => (b.onclick = () => abrirAccao(id, b.dataset.accao)));
}

async function abrirAccao(id, accao) {
  const def = ACCOES[accao];
  const executar = async (corpo) => {
    await api(`/api/pedidos/${id}/accoes/${accao}`, { method: "POST", body: JSON.stringify(corpo) });
    aviso(def.aviso);
    actualizarContadores();
    vistaPedido(id);
  };
  if (!def.campos) {
    if (def.confirmar && !(await confirmar(def.l, def.confirmar, def.l))) return;
    try { await executar({}); } catch (err) { aviso(err.message, "erro"); vistaPedido(id); }
    return;
  }
  const opcoes = {};
  for (const [, , t] of def.campos) {
    if (t === "tecnico") opcoes.tecnico = (await api("/api/utilizadores?activo=true")).filter((u) => u.perfil === "helpdesk" || u.perfil === "admin").map((u) => [u.id, u.nome]);
    if (t === "prioridade") opcoes.prioridade = ["critica", "alta", "media", "baixa"].map((p) => [p, rot(p)]);
    if (t === "equipamento") opcoes.equipamento = (await api("/api/equipamentos?estado=stock")).map((e) => [e.id, `${e.etiqueta} · ${e.tipo} ${e.marca || ""} ${e.modelo || ""}`]);
    if (t === "licenca") opcoes.licenca = (await api("/api/licencas")).map((l) => [l.id, `${l.produto} (${l.livres} livres)`]);
  }
  abrirDialogo({
    titulo: def.l, botaoTexto: def.l, perigo: def.tipo === "perigo",
    corpo: def.campos.map(([k, l, t, req]) => `<label class="largo">${esc(l)}${t === "textarea"
      ? `<textarea name="${k}" rows="4" ${req ? "required" : ""}></textarea>`
      : `<select name="${k}" ${req ? "required" : ""}><option value="">Escolher...</option>${(opcoes[t] || []).map(([v, n]) => `<option value="${esc(v)}">${esc(n)}</option>`).join("")}</select>`}</label>`).join(""),
    aoGravar: async () => {
      const corpo = {};
      for (const [k, , t] of def.campos) {
        const v = formDialogo.elements[k].value.trim();
        corpo[k] = v === "" ? null : (["tecnico", "equipamento", "licenca"].includes(t) ? Number(v) : v);
      }
      await executar(corpo);
    },
  });
}

// ---------- painel ----------
async function vistaPainel() {
  const p = await api("/api/painel");
  const maxTec = Math.max(1, ...p.por_tecnico.map((x) => x.abertos));
  const maxTipo = Math.max(1, ...Object.values(p.por_tipo));
  const inv = cfg.inventario;
  conteudo.innerHTML = `
    ${cabecalhoPagina("Painel", "Visão geral dos pedidos em aberto.", botao("ir-fila", "Abrir fila de pedidos", { ic: "lista" }))}
    <div class="kpis">
      ${kpi("Em aberto", p.abertos, `${p.por_estado.em_aprovacao} em aprovação`, "lista")}
      ${kpi("Sem técnico", p.sem_tecnico, "por atribuir", "pessoa_mais")}
      ${kpi("Fora de prazo", p.sla_violado, `${p.sla_em_risco} em risco`, "relogio")}
      ${kpi("Resolvidos em 7 dias", p.resolvidos_7d, "", "certo")}
      ${inv ? kpi("Equipamento em stock", p.equipamentos_por_estado.stock, `${p.equipamentos_por_estado.reparacao} em reparação`, "portatil") : ""}
    </div>
    <section class="cartao" style="margin-bottom:16px"><h2>Exigem atenção</h2>${tabela(p.atencao, colunasPedido(), { clicavel: true, vazioTexto: "Nenhum pedido fora de prazo ou em risco." })}</section>
    <div class="grelha">
      <section class="cartao"><h2>Carga por técnico</h2>${p.por_tecnico.map((x) => barra(x.tecnico, x.abertos / maxTec, x.abertos)).join("") || vazio("Sem pedidos em aberto.")}
        <h2 style="margin-top:20px">Por estado</h2>${Object.entries(p.por_estado).map(([e, n]) => barra(rot(e), n / Math.max(1, p.abertos), n)).join("")}</section>
      <section class="cartao"><h2>Em aberto por categoria</h2>${Object.entries(p.por_tipo).map(([t, n]) => barra(rot(t), n / maxTipo, n)).join("")}
      ${inv ? `<h2 style="margin-top:20px">Licenças</h2>${tabela(p.licencas, [["produto", "Produto"], ["quantidade", "Total", null, "num"], ["usadas", "Usadas", null, "num"],
        ["livres", "Livres", (v) => `<span class="etiqueta ${v === 0 ? "perigo" : v <= 2 ? "alerta" : "ok"}">${v}</span>`, "num"], ["renovacao_em", "Renovação", dataPT]])}` : ""}</section>
    </div>`;
  $("ir-fila").onclick = () => (location.hash = "pedidos");
}

// ---------- administração: listas e formulários ----------
const ENTIDADES = {
  utilizadores: {
    titulo: "Utilizadores", singular: "utilizador", ajuda: "Com o Entra ID ligado, os colaboradores entram sozinhos. Aqui defines quem é Helpdesk ou Administrador.",
    campos: [["nome", "Nome *", "text", true], ["email", "Email *", "email", true], ["departamento_id", "Departamento", "ref:departamentos"],
      ["perfil", "Perfil *", "select", true, ["colaborador", "helpdesk", "admin"]], ["activo", "Activo", "toggle"]],
    colunas: [["nome", "Nome", (v, o) => `<strong>${esc(v)}</strong><small class="sub">${esc(o.email)}</small>`], ["departamento_id", "Departamento", (v) => esc(nomeDe("departamentos", v))],
      ["perfil", "Perfil", (v) => `<span class="etiqueta ${v === "colaborador" ? "" : "marca"}">${esc(rot(v))}</span>`], ["activo", "Activo", simNao]],
    refs: ["departamentos"],
  },
  catalogo: {
    titulo: "Catálogo", singular: "item", ajuda: "O que os colaboradores podem pedir. Cada item tem as suas perguntas de escolha.",
    campos: [["nome", "Nome *", "text", true], ["tipo", "Categoria *", "select", true, TIPOS],
      ["descricao", "Descrição curta (aparece no mosaico)", "text"], ["prioridade_padrao", "Urgência por omissão", "select", true, ["critica", "alta", "media", "baixa"]],
      ["icone", "Ícone", "icone"], ["ordem", "Ordem na lista", "number"],
      ["requer_aprovacao", "Requer aprovação da DSI", "toggle"], ["activo", "Visível para os colaboradores", "toggle"],
      ["automacao", "Automação", "select", false, ["desbloquear_ad"]], ["campos", "Perguntas do formulário", "campos"]],
    colunas: [["nome", "Item", (v, o) => `<div class="assunto"><span class="mini-icone">${icone(o.icone)}</span><div><strong>${esc(v)}</strong><small>${esc(o.descricao || "")}</small></div></div>`],
      ["tipo", "Categoria", rot], ["campos", "Perguntas", (v) => { try { return String(JSON.parse(v || "[]").length); } catch { return "?"; } }, "num"],
      ["requer_aprovacao", "Aprovação", simNao], ["activo", "Visível", simNao]],
  },
  departamentos: { titulo: "Departamentos", singular: "departamento", ajuda: "Vêm do Entra ID quando a sincronização estiver activa.", campos: [["nome", "Nome *", "text", true]], colunas: [["nome", "Nome"]] },
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
};

async function vistaLista(nome, alvo = conteudo, topo = "") {
  const ent = ENTIDADES[nome];
  await Promise.all((ent.refs || []).map((r) => carregar(r)));
  const linhas = await api(`/api/${nome}?limit=2000`);
  alvo.innerHTML = `${topo || cabecalhoPagina(ent.titulo, ent.ajuda || "")}
    <div class="seccao-cab">${topo ? `<p class="ajuda-seccao">${esc(ent.ajuda || "")}</p>` : "<span></span>"}${botao(`novo-${nome}`, `Novo ${ent.singular}`, { classe: "primario", ic: "mais" })}</div>
    <div class="barra"><input type="search" id="filtro-${nome}" placeholder="Filtrar ${ent.titulo.toLowerCase()}..."></div>
    <section class="cartao" id="tabela-${nome}">${tabela(linhas, ent.colunas, { editar: true })}</section>`;
  const redesenhar = () => vistaLista(nome, alvo, topo);
  $(`novo-${nome}`).onclick = () => abrirFormulario(nome, null, redesenhar);
  const ligar = () => alvo.querySelectorAll("[data-editar]").forEach((b) => (b.onclick = () => abrirFormulario(nome, linhas.find((x) => x.id === Number(b.dataset.editar)), redesenhar)));
  ligar();
  $(`filtro-${nome}`).oninput = (e) => {
    const t = semAcentos(e.target.value);
    const filtradas = linhas.filter((o) => semAcentos(Object.values(o).join(" ")).includes(t));
    $(`tabela-${nome}`).innerHTML = tabela(filtradas, ent.colunas, { editar: true, vazioTexto: "Nenhum resultado." });
    ligar();
  };
}

// Editor visual das perguntas de um item do catálogo (substitui o JSON).
const TIPOS_PERGUNTA = [["opcoes", "Escolha única"], ["multi", "Escolha múltipla"], ["texto", "Texto curto"], ["data", "Data"]];
function editorPerguntas(json) {
  let lista = [];
  try { lista = json ? JSON.parse(json) : []; } catch { lista = []; }
  const html = (c, i) => `
    <div class="pergunta" data-i="${i}" data-id="${esc(c.id || "")}">
      <div class="pergunta-topo">
        <input class="p-rotulo" value="${esc(c.rotulo || "")}" placeholder="Pergunta (ex.: Que conta?)">
        <select class="p-tipo">${TIPOS_PERGUNTA.map(([v, l]) => `<option value="${v}" ${c.tipo === v ? "selected" : ""}>${l}</option>`).join("")}</select>
        <button type="button" class="icone-btn p-cima" title="Subir">${icone("cima")}</button>
        <button type="button" class="icone-btn p-baixo" title="Descer">${icone("baixo")}</button>
        <button type="button" class="icone-btn p-remover" title="Remover">${icone("lixo")}</button>
      </div>
      <textarea class="p-opcoes" rows="3" placeholder="Uma opção por linha" ${c.tipo === "opcoes" || c.tipo === "multi" ? "" : "hidden"}>${esc((c.opcoes || []).join("\n"))}</textarea>
      <input class="p-ajuda" value="${esc(c.ajuda || "")}" placeholder="Exemplo ou ajuda (opcional)" ${c.tipo === "texto" ? "" : "hidden"}>
      <div class="pergunta-opcoes">
        <label class="interruptor"><input type="checkbox" class="p-obrig" ${c.obrigatorio ? "checked" : ""}><span></span>Obrigatória</label>
        <label class="interruptor" ${c.tipo === "multi" ? "" : "hidden"}><input type="checkbox" class="p-outro" ${c.outro ? "checked" : ""}><span></span>Permitir escrever "Outro"</label>
      </div>
    </div>`;
  return `<div class="editor-perguntas" id="editor-perguntas">${lista.map(html).join("")}</div>
    <button type="button" id="nova-pergunta">${icone("mais")}Adicionar pergunta</button>`;
}
function ligarEditorPerguntas() {
  const ed = $("editor-perguntas");
  if (!ed) return;
  const vaziaHTML = () => editorPerguntas(JSON.stringify([{ id: "", rotulo: "", tipo: "opcoes", opcoes: [], obrigatorio: true }]));
  $("nova-pergunta").onclick = () => {
    const tmp = document.createElement("div"); tmp.innerHTML = vaziaHTML();
    ed.appendChild(tmp.querySelector(".pergunta")); ed.lastElementChild.querySelector(".p-rotulo").focus();
  };
  ed.addEventListener("click", (e) => {
    const p = e.target.closest(".pergunta");
    if (!p) return;
    if (e.target.closest(".p-remover")) p.remove();
    if (e.target.closest(".p-cima") && p.previousElementSibling) ed.insertBefore(p, p.previousElementSibling);
    if (e.target.closest(".p-baixo") && p.nextElementSibling) ed.insertBefore(p.nextElementSibling, p);
  });
  ed.addEventListener("change", (e) => {
    if (!e.target.classList.contains("p-tipo")) return;
    const p = e.target.closest(".pergunta"), t = e.target.value;
    p.querySelector(".p-opcoes").hidden = !(t === "opcoes" || t === "multi");
    p.querySelector(".p-ajuda").hidden = t !== "texto";
    p.querySelector(".p-outro").closest("label").hidden = t !== "multi";
  });
}
function lerEditorPerguntas() {
  const usados = new Set();
  return JSON.stringify([...document.querySelectorAll("#editor-perguntas .pergunta")].map((p) => {
    const rotulo = p.querySelector(".p-rotulo").value.trim();
    if (!rotulo) throw new Error("Há uma pergunta sem texto.");
    let id = p.dataset.id || semAcentos(rotulo).replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 30) || "campo";
    while (usados.has(id)) id += "_2";
    usados.add(id);
    const tipo = p.querySelector(".p-tipo").value;
    const c = { id, rotulo, tipo, obrigatorio: p.querySelector(".p-obrig").checked };
    if (tipo === "opcoes" || tipo === "multi") {
      c.opcoes = p.querySelector(".p-opcoes").value.split("\n").map((x) => x.trim()).filter(Boolean);
      if (!c.opcoes.length) throw new Error(`A pergunta "${rotulo}" precisa de opções (uma por linha).`);
    }
    if (tipo === "multi") c.outro = p.querySelector(".p-outro").checked;
    if (tipo === "texto") c.ajuda = p.querySelector(".p-ajuda").value.trim();
    return c;
  }));
}

function abrirFormulario(nome, obj, aoGravar) {
  const ent = ENTIDADES[nome];
  const corpo = ent.campos.map(([k, l, t = "text", req, opcoes]) => {
    const v = obj?.[k] ?? (t === "toggle" && !obj ? true : "");
    let input;
    if (t === "select") input = `<select name="${k}" ${req ? "required" : ""}>${req ? "" : '<option value="">Nenhuma</option>'}${opcoes.map((o) => `<option value="${esc(o)}" ${o === v ? "selected" : ""}>${esc(rot(o))}</option>`).join("")}</select>`;
    else if (t.startsWith("ref:")) input = `<select name="${k}"><option value="">Nenhum</option>${(cache[t.slice(4)] || []).filter((o) => o.id !== obj?.id).map((o) => `<option value="${o.id}" ${o.id === v ? "selected" : ""}>${esc(o.nome)}</option>`).join("")}</select>`;
    else if (t === "textarea") input = `<textarea name="${k}" rows="3">${esc(v)}</textarea>`;
    else if (t === "toggle") return `<label class="interruptor campo-toggle"><input type="checkbox" name="${k}" ${v ? "checked" : ""}><span></span>${esc(l)}</label>`;
    else if (t === "icone") input = `<input type="hidden" name="${k}" value="${esc(v || "caixa")}"><div class="grelha-icones">${ICONES_CATALOGO.map((n) => `<button type="button" data-icone="${n}" class="${n === (v || "caixa") ? "activo" : ""}" title="${n}">${icone(n)}</button>`).join("")}</div>`;
    else if (t === "campos") return `<div class="largo campo-editor"><div class="rotulo-campo">${esc(l)}</div>${editorPerguntas(v)}</div>`;
    else input = `<input type="${t}" name="${k}" value="${esc(v)}" ${t === "number" ? 'step="any" min="0"' : ""} ${req ? "required" : ""}>`;
    return `<label class="${t === "textarea" || t === "icone" ? "largo" : ""}">${esc(l)}${input}</label>`;
  }).join("");
  abrirDialogo({
    titulo: `${obj ? "Editar" : "Novo"} ${ent.singular}`, corpo,
    aoGravar: async () => {
      const dados = {};
      for (const [k, , t = "text"] of ent.campos) {
        if (t === "campos") { dados[k] = lerEditorPerguntas(); continue; }
        const el = formDialogo.elements[k];
        let v = t === "toggle" ? el.checked : el.value.trim();
        if (v === "") v = null;
        else if (t === "number" || t.startsWith("ref:")) v = Number(v);
        if (v !== null || obj) dados[k] = v;
      }
      await api(obj ? `/api/${nome}/${obj.id}` : `/api/${nome}`, { method: obj ? "PATCH" : "POST", body: JSON.stringify(dados) });
      aviso(obj ? "Alterações gravadas." : `${ent.singular[0].toUpperCase()}${ent.singular.slice(1)} criado.`);
      aoGravar();
    },
  });
  dialogo.querySelectorAll("[data-icone]").forEach((b) => (b.onclick = () => {
    dialogo.querySelectorAll("[data-icone]").forEach((x) => x.classList.toggle("activo", x === b));
    formDialogo.elements.icone.value = b.dataset.icone;
  }));
  ligarEditorPerguntas();
}

// ---------- licenças (módulo de inventário) ----------
async function vistaLicencas() {
  const linhas = await api("/api/licencas");
  conteudo.innerHTML = `
    ${cabecalhoPagina("Licenças", "Quantidades compradas, usadas e livres.", admin() ? botao("nova-licenca", "Nova licença", { classe: "primario", ic: "mais" }) : "")}
    <section class="cartao">${tabela(linhas, [["produto", "Produto", (v, o) => `<button class="ligacao" data-lic="${o.id}">${esc(v)}</button>`], ["fornecedor", "Fornecedor"],
      ["quantidade", "Total", null, "num"], ["usadas", "Usadas", null, "num"],
      ["livres", "Livres", (v) => `<span class="etiqueta ${v === 0 ? "perigo" : v <= 2 ? "alerta" : "ok"}">${v}</span>`, "num"],
      ["custo_anual", "Custo anual", kz, "num"], ["renovacao_em", "Renovação", dataPT]], { editar: admin() })}</section>`;
  if (admin()) {
    $("nova-licenca").onclick = () => abrirFormulario("licencas", null, vistaLicencas);
    conteudo.querySelectorAll("[data-editar]").forEach((b) => (b.onclick = () => abrirFormulario("licencas", linhas.find((x) => x.id === Number(b.dataset.editar)), vistaLicencas)));
  }
  conteudo.querySelectorAll("[data-lic]").forEach((b) => (b.onclick = () => verAtribuicoes(linhas.find((x) => x.id === Number(b.dataset.lic)))));
}

async function verAtribuicoes(lic) {
  const at = await api(`/api/licencas/${lic.id}/atribuicoes`);
  abrirDialogo({
    titulo: `${lic.produto}: ${at.length} de ${lic.quantidade} atribuídas`,
    corpo: `<div class="largo">${tabela(at, [["utilizador", "Utilizador"], ["atribuida_em", "Desde", dataPT],
      ["utilizador_id", "", (v) => `<button type="button" class="pequeno perigo" data-remover="${v}">Retirar</button>`]])}
      <p class="vazio">Novas atribuições fazem-se a partir de um pedido, para ficar registado quem pediu e quem aprovou.</p></div>`,
  });
  $("dialogo-corpo").querySelectorAll("[data-remover]").forEach((b) => (b.onclick = async () => {
    try { await api(`/api/licencas/${lic.id}/atribuicoes/${b.dataset.remover}`, { method: "DELETE" }); aviso("Licença retirada."); dialogo.close(); await vistaLicencas(); }
    catch (err) { $("dialogo-erro").textContent = err.message; }
  }));
}

// ---------- administração ----------
async function vistaAdmin(sub) {
  const abas = [["utilizadores", "Utilizadores", "utilizadores"], ["catalogo", "Catálogo", "lista"], ["departamentos", "Departamentos", "pasta"], ["integracoes", "Integrações", "nuvem"]];
  const topo = `${cabecalhoPagina("Administração", "Configuração do Gestor de Pedidos.")}
    <div class="abas abas-admin">${abas.map(([k, l, ic]) => `<button onclick="location.hash='admin/${k}'" class="${sub === k ? "activo" : ""}">${icone(ic)}${l}</button>`).join("")}</div>`;
  if (sub === "integracoes") return vistaIntegracoes(topo);
  await vistaLista(ENTIDADES[sub] ? sub : "utilizadores", conteudo, topo);
}

async function vistaIntegracoes(topo) {
  const [e, ns] = await Promise.all([api("/api/admin/estado"), api("/api/admin/notificacoes")]);
  const sim = (v) => (v ? '<span class="etiqueta ok">Activo</span>' : '<span class="etiqueta alerta">Por configurar</span>');
  conteudo.innerHTML = `${topo}
    <section class="cartao" style="margin-bottom:16px">
      <h2>Microsoft 365</h2>
      <div class="meta">
        <div><span>Início de sessão</span>${e.modo_autenticacao === "entra" ? "Conta Microsoft (Entra ID)" : "Modo de teste (sem palavra-passe)"}</div>
        <div><span>Ligação ao Microsoft Graph</span>${sim(e.graph_configurado)}</div>
        <div><span>Caixa do Helpdesk</span>${esc(e.caixa_helpdesk || "Não definida")}</div>
        <div><span>Pedidos por email</span>${sim(e.leitura_caixa)}</div>
        <div><span>Último ciclo</span>${dataHora(e.ultimo_ciclo) || "Ainda não correu"}</div>
        <div><span>Última sincronização</span>${dataHora(e.ultima_sincronizacao) || "Ainda não correu"}</div>
      </div>
      <div class="barra-accoes" style="margin:16px 0 0">
        ${botao("btn-ciclo", "Enviar emails pendentes agora", { ic: "email" })}
        <button id="btn-sync" ${e.graph_configurado ? "" : "disabled"}>${icone("utilizadores")}Sincronizar colaboradores</button>
      </div>
      <p class="vazio" id="resultado"></p>
    </section>
    <section class="cartao"><h2>Emails enviados pelo portal</h2>
      ${tabela(ns, [["criado_em", "Data", dataHora], ["para", "Para"], ["assunto", "Assunto"],
        ["estado", "Estado", (v) => `<span class="etiqueta ${v === "enviada" ? "ok" : v === "erro" ? "perigo" : "alerta"}">${esc({ enviada: "Enviado", erro: "Erro", simulada: "Simulado", pendente: "Pendente" }[v] || v)}</span>`],
        ["erro", "Erro", (v) => esc((v || "").slice(0, 80))]], { vazioTexto: "Ainda não foram gerados emails." })}
    </section>`;
  const correr = async (url, msg) => {
    $("resultado").textContent = "A executar...";
    try { await api(url, { method: "POST" }); aviso(msg); vistaIntegracoes(topo); } catch (err) { $("resultado").textContent = err.message; }
  };
  $("btn-ciclo").onclick = () => correr("/api/admin/ciclo", "Tarefas executadas.");
  $("btn-sync").onclick = () => correr("/api/admin/ciclo?sincronizar=true", "Sincronização concluída.");
}

arrancar();
