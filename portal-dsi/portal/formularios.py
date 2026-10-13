"""Formulários guiados por item do catálogo: o colaborador responde com cliques.

Cada item tem uma lista de campos em JSON, por exemplo:
  [{"id": "sistema", "rotulo": "Que conta?", "tipo": "opcoes",
    "opcoes": ["Windows / rede", "Anywhere"], "obrigatorio": true},
   {"id": "software", "rotulo": "Que programas?", "tipo": "multi",
    "opcoes": ["Google Chrome", "7-Zip"], "outro": true}]

Tipos: opcoes (escolha única), multi (várias, com "outro" opcional para escrever),
texto (linha curta) e data.
"""

import json
from datetime import date

TIPOS = ("opcoes", "multi", "texto", "data")


def ler(campos_json: str | None) -> list[dict]:
    if not campos_json:
        return []
    campos = json.loads(campos_json)
    if not isinstance(campos, list):
        raise ValueError("Os campos têm de ser uma lista.")
    for c in campos:
        if not isinstance(c, dict) or not c.get("id") or not c.get("rotulo") or c.get("tipo") not in TIPOS:
            raise ValueError(f"Campo mal definido: {c}. Precisa de id, rotulo e tipo ({', '.join(TIPOS)}).")
        if c["tipo"] in ("opcoes", "multi") and not c.get("opcoes"):
            raise ValueError(f"O campo {c['id']} precisa de opcoes.")
    return campos


def validar(campos_json: str | None, dados: dict | None) -> dict:
    """Confirma as respostas e devolve-as limpas (só os campos conhecidos)."""
    dados = dados or {}
    limpo: dict = {}
    for c in ler(campos_json):
        v = dados.get(c["id"])
        if c["tipo"] == "multi":
            v = [x for x in (v or []) if isinstance(x, str) and x.strip()]
            invalidos = [x for x in v if x not in c["opcoes"] and not c.get("outro")]
            if invalidos:
                raise ValueError(f"{c['rotulo']}: opção inválida ({', '.join(invalidos)}).")
            v = [x.strip()[:120] for x in v]
        elif c["tipo"] == "opcoes":
            v = (v or "").strip() if isinstance(v, str) else ""
            if v and v not in c["opcoes"]:
                raise ValueError(f"{c['rotulo']}: opção inválida ({v}).")
        elif c["tipo"] == "data":
            v = (v or "").strip() if isinstance(v, str) else ""
            if v:
                date.fromisoformat(v)
        else:
            v = (v or "").strip()[:300] if isinstance(v, str) else ""
        if c.get("obrigatorio") and not v:
            raise ValueError(f"Falta responder: {c['rotulo']}")
        if v:
            limpo[c["id"]] = v
    return limpo


def linhas(campos_json: str | None, dados_json: str | None) -> list[dict]:
    """Respostas legíveis, pela ordem do formulário."""
    if not dados_json:
        return []
    dados = json.loads(dados_json)
    try:
        campos = ler(campos_json)
    except ValueError:
        campos = []
    rotulos = {c["id"]: c["rotulo"] for c in campos}
    ordem = [c["id"] for c in campos] + [k for k in dados if k not in rotulos]
    out = []
    for k in ordem:
        if k in dados:
            v = dados[k]
            out.append({"campo": rotulos.get(k, k), "valor": ", ".join(v) if isinstance(v, list) else str(v)})
    return out


def resumo(dados: dict) -> str:
    partes = [", ".join(v) if isinstance(v, list) else str(v) for v in dados.values()]
    return " · ".join(partes)[:150]
