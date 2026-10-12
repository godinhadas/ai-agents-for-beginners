"""Agente IA do CRM: modelo de linguagem com chamada de ferramentas sobre os dados.

Usa a API compatível com OpenAI. Por omissão aponta para GitHub Models
(gratuito com GITHUB_TOKEN, como no resto do curso); para Azure OpenAI ou
outro fornecedor basta mudar CRM_LLM_BASE_URL, CRM_LLM_API_KEY e CRM_LLM_MODEL.
"""

import json
import os
from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from . import services

MAX_ITERACOES = 6

SYSTEM_PROMPT = """És o assistente comercial e operacional do CRM da MHAIS Seguros, em Angola.
Respondes sempre em português de Angola, sem Acordo Ortográfico, de forma directa e objectiva.
Valores monetários em kwanzas (Kz), com separador de milhares.
Usa SEMPRE as ferramentas para obter dados; nunca inventes clientes, apólices, valores ou datas.
Se a informação não existir, di-lo claramente.
Só registas actividades quando o utilizador o pede explicitamente, e confirmas o que registaste.
Data de hoje: {hoje}."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_clientes",
            "description": "Pesquisa clientes por nome, NIF ou email. Devolve id, nome, NIF, tipo e província.",
            "parameters": {
                "type": "object",
                "properties": {"texto": {"type": "string", "description": "Parte do nome, NIF ou email"}},
                "required": ["texto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "visao_cliente",
            "description": "Visão 360 de um cliente: dados, apólices, sinistros, oportunidades e actividades recentes.",
            "parameters": {
                "type": "object",
                "properties": {"cliente_id": {"type": "integer"}},
                "required": ["cliente_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "renovacoes",
            "description": "Apólices activas que terminam nos próximos N dias, ordenadas por data de fim.",
            "parameters": {
                "type": "object",
                "properties": {"dias": {"type": "integer", "minimum": 1, "maximum": 365}},
                "required": ["dias"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sinistros_abertos",
            "description": "Sinistros ainda não fechados (participado, em análise ou aprovado sem pagamento).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pipeline",
            "description": "Pipeline comercial: quantidade e valor estimado das oportunidades por fase.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registar_actividade",
            "description": "Regista uma actividade (chamada, email, reunião, nota ou tarefa) num cliente. "
                           "Usar só quando o utilizador pede explicitamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_id": {"type": "integer"},
                    "tipo": {"type": "string", "enum": ["chamada", "email", "reuniao", "nota", "tarefa"]},
                    "assunto": {"type": "string"},
                    "descricao": {"type": "string"},
                },
                "required": ["cliente_id", "tipo", "assunto"],
            },
        },
    },
]


def _ferramentas(db: Session) -> dict[str, Callable[..., object]]:
    return {
        "pesquisar_clientes": lambda texto: services.pesquisar_clientes(db, texto),
        "visao_cliente": lambda cliente_id: services.visao_cliente(db, int(cliente_id))
        or {"erro": f"cliente {cliente_id} não existe"},
        "renovacoes": lambda dias=60: services.renovacoes(db, max(1, min(int(dias), 365))),
        "sinistros_abertos": lambda: services.sinistros_abertos(db),
        "pipeline": lambda: services.pipeline(db),
        "registar_actividade": lambda cliente_id, tipo, assunto, descricao=None: services.registar_actividade(
            db, int(cliente_id), tipo, assunto, descricao
        ),
    }


def executar_ferramenta(db: Session, nome: str, argumentos: str) -> object:
    """Executa uma ferramenta pedida pelo modelo; erros voltam ao modelo como dados."""
    fn = _ferramentas(db).get(nome)
    if fn is None:
        return {"erro": f"ferramenta desconhecida: {nome}"}
    try:
        args = json.loads(argumentos or "{}")
        return fn(**args)
    except (ValueError, TypeError) as exc:
        db.rollback()
        return {"erro": str(exc)}


class AgenteIndisponivel(RuntimeError):
    pass


def criar_cliente_llm():
    api_key = os.getenv("CRM_LLM_API_KEY") or os.getenv("GITHUB_TOKEN")
    if not api_key:
        raise AgenteIndisponivel(
            "Agente IA sem credenciais: define GITHUB_TOKEN (GitHub Models) ou CRM_LLM_API_KEY no .env."
        )
    from openai import OpenAI

    return OpenAI(
        base_url=os.getenv("CRM_LLM_BASE_URL", "https://models.github.ai/inference"),
        api_key=api_key,
        timeout=60,
        max_retries=1,
    )


def conversar(db: Session, mensagens: list[dict], cliente_llm=None) -> dict:
    cliente_llm = cliente_llm or criar_cliente_llm()
    modelo = os.getenv("CRM_LLM_MODEL", "openai/gpt-4o-mini")
    historico: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT.format(hoje=date.today().isoformat())}]
    historico += mensagens
    accoes: list[dict] = []

    for _ in range(MAX_ITERACOES):
        resp = cliente_llm.chat.completions.create(model=modelo, messages=historico, tools=TOOLS, temperature=0.2)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"resposta": msg.content or "", "accoes": accoes}

        historico.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            resultado = executar_ferramenta(db, tc.function.name, tc.function.arguments)
            accoes.append({"ferramenta": tc.function.name, "argumentos": tc.function.arguments})
            historico.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

    return {"resposta": "Não consegui concluir o pedido dentro do limite de passos. Reformula ou divide a pergunta.",
            "accoes": accoes}
