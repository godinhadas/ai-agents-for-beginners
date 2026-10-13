"""Tarefas em segundo plano: envio de emails, leitura da caixa, fecho automático e sincronização.

Correm dentro do próprio servidor, num ciclo a cada PORTAL_INTERVALO_SEG segundos (60 por omissão).
Pressupõe um único processo do servidor (uvicorn sem --workers), caso contrário as tarefas duplicam.
"""

import asyncio
import logging
import os
from datetime import datetime

from . import correio, db as dbmod, graph as graphmod, notificacoes, pedidos as wf, sincronizacao

log = logging.getLogger("portal.tarefas")
estado: dict = {"ultimo_ciclo": None, "ultima_sync": None, "resultados": {}}


def ciclo(forcar_sync: bool = False) -> dict:
    g = None
    if graphmod.configurado():
        try:
            g = graphmod.Graph()
        except Exception as exc:
            log.warning("Graph indisponível: %s", exc)
    res: dict = {}
    with dbmod.SessionLocal() as db:
        passos = [("fecho_automatico", lambda: wf.fechar_automaticamente(db))]
        if g and os.getenv("PORTAL_LER_CAIXA", "0") == "1":
            passos.append(("caixa", lambda: correio.processar_caixa(db, g)))
        passos.append(("emails", lambda: notificacoes.enviar_pendentes(db, g)))
        horas = float(os.getenv("PORTAL_SYNC_HORAS", "24"))
        ultima = estado["ultima_sync"]
        if g and (forcar_sync or ultima is None or (datetime.now() - ultima).total_seconds() >= horas * 3600):
            passos.append(("sincronizacao", lambda: sincronizacao.sincronizar(db, g)))
            estado["ultima_sync"] = datetime.now()
        for nome, fn in passos:
            try:
                res[nome] = fn()
            except Exception as exc:
                db.rollback()
                res[nome] = {"erro": str(exc)[:300]}
                log.exception("Tarefa %s falhou", nome)
    estado["ultimo_ciclo"] = datetime.now()
    estado["resultados"] = res
    return res


async def correr_para_sempre():
    intervalo = int(os.getenv("PORTAL_INTERVALO_SEG", "60"))
    while True:
        await asyncio.sleep(intervalo)
        await asyncio.to_thread(ciclo)
