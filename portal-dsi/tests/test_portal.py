from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from portal import db as dbmod, sla
from portal.models import Pedido, Utilizador


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setenv("PORTAL_SEED", "1")
    monkeypatch.setenv("PORTAL_AUTH_MODE", "dev")
    monkeypatch.setenv("PORTAL_TAREFAS", "0")
    dbmod.configure("sqlite://")
    from portal.main import app

    with TestClient(app) as c:
        yield c
    dbmod.Base.metadata.drop_all(dbmod.engine)


def uid(email_prefixo: str) -> int:
    with dbmod.SessionLocal() as db:
        return db.scalar(select(Utilizador.id).where(Utilizador.email.startswith(email_prefixo)))


def entrar(c: TestClient, prefixo: str) -> int:
    i = uid(prefixo)
    assert c.post("/api/auth/login", json={"utilizador_id": i}).status_code == 200
    return i


def item(c, nome):
    return next(x["id"] for x in c.get("/api/catalogo").json() if x["nome"] == nome)


# ---------- SLA ----------

def test_horas_uteis_saltam_noite_e_fim_de_semana():
    sexta_16h = datetime(2026, 10, 16, 16, 0)
    assert sla.somar_horas_uteis(sexta_16h, 2) == datetime(2026, 10, 19, 9, 0)  # segunda 09:00
    sabado = datetime(2026, 10, 17, 11, 0)
    assert sla.somar_horas_uteis(sabado, 1) == datetime(2026, 10, 19, 9, 0)
    assert sla.somar_horas_uteis(datetime(2026, 10, 14, 7, 0), 9) == datetime(2026, 10, 14, 17, 0)
    resp, resol = sla.prazos("critica", sexta_16h)
    assert resol == sexta_16h + timedelta(hours=4)  # crítica conta horas corridas


# ---------- sessão e permissões ----------

def test_sem_sessao_devolve_401(app_client):
    assert app_client.get("/api/pedidos").status_code == 401
    assert app_client.get("/api/eu").status_code == 401


def test_colaborador_nao_ve_pedidos_alheios_nem_inventario(app_client):
    entrar(app_client, "joana.sebastiao")
    meus = app_client.get("/api/pedidos").json()
    assert meus and all("Joana" in p["beneficiario"] or "Joana" in p["criado_por"] for p in meus)
    assert app_client.get("/api/pedidos", params={"vista": "todos"}).status_code == 400
    assert app_client.get("/api/equipamentos").status_code == 403
    alheio = next(p for p in _todos_pedidos() if p.beneficiario.email.startswith("wilson"))
    assert app_client.get(f"/api/pedidos/{alheio.id}").status_code == 404
    assert app_client.post("/api/catalogo", json={"nome": "X1", "tipo": "incidente"}).status_code == 403


def _todos_pedidos():
    with dbmod.SessionLocal() as db:
        ps = db.scalars(select(Pedido)).all()
        for p in ps:
            _ = p.beneficiario.email
        return ps


# ---------- circuito ----------

def test_incidente_vai_directo_para_novo_e_helpdesk_resolve(app_client):
    entrar(app_client, "domingos.pedro")
    r = app_client.post("/api/pedidos", json={"titulo": "PC lento", "descricao": "Demora 10 min a arrancar",
                                               "item_id": item(app_client, "Avaria ou erro em computador")})
    assert r.status_code == 201 and r.json()["estado"] == "novo"
    pid = r.json()["id"]
    assert "cancelar" in app_client.get(f"/api/pedidos/{pid}").json()["accoes"]

    entrar(app_client, "paulo.cassule")
    assert app_client.post(f"/api/pedidos/{pid}/accoes/assumir", json={}).json()["estado"] == "em_curso"
    assert app_client.post(f"/api/pedidos/{pid}/accoes/resolver", json={}).status_code == 409  # falta a solução
    app_client.post(f"/api/pedidos/{pid}/comentarios", json={"texto": "Nota interna", "interno": True})
    assert app_client.post(f"/api/pedidos/{pid}/accoes/resolver",
                           json={"motivo": "Disco substituído por SSD"}).json()["estado"] == "resolvido"

    entrar(app_client, "domingos.pedro")
    d = app_client.get(f"/api/pedidos/{pid}").json()
    assert not any(c["interno"] for c in d["comentarios"])  # notas internas escondidas
    assert d["sla"] == "cumprido"
    assert app_client.post(f"/api/pedidos/{pid}/accoes/reabrir", json={}).status_code == 409
    assert app_client.post(f"/api/pedidos/{pid}/accoes/fechar", json={}).json()["estado"] == "fechado"
    assert app_client.post(f"/api/pedidos/{pid}/comentarios", json={"texto": "x"}).status_code == 409


def test_pedido_em_nome_de_outro_com_aprovacao_da_chefia_e_entrega(app_client):
    # O Helpdesk pede um monitor em nome da Joana; aprova a chefia dela (Helena).
    entrar(app_client, "paulo.cassule")
    joana = uid("joana.sebastiao")
    r = app_client.post("/api/pedidos", json={"titulo": "Monitor adicional", "descricao": "Pedido por telefone",
                                               "beneficiario_id": joana, "item_id": item(app_client, "Monitor")})
    pid = r.json()["id"]
    assert r.json()["estado"] == "em_aprovacao"
    assert app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={}).status_code == 403  # Helpdesk não aprova

    entrar(app_client, "joana.sebastiao")
    assert any(p["id"] == pid for p in app_client.get("/api/pedidos").json())  # beneficiária vê o pedido
    assert app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={}).status_code == 403

    entrar(app_client, "helena.tavares")
    assert pid in [p["id"] for p in app_client.get("/api/pedidos", params={"vista": "aprovar"}).json()]
    assert app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={}).json()["estado"] == "novo"

    entrar(app_client, "edna.muhongo")
    monitores = app_client.get("/api/equipamentos", params={"tipo": "Monitor", "estado": "stock"}).json()
    r = app_client.post(f"/api/pedidos/{pid}/accoes/entregar_equipamento", json={"equipamento_id": monitores[0]["id"]})
    assert r.status_code == 200
    eq = next(e for e in app_client.get("/api/equipamentos").json() if e["id"] == monitores[0]["id"])
    assert eq["estado"] == "atribuido" and eq["utilizador_id"] == joana
    # o mesmo equipamento não pode ser entregue duas vezes
    assert app_client.post(f"/api/pedidos/{pid}/accoes/entregar_equipamento",
                           json={"equipamento_id": monitores[0]["id"]}).status_code == 409
    eventos = [e["accao"] for e in app_client.get(f"/api/pedidos/{pid}").json()["eventos"]]
    assert eventos[:4] == ["criado", "aguarda_aprovacao", "aprovado", "equipamento_entregue"]


def test_recusa_exige_motivo(app_client):
    entrar(app_client, "ricardo.manuel")
    pid = app_client.post("/api/pedidos", json={"titulo": "Pen drive", "descricao": "Para apresentações",
                                                 "item_id": item(app_client, "Pen drive")}).json()["id"]
    entrar(app_client, "helena.tavares")
    assert app_client.post(f"/api/pedidos/{pid}/accoes/recusar", json={}).status_code == 409
    assert app_client.post(f"/api/pedidos/{pid}/accoes/recusar",
                           json={"motivo": "Usar o OneDrive"}).json()["estado"] == "recusado"


def test_chefia_que_pede_para_a_equipa_aprova_automaticamente(app_client):
    entrar(app_client, "helena.tavares")
    r = app_client.post("/api/pedidos", json={"titulo": "VPN para o Ricardo", "descricao": "Trabalho remoto",
                                               "beneficiario_id": uid("ricardo.manuel"),
                                               "item_id": item(app_client, "Acesso VPN")})
    assert r.json()["estado"] == "novo"


def test_licencas_controlam_disponiveis(app_client):
    entrar(app_client, "antonio.godinho")
    pbi = next(l for l in app_client.get("/api/licencas").json() if l["produto"] == "Power BI Pro")
    assert pbi["livres"] == 0
    pid = app_client.post("/api/pedidos", json={"titulo": "Power BI", "descricao": "Relatórios comerciais",
                                                 "beneficiario_id": uid("joana.sebastiao"),
                                                 "item_id": item(app_client, "Licença Power BI Pro")}).json()["id"]
    app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={})  # admin pode aprovar
    r = app_client.post(f"/api/pedidos/{pid}/accoes/atribuir_licenca", json={"licenca_id": pbi["id"]})
    assert r.status_code == 409 and "Sem licenças livres" in r.json()["detail"]
    app_client.patch(f"/api/licencas/{pbi['id']}", json={"quantidade": 5})
    assert app_client.post(f"/api/pedidos/{pid}/accoes/atribuir_licenca",
                           json={"licenca_id": pbi["id"]}).status_code == 200
    assert next(l for l in app_client.get("/api/licencas").json() if l["id"] == pbi["id"])["livres"] == 1


def test_critica_so_pela_dsi(app_client):
    entrar(app_client, "joana.sebastiao")
    pid = app_client.post("/api/pedidos", json={"titulo": "Urgente", "descricao": "Tudo parado",
                                                 "tipo": "incidente", "prioridade": "critica"}).json()["id"]
    assert app_client.get(f"/api/pedidos/{pid}").json()["prioridade"] == "alta"


def test_painel_e_inicio(app_client):
    entrar(app_client, "antonio.godinho")
    p = app_client.get("/api/painel").json()
    assert p["abertos"] == 4 and p["sla_violado"] >= 1
    assert p["equipamentos_por_estado"]["stock"] == 5
    assert any(l["produto"] == "Microsoft 365 Business Premium" for l in p["licencas_a_renovar"])
    entrar(app_client, "helena.tavares")
    assert app_client.get("/api/painel").status_code == 403
    ini = app_client.get("/api/inicio").json()
    assert len(ini["para_aprovar"]) == 1 and ini["licencas"]


def test_fecho_automatico(app_client):
    with dbmod.SessionLocal() as db:
        p = db.scalar(select(Pedido).where(Pedido.estado == "resolvido"))
        p.resolvido_em = datetime.now() - timedelta(days=6)
        db.commit()
        pid = p.id
    entrar(app_client, "antonio.godinho")
    app_client.get("/api/pedidos")
    assert app_client.get(f"/api/pedidos/{pid}").json()["estado"] == "fechado"


def test_interface_servida(app_client):
    assert "Portal DSI" in app_client.get("/").text
