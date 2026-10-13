"""Linha de comandos: python -m portal.sincronizar"""

import json
import logging

from dotenv import load_dotenv

from . import db as dbmod
from .graph import Graph
from .sincronizacao import sincronizar

if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    dbmod.init_db()
    with dbmod.SessionLocal() as db:
        print(json.dumps(sincronizar(db, Graph()), ensure_ascii=False, indent=2))
