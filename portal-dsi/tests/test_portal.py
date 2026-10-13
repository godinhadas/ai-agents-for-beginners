from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from portal import db as dbmod, sla
from portal.models import Pedido, Utilizador


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setenv("PORTAL_SEED", "demo")
    monkeypatch.setenv("PORTAL_AUTH_MODE", "dev")
    monkeypatch.setenv("PORTAL_TAREFAS", "0")
    monkeypatch.setenv("PORTAL_INVENTARIO", "1")
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
    assert app_client.post("/api/catalogo", json={"nome": "X1", "tipo": "outro"}).status_code == 403


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
                                               "item_id": item(app_client, "Computador lento ou com erros"), "dados": {"sintomas": ["Muito lento"]}})
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


def test_pedido_em_nome_de_outro_com_aprovacao_da_dsi_e_entrega(app_client):
    # O Helpdesk pede um monitor em nome da Joana; só a DSI (administrador) aprova.
    entrar(app_client, "paulo.cassule")
    joana = uid("joana.sebastiao")
    r = app_client.post("/api/pedidos", json={"titulo": "Monitor adicional", "descricao": "Pedido por telefone",
                                               "beneficiario_id": joana, "item_id": item(app_client, "Monitor"), "dados": {"quantidade": "1"}})
    pid = r.json()["id"]
    assert r.json()["estado"] == "em_aprovacao"
    assert app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={}).status_code == 403  # Helpdesk não aprova

    entrar(app_client, "joana.sebastiao")
    assert any(p["id"] == pid for p in app_client.get("/api/pedidos").json())  # beneficiária vê o pedido
    assert app_client.post(f"/api/pedidos/{pid}/accoes/aprovar", json={}).status_code == 403

    assert app_client.get("/api/pedidos", params={"vista": "aprovar"}).status_code == 400  # colaborador não aprova
    entrar(app_client, "antonio.godinho")
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
                                                 "item_id": item(app_client, "Pen drive ou disco externo"), "dados": {"capacidade": "64 GB"}}).json()["id"]
    entrar(app_client, "antonio.godinho")
    assert app_client.post(f"/api/pedidos/{pid}/accoes/recusar", json={}).status_code == 409
    assert app_client.post(f"/api/pedidos/{pid}/accoes/recusar",
                           json={"motivo": "Usar o OneDrive"}).json()["estado"] == "recusado"


def test_pedido_registado_pela_dsi_fica_aprovado(app_client):
    entrar(app_client, "antonio.godinho")
    r = app_client.post("/api/pedidos", json={"titulo": "VPN para o Ricardo", "descricao": "Trabalho remoto",
                                               "beneficiario_id": uid("ricardo.manuel"),
                                               "item_id": item(app_client, "VPN e acesso remoto"), "dados": {"periodo": "Permanente"}})
    assert r.json()["estado"] == "novo"


def test_catalogo_base_sem_dados_de_teste(monkeypatch):
    monkeypatch.setenv("PORTAL_SEED", "0")
    monkeypatch.setenv("PORTAL_AUTH_MODE", "dev")
    monkeypatch.setenv("PORTAL_TAREFAS", "0")
    monkeypatch.setenv("PORTAL_INVENTARIO", "1")
    monkeypatch.setenv("PORTAL_ADMINS", "antonio.godinho@mhais.co.ao")
    dbmod.configure("sqlite://")
    from portal.main import app

    with TestClient(app) as c:
        us = c.get("/api/auth/utilizadores-demo").json()
        assert [(u["nome"], u["perfil"]) for u in us] == [("Antonio Godinho", "admin")]
        c.post("/api/auth/login", json={"utilizador_id": us[0]["id"]})
        assert c.get("/api/pedidos").json() == [] and c.get("/api/equipamentos").json() == []
        tipos = {i["tipo"] for i in c.get("/api/catalogo").json()}
        assert tipos == {"acesso", "anywhere", "equipamento", "licenca", "intervencao", "outro"}
    dbmod.Base.metadata.drop_all(dbmod.engine)


def test_licencas_controlam_disponiveis(app_client):
    entrar(app_client, "antonio.godinho")
    pbi = next(l for l in app_client.get("/api/licencas").json() if l["produto"] == "Power BI Pro")
    assert pbi["livres"] == 0
    pid = app_client.post("/api/pedidos", json={"titulo": "Power BI", "descricao": "Relatórios comerciais",
                                                 "beneficiario_id": uid("joana.sebastiao"),
                                                 "item_id": item(app_client, "Licença Microsoft 365"), "dados": {"licencas": ["Power BI Pro"]}}).json()["id"]
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
                                                 "tipo": "intervencao", "prioridade": "critica"}).json()["id"]
    assert app_client.get(f"/api/pedidos/{pid}").json()["prioridade"] == "alta"


def test_painel_e_inicio(app_client):
    entrar(app_client, "antonio.godinho")
    p = app_client.get("/api/painel").json()
    assert p["abertos"] == 4 and p["sla_violado"] >= 1
    assert p["equipamentos_por_estado"]["stock"] == 4
    assert any(l["produto"] == "Microsoft 365 Business Premium" for l in p["licencas_a_renovar"])
    assert len(app_client.get("/api/inicio").json()["para_aprovar"]) == 1
    entrar(app_client, "joana.sebastiao")
    assert app_client.get("/api/painel").status_code == 403
    ini = app_client.get("/api/inicio").json()
    assert ini["para_aprovar"] == [] and ini["licencas"] and ini["equipamentos"]


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
    assert "Gestor de Pedidos DSI" in app_client.get("/").text


# ---------- formulários guiados ----------

def test_formulario_guiado_valida_e_gera_titulo(app_client):
    entrar(app_client, "joana.sebastiao")
    sw = item(app_client, "Instalação de software")
    r = app_client.post("/api/pedidos", json={"item_id": sw, "dados": {}})
    assert r.status_code == 409 and "Que programas?" in r.json()["detail"]
    r = app_client.post("/api/pedidos", json={"item_id": item(app_client, "Monitor"), "dados": {"quantidade": "7"}})
    assert r.status_code == 409 and "opção inválida" in r.json()["detail"]
    # lista padrão + "outro" escrito à mão, sem descrição
    r = app_client.post("/api/pedidos", json={"item_id": sw, "dados": {"software": ["7-Zip", "SPSS 29"]}})
    assert r.status_code == 201
    d = app_client.get(f"/api/pedidos/{r.json()['id']}").json()
    assert d["titulo"] == "Instalação de software: 7-Zip, SPSS 29"
    assert d["respostas"] == [{"campo": "Que programas?", "valor": "7-Zip, SPSS 29"}]
    # sem formulário ("Outro pedido") a descrição continua obrigatória
    assert app_client.post("/api/pedidos", json={"item_id": item(app_client, "Outro pedido")}).status_code == 409


def test_catalogo_rejeita_campos_mal_definidos(app_client):
    entrar(app_client, "antonio.godinho")
    base = {"nome": "Teste", "tipo": "outro"}
    assert app_client.post("/api/catalogo", json={**base, "campos": "{nao json"}).status_code == 422
    assert app_client.post("/api/catalogo", json={**base, "campos": '[{"id": "x", "rotulo": "X", "tipo": "opcoes"}]'}).status_code == 422
    assert app_client.post("/api/catalogo", json={**base, "campos": '[{"id": "x", "rotulo": "X", "tipo": "texto"}]'}).status_code == 201


# ---------- automação: desbloquear conta no AD ----------

@pytest.fixture()
def ad_falso(monkeypatch):
    from portal import automacoes

    chamadas = []

    def executor(script):
        chamadas.append(script)
        return 0, "DESBLOQUEADA jsebastiao"

    monkeypatch.setattr(automacoes, "executor", executor)
    monkeypatch.setenv("PORTAL_AUTOMACAO_AD", "1")
    return chamadas


def _desbloqueio(app_client, sistema="Windows / rede", para=None):
    corpo = {"item_id": item(app_client, "Desbloquear conta ou repor palavra-passe"),
             "dados": {"sistema": sistema, "situacao": "Conta bloqueada"}}
    if para:
        corpo["beneficiario_id"] = uid(para)
    return app_client.post("/api/pedidos", json=corpo).json()["id"]


def test_automacao_com_um_clique_do_tecnico(app_client, ad_falso):
    entrar(app_client, "joana.sebastiao")
    pid = _desbloqueio(app_client)
    assert app_client.get(f"/api/pedidos/{pid}").json()["estado"] == "novo"  # sem modo imediato, espera técnico
    assert "automatizar" not in app_client.get(f"/api/pedidos/{pid}").json()["accoes"]
    entrar(app_client, "paulo.cassule")
    d = app_client.get(f"/api/pedidos/{pid}").json()
    assert d["accoes"][0] == "automatizar" and d["automacao"] == "Desbloquear conta no Active Directory"
    assert app_client.post(f"/api/pedidos/{pid}/accoes/automatizar", json={}).json()["estado"] == "resolvido"
    assert "joana.sebastiao@mhais.example" in ad_falso[0]
    eventos = [e["accao"] for e in app_client.get(f"/api/pedidos/{pid}").json()["eventos"]]
    assert eventos[-2:] == ["automacao", "resolvido"]


def test_automacao_imediata_so_para_o_proprio(app_client, ad_falso, monkeypatch):
    monkeypatch.setenv("PORTAL_AUTOMACAO_IMEDIATA", "1")
    entrar(app_client, "joana.sebastiao")
    proprio = _desbloqueio(app_client)
    assert app_client.get(f"/api/pedidos/{proprio}").json()["estado"] == "resolvido"
    outro = _desbloqueio(app_client, para="ricardo.manuel")  # A pede para B: passa sempre por um técnico
    assert app_client.get(f"/api/pedidos/{outro}").json()["estado"] == "novo"
    anywhere = _desbloqueio(app_client, sistema="Anywhere")  # automação só para contas Windows
    assert app_client.get(f"/api/pedidos/{anywhere}").json()["estado"] == "novo"
    assert len(ad_falso) == 1


def test_automacao_falhada_fica_para_o_tecnico(app_client, monkeypatch):
    from portal import automacoes

    monkeypatch.setenv("PORTAL_AUTOMACAO_AD", "1")
    monkeypatch.setattr(automacoes, "executor", lambda s: (2, "NAO_ENCONTRADO"))
    entrar(app_client, "joana.sebastiao")
    pid = _desbloqueio(app_client)
    entrar(app_client, "paulo.cassule")
    assert app_client.post(f"/api/pedidos/{pid}/accoes/automatizar", json={}).json()["estado"] == "novo"
    ev = app_client.get(f"/api/pedidos/{pid}").json()["eventos"][-1]
    assert ev["accao"] == "automacao" and "não encontrado" in ev["detalhe"]


def test_automacao_recusa_email_perigoso():
    from portal.automacoes import desbloquear_ad

    ok, msg = desbloquear_ad("x'; Remove-ADUser -Identity admin; '@mhais.co.ao")
    assert not ok and "formato inválido" in msg
