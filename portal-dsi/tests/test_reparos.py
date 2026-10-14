"""Reparos do piloto: novidades, conversa, confirmação da resolução, pesquisa e prazos."""

from tests.test_portal import app_client, entrar, item  # noqa: F401  (fixture partilhada)


def _novo_pedido(c):
    entrar(c, "domingos.pedro")
    r = c.post("/api/pedidos", json={"descricao": "Demora 10 min a arrancar",
                                      "item_id": item(c, "Computador lento ou com erros"), "dados": {"sintomas": ["Muito lento"]}})
    return r.json()["id"]


def test_mensagens_geram_novidades_e_ficam_lidas_ao_abrir(app_client):
    c = app_client
    pid = _novo_pedido(c)
    entrar(c, "paulo.cassule")
    c.post(f"/api/pedidos/{pid}/accoes/assumir", json={})
    c.post(f"/api/pedidos/{pid}/comentarios", json={"texto": "Podes reiniciar o PC?"})
    c.post(f"/api/pedidos/{pid}/comentarios", json={"texto": "Só para a DSI", "interno": True})

    entrar(c, "domingos.pedro")
    n = c.get("/api/novidades").json()
    assert pid in n["pedidos"]
    textos = [i["texto"] for i in n["itens"] if i["pedido_id"] == pid]
    assert "Podes reiniciar o PC?" in textos and "Só para a DSI" not in textos
    lista = c.get("/api/pedidos").json()
    assert next(p for p in lista if p["id"] == pid)["novidade"] is True

    d = c.get(f"/api/pedidos/{pid}").json()  # abrir marca como lido
    assert [m["texto"] for m in d["conversa"]] == ["Podes reiniciar o PC?"]
    assert pid not in c.get("/api/novidades").json()["pedidos"]

    c.post(f"/api/pedidos/{pid}/comentarios", json={"texto": "Já reiniciei, continua lento"})
    entrar(c, "paulo.cassule")
    n = c.get("/api/novidades").json()
    assert any(i["pedido_id"] == pid and i["tipo"] == "mensagem" for i in n["itens"])
    assert c.post("/api/novidades/lidas").json()["marcadas"] >= 1
    assert c.get("/api/novidades").json()["total"] == 0


def test_resolucao_pede_confirmacao_ao_requerente(app_client):
    c = app_client
    pid = _novo_pedido(c)
    entrar(c, "paulo.cassule")
    c.post(f"/api/pedidos/{pid}/accoes/assumir", json={})
    c.post(f"/api/pedidos/{pid}/accoes/resolver", json={"motivo": "Limpeza de arranque"})
    d = c.get(f"/api/pedidos/{pid}").json()
    assert "fechar" not in d["accoes"]  # o técnico não fecha: quem pediu confirma

    entrar(c, "domingos.pedro")
    n = c.get("/api/novidades").json()
    assert any("confirma" in i["texto"] for i in n["itens"] if i["pedido_id"] == pid)
    d = c.get(f"/api/pedidos/{pid}").json()
    assert {"fechar", "reabrir"} <= set(d["accoes"])
    assert d["solucao"] == "Limpeza de arranque" and d["fecho_automatico_em"]
    assert any(m["tipo"] == "evento" and m["accao"] == "resolvido" for m in d["conversa"])

    # fecha e ainda pode reabrir se o problema voltar
    assert c.post(f"/api/pedidos/{pid}/accoes/fechar", json={}).json()["estado"] == "fechado"
    assert "reabrir" in c.get(f"/api/pedidos/{pid}").json()["accoes"]
    assert c.post(f"/api/pedidos/{pid}/accoes/reabrir", json={"motivo": "Voltou a ficar lento"}).json()["estado"] == "em_curso"
    entrar(c, "paulo.cassule")
    assert any(i["pedido_id"] == pid and "reaberto" in i["texto"] for i in c.get("/api/novidades").json()["itens"])


def test_tecnico_nao_consegue_fechar(app_client):
    c = app_client
    pid = _novo_pedido(c)
    entrar(c, "paulo.cassule")
    c.post(f"/api/pedidos/{pid}/accoes/assumir", json={})
    c.post(f"/api/pedidos/{pid}/accoes/resolver", json={"motivo": "Feito"})
    r = c.post(f"/api/pedidos/{pid}/accoes/fechar", json={})
    assert r.status_code in (403, 409) and c.get(f"/api/pedidos/{pid}").json()["estado"] == "resolvido"


def test_pesquisa_por_numero_parcial(app_client):
    c = app_client
    pid = _novo_pedido(c)
    entrar(c, "paulo.cassule")
    for q in (str(pid), f"0{pid}", f"PED-{pid:06d}", f"ped {pid}"):
        r = c.get("/api/pedidos", params={"vista": "todos", "estado": "", "q": q}).json()
        assert r and r[0]["id"] == pid, q  # o número exacto aparece primeiro
    nome = c.get("/api/pedidos", params={"vista": "todos", "estado": "", "q": "Domingos"}).json()
    assert any(p["id"] == pid for p in nome)


def test_prazos_visiveis_para_o_colaborador(app_client):
    c = app_client
    pid = _novo_pedido(c)
    p = next(x for x in c.get("/api/pedidos").json() if x["id"] == pid)
    assert p["prazo_resolucao"] and p["prazo_resposta"] and p["sla"] == "ok"
    d = c.get(f"/api/pedidos/{pid}").json()
    assert d["prazo_resposta"] and d["prazo_resolucao"]
