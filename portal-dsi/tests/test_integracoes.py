"""Testes da etapa 1b com o Microsoft Graph e o Entra ID simulados (sem rede)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from portal import correio, db as dbmod, entra, notificacoes, pedidos as wf, sincronizacao
from portal.models import Departamento, ItemCatalogo, MensagemRecebida, Notificacao, Pedido, Utilizador

TENANT = "11111111-2222-3333-4444-555555555555"


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setenv("PORTAL_SEED", "demo")
    monkeypatch.setenv("PORTAL_AUTH_MODE", "dev")
    monkeypatch.setenv("PORTAL_TAREFAS", "0")
    monkeypatch.setenv("PORTAL_INVENTARIO", "1")
    monkeypatch.setenv("PORTAL_CAIXA_HELPDESK", "helpdesk@mhais.example")
    dbmod.configure("sqlite://")
    from portal.main import app

    with TestClient(app) as c:
        yield c
    dbmod.Base.metadata.drop_all(dbmod.engine)


@pytest.fixture()
def db(app_client):
    with dbmod.SessionLocal() as s:
        yield s


def user(db, prefixo) -> Utilizador:
    return db.scalar(select(Utilizador).where(Utilizador.email.startswith(prefixo)))


class FakeGraph:
    def __init__(self, gets=None, opcionais=None):
        self.gets, self.opcionais = gets or {}, opcionais or {}
        self.posts, self.patches = [], []

    def get(self, caminho, params=None, headers=None):
        return {"value": self.gets.get(caminho, [])}

    def get_todos(self, caminho, params=None, headers=None):
        return self.gets.get(caminho, [])

    def get_opcional(self, caminho, params=None):
        return self.opcionais.get(caminho)

    def post(self, caminho, corpo):
        self.posts.append((caminho, corpo))

    def patch(self, caminho, corpo):
        self.patches.append((caminho, corpo))


# ---------- notificações ----------

def test_notificacoes_seguem_o_circuito(db):
    db.query(Notificacao).delete()
    db.commit()
    joana, antonio, paulo = user(db, "joana"), user(db, "antonio"), user(db, "paulo")
    monitor = db.scalar(select(ItemCatalogo.id).where(ItemCatalogo.nome == "Monitor"))
    p = wf.criar(db, joana, titulo="Monitor", descricao="Segundo monitor", item_id=monitor, dados={"quantidade": "1"})
    dest = lambda: sorted(n.para.split("@")[0] for n in db.scalars(select(Notificacao).where(Notificacao.pedido_id == p.id)))
    # a própria Joana não recebe aviso do que fez; a DSI recebe o pedido de aprovação
    assert dest() == ["antonio.godinho"]
    wf.executar(db, antonio, p, "aprovar", {})
    assert "joana.sebastiao" in dest() and "paulo.cassule" in dest() and "edna.muhongo" in dest()
    wf.executar(db, paulo, p, "assumir", {})
    wf.comentar(db, paulo, p, "Notas internas", interno=True)
    n_antes = len(dest())
    wf.comentar(db, paulo, p, "Passo aí às 15h")
    assert len(dest()) == n_antes + 1  # nota interna não gera email; comentário público sim


def test_envio_simulado_e_real(db, monkeypatch):
    assert notificacoes.enviar_pendentes(db, None)["simuladas"] > 0
    n = Notificacao(para="joana.sebastiao@mhais.example", assunto="[PED-000001] Teste", corpo="<p>x</p>")
    db.add(n)
    db.commit()
    g = FakeGraph()
    assert notificacoes.enviar_pendentes(db, g) == {"enviadas": 1, "simuladas": 0, "erros": 0}
    caminho, corpo = g.posts[0]
    assert caminho == "/users/helpdesk@mhais.example/sendMail"
    assert corpo["message"]["toRecipients"][0]["emailAddress"]["address"] == "joana.sebastiao@mhais.example"

    class Falha(FakeGraph):
        def post(self, *_):
            raise RuntimeError("403 ErrorAccessDenied")

    db.add(Notificacao(para="x@mhais.example", assunto="a", corpo="b"))
    db.commit()
    assert notificacoes.enviar_pendentes(db, Falha())["erros"] == 1
    assert db.scalar(select(Notificacao).where(Notificacao.para == "x@mhais.example")).estado == "erro"


# ---------- pedidos por email ----------

def msg(id_, de, assunto, texto, cabecalhos=None):
    return {"id": id_, "internetMessageId": f"<{id_}@mail>", "subject": assunto,
            "from": {"emailAddress": {"address": de}}, "uniqueBody": {"content": texto},
            "receivedDateTime": f"2026-10-13T10:{id_[-2:]}:00Z", "internetMessageHeaders": cabecalhos or []}


def test_caixa_cria_pedidos_e_comentarios(db):
    existente = db.scalar(select(Pedido).where(Pedido.titulo.like("Outlook%")))
    caixa = "/users/helpdesk@mhais.example/mailFolders/inbox/messages"
    g = FakeGraph(gets={caixa: [
        msg("m01", "Teresa.Lukeny@mhais.example", "Scanner não digitaliza", "O scanner do 3.º piso não envia para o email."),
        msg("m02", "joana.sebastiao@mhais.example", f"RE: [{existente.numero}] Nova resposta da DSI: Outlook",
            "Já reiniciei e continua."),
        msg("m03", "estranho@gmail.com", "Olá", "spam"),
        msg("m04", "wilson.capitango@mhais.example", "Resposta automática: Ausente", "Fora do escritório",
            [{"name": "Auto-Submitted", "value": "auto-replied"}]),
    ]})
    assert correio.processar_caixa(db, g) == {"criado": 1, "comentario": 1, "ignorado": 2}
    novo = db.scalar(select(Pedido).where(Pedido.origem == "email"))
    assert novo.titulo == "Scanner não digitaliza" and novo.beneficiario.email.startswith("teresa")
    assert novo.estado == "novo" and novo.tipo == "outro"
    assert existente.comentarios[-1].texto == "Já reiniciei e continua."
    assert len(g.patches) == 4 and all(c == {"isRead": True} for _, c in g.patches)
    # se o email voltar a aparecer (ex.: falhou a marcação como lido), não é tratado outra vez
    assert correio.processar_caixa(db, g) == {"duplicado": 4}
    assert db.scalar(select(MensagemRecebida).where(MensagemRecebida.remetente == "estranho@gmail.com")).resultado == "ignorado"


def test_resposta_a_pedido_fechado_abre_pedido_novo(db):
    p = db.scalar(select(Pedido).where(Pedido.estado == "resolvido"))
    wf.executar(db, p.beneficiario, p, "fechar", {})
    assert correio.processar_mensagem(db, msg("m10", p.beneficiario.email, f"RE: [{p.numero}] Pedido resolvido: x",
                                              "Voltou a acontecer")) == "criado"


# ---------- sincronização com o Entra ID ----------

def test_sincronizacao_entra(db):
    db_users = len(db.scalars(select(Utilizador)).all())
    paulo = user(db, "paulo")
    g = FakeGraph(
        gets={"/users": [
            {"id": "oid-dir", "displayName": "Carla Mendes", "mail": "carla.mendes@mhais.example",
             "department": "Actuariado", "accountEnabled": True, "userType": "Member"},
            {"id": "oid-col", "displayName": "Nuno Lopes", "mail": "Nuno.Lopes@mhais.example",
             "department": "Actuariado", "accountEnabled": True, "userType": "Member"},
            {"id": "oid-paulo", "displayName": "Paulo Cassule", "mail": "paulo.cassule@mhais.example",
             "department": "DSI", "accountEnabled": True, "userType": "Member"},
            {"id": "oid-saiu", "displayName": "Domingos Pedro", "mail": "domingos.pedro@mhais.example",
             "department": "Recursos Humanos", "accountEnabled": False, "userType": "Member"},
            {"id": "oid-convidado", "displayName": "Consultor", "mail": "c@fornecedor.example",
             "accountEnabled": True, "userType": "Guest"},
            {"id": "oid-sala", "displayName": "Sala Reuniões", "mail": None, "accountEnabled": True},
        ]},
        opcionais={"/users/oid-col/manager": {"id": "oid-dir"}, "/users/oid-paulo/manager": {"id": "oid-col"}},
    )
    r = sincronizacao.sincronizar(db, g)
    assert r["criados"] == 2 and r["desactivados"] == 1
    carla, nuno = user(db, "carla"), user(db, "nuno")
    assert carla.perfil == "colaborador" and nuno.chefia_id == carla.id and nuno.email == "nuno.lopes@mhais.example"
    assert db.get(Departamento, nuno.departamento_id).nome == "Actuariado"
    assert user(db, "paulo").perfil == "helpdesk"  # perfis da DSI não são mexidos
    assert paulo.entra_oid == "oid-paulo" and paulo.chefia_id == nuno.id
    assert not user(db, "domingos").activo
    assert user(db, "c@fornecedor") is None
    # segunda execução não duplica nada
    r2 = sincronizacao.sincronizar(db, g)
    assert r2["criados"] == 0 and len(db.scalars(select(Utilizador)).all()) == db_users + 2


# ---------- início de sessão Microsoft ----------

def claims(**kw):
    base = {"tid": TENANT, "oid": "oid-joana", "preferred_username": "joana.sebastiao@mhais.example", "name": "Joana"}
    return {**base, **kw}


def test_claims_entra(db, monkeypatch):
    monkeypatch.setenv("ENTRA_TENANT_ID", TENANT)
    monkeypatch.setenv("PORTAL_ADMINS", "antonio.godinho@mhais.example")
    with pytest.raises(PermissionError):
        entra.utilizador_de_claims(db, claims(tid="outro-tenant"))
    joana = entra.utilizador_de_claims(db, claims())
    assert joana.email == "joana.sebastiao@mhais.example" and joana.entra_oid == "oid-joana"
    assert entra.utilizador_de_claims(db, claims(preferred_username="outro@x")).id == joana.id  # pelo oid
    novo = entra.utilizador_de_claims(db, claims(oid="oid-novo", preferred_username="novo@mhais.example", name="Novo"))
    assert novo.perfil == "colaborador"
    assert entra.utilizador_de_claims(db, claims(oid="oid-ag", preferred_username="Antonio.Godinho@mhais.example")).perfil == "admin"
    monkeypatch.setenv("PORTAL_AUTO_CRIAR", "0")
    with pytest.raises(PermissionError):
        entra.utilizador_de_claims(db, claims(oid="oid-x", preferred_username="x@mhais.example"))
    d = user(db, "domingos")
    d.activo = False
    db.commit()
    with pytest.raises(PermissionError):
        entra.utilizador_de_claims(db, claims(oid="oid-d", preferred_username=d.email))


def test_fluxo_login_entra(app_client, monkeypatch):
    monkeypatch.setenv("PORTAL_AUTH_MODE", "entra")
    monkeypatch.setenv("ENTRA_TENANT_ID", TENANT)

    class FakeMsal:
        def initiate_auth_code_flow(self, scopes, redirect_uri):
            return {"auth_uri": "https://login.microsoftonline.com/fake", "state": "s1", "redirect_uri": redirect_uri}

        def acquire_token_by_auth_code_flow(self, fluxo, params):
            if params.get("state") != fluxo["state"]:
                raise ValueError("state mismatch")
            return {"id_token_claims": claims()}

    monkeypatch.setattr(entra, "_app", lambda: FakeMsal())
    assert app_client.get("/api/auth/utilizadores-demo").status_code == 404  # login de demonstração desligado
    r = app_client.get("/auth/login", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].startswith("https://login.microsoftonline.com")
    r = app_client.get("/auth/callback", params={"code": "c", "state": "errado"}, follow_redirects=False)
    assert app_client.get("/api/eu").status_code == 401  # state inválido: não entra
    app_client.get("/auth/login", follow_redirects=False)
    r = app_client.get("/auth/callback", params={"code": "c", "state": "s1"}, follow_redirects=False)
    assert r.headers["location"] == "/#inicio"
    assert app_client.get("/api/eu").json()["email"] == "joana.sebastiao@mhais.example"


def test_admin_estado_e_notificacoes(app_client):
    with dbmod.SessionLocal() as s:
        uid = user(s, "antonio").id
    app_client.post("/api/auth/login", json={"utilizador_id": uid})
    e = app_client.get("/api/admin/estado").json()
    assert e["modo_autenticacao"] == "dev" and e["graph_configurado"] in (True, False)
    assert isinstance(app_client.get("/api/admin/notificacoes").json(), list)
    assert app_client.post("/api/admin/ciclo").json()["emails"]["simuladas"] >= 0
