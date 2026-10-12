import json
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from crm import agent, db as dbmod


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("CRM_SEED", "1")
    dbmod.configure("sqlite://")
    from crm.main import app

    with TestClient(app) as c:
        yield c
    dbmod.Base.metadata.drop_all(dbmod.engine)


def test_painel_com_dados_demo(client):
    p = client.get("/api/painel").json()
    assert p["clientes"] == 6
    assert p["apolices_activas"] == 6
    assert p["renovacoes_30"] == 2  # AUT-0001 (20 dias) e AUT-0005 (10 dias)
    assert p["sinistros_abertos"] == 2
    assert p["pipeline_aberto"] == 7_500_000 + 41_000_000 + 5_200_000


def test_crud_cliente_e_unicidade_nif(client):
    novo = {"tipo": "particular", "nome": "Ana Teste", "nif": "009999999LA001", "provincia": "Luanda"}
    r = client.post("/api/clientes", json=novo)
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.post("/api/clientes", json=novo).status_code == 409
    assert client.patch(f"/api/clientes/{cid}", json={"telefone": "+244 900 000 000"}).json()["telefone"]
    assert client.get("/api/clientes", params={"q": "Ana Teste"}).json()[0]["id"] == cid
    assert client.delete(f"/api/clientes/{cid}").status_code == 204
    assert client.get(f"/api/clientes/{cid}").status_code == 404


def test_validacoes_apolice(client):
    base = {"numero": "X-1", "cliente_id": 1, "ramo": "Automóvel", "premio_anual": 1000,
            "data_inicio": "2026-01-01", "data_fim": "2025-01-01"}
    assert client.post("/api/apolices", json=base).status_code == 422  # datas invertidas
    assert client.post("/api/apolices", json={**base, "data_fim": "2027-01-01", "cliente_id": 999}).status_code == 422
    assert client.post("/api/apolices", json={**base, "data_fim": "2027-01-01", "ramo": "Inexistente"}).status_code == 422
    r = client.post("/api/apolices", json={**base, "data_fim": "2027-01-01"})
    assert r.status_code == 201
    # PATCH parcial que torna as datas inválidas tem de ser recusado
    assert client.patch(f"/api/apolices/{r.json()['id']}", json={"data_fim": "2025-06-01"}).status_code == 422
    assert client.patch(f"/api/apolices/{r.json()['id']}", json={"premio_anual": -5}).status_code == 422


def test_apagar_cliente_com_apolices_recusado(client):
    assert client.delete("/api/clientes/1").status_code == 409


def test_visao_360_e_renovacoes(client):
    v = client.get("/api/clientes/1/360").json()
    assert v["cliente"]["nome"].startswith("Construções Kalandula")
    assert {a["numero"] for a in v["apolices"]} == {"AT-2025-0002", "MR-2025-0003"}
    ren = client.get("/api/renovacoes", params={"dias": 30}).json()
    assert [r["numero"] for r in ren] == ["AUT-2025-0005", "AUT-2025-0001"]
    assert client.get("/api/clientes/999/360").status_code == 404


def test_filtros_lista(client):
    assert all(a["estado"] == "activa" for a in client.get("/api/apolices", params={"estado": "activa"}).json())
    assert len(client.get("/api/oportunidades", params={"cliente_id": 1}).json()) == 1


def test_chat_sem_credenciais_devolve_503(client, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CRM_LLM_API_KEY", raising=False)
    r = client.post("/api/agente/chat", json={"mensagens": [{"role": "user", "content": "olá"}]})
    assert r.status_code == 503


class _FakeLLM:
    """Simula um modelo que pede uma ferramenta e depois responde."""

    def __init__(self, chamadas):
        self.chamadas = list(chamadas)
        self.recebido = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.recebido.append(list(kw["messages"]))
        nome, args = self.chamadas.pop(0) if self.chamadas else (None, None)
        if nome:
            tc = SimpleNamespace(id=f"call_{len(self.recebido)}",
                                 function=SimpleNamespace(name=nome, arguments=json.dumps(args)))
            msg = SimpleNamespace(content=None, tool_calls=[tc])
        else:
            msg = SimpleNamespace(content="Resposta final", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_agente_usa_ferramentas_e_regista_actividade(client):
    fake = _FakeLLM([
        ("renovacoes", {"dias": 30}),
        ("registar_actividade", {"cliente_id": 3, "tipo": "chamada", "assunto": "Lembrete de renovação"}),
    ])
    with dbmod.SessionLocal() as db:
        out = agent.conversar(db, [{"role": "user", "content": "renovações?"}], cliente_llm=fake)
    assert out["resposta"] == "Resposta final"
    assert [a["ferramenta"] for a in out["accoes"]] == ["renovacoes", "registar_actividade"]
    resultado_renov = json.loads(fake.recebido[1][-1]["content"])
    assert resultado_renov[0]["numero"] == "AUT-2025-0005"
    acts = client.get("/api/actividades", params={"cliente_id": 3}).json()
    assert any(a["assunto"] == "Lembrete de renovação" and a["data"] == date.today().isoformat() for a in acts)


def test_ferramenta_com_erro_volta_ao_modelo(client):
    with dbmod.SessionLocal() as db:
        assert "erro" in agent.executar_ferramenta(db, "registar_actividade",
                                                   json.dumps({"cliente_id": 999, "tipo": "nota", "assunto": "x"}))
        assert "erro" in agent.executar_ferramenta(db, "nao_existe", "{}")
        assert "erro" in agent.executar_ferramenta(db, "visao_cliente", '{"cliente_id": 999}')
        assert agent.executar_ferramenta(db, "pesquisar_clientes", '{"texto": "Benguela"}')[0]["id"] == 2


def test_agente_limita_iteracoes(client):
    fake = _FakeLLM([("pipeline", {})] * (agent.MAX_ITERACOES + 2))
    with dbmod.SessionLocal() as db:
        out = agent.conversar(db, [{"role": "user", "content": "loop"}], cliente_llm=fake)
    assert len(out["accoes"]) == agent.MAX_ITERACOES
    assert "limite" in out["resposta"]


def test_interface_servida(client):
    r = client.get("/")
    assert r.status_code == 200 and "CRM" in r.text
