# CRM MHAIS

CRM (gestão da relação com clientes) para a MHAIS Seguros, com agente IA (inteligência artificial) integrado. MVP (produto mínimo viável) em Python: FastAPI, SQLAlchemy e SQLite, com interface web sem dependências externas.

## Arranque rápido

```bash
cd crm-app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # preencher GITHUB_TOKEN para activar o agente IA
uvicorn crm.main:app --reload # http://127.0.0.1:8000
```

- Interface: `http://127.0.0.1:8000/`
- Documentação da API (OpenAPI): `http://127.0.0.1:8000/docs`
- Testes: `pytest` (dentro de `crm-app/`)

Na primeira execução, com `CRM_SEED=1`, a base é carregada com dados fictícios de demonstração, com datas relativas ao dia de hoje para o painel ter sempre renovações e sinistros em curso.

## O que está incluído

| Módulo | Conteúdo |
|---|---|
| Painel | Clientes, apólices activas, prémio em carteira, renovações a 30/60/90 dias, sinistros em aberto, pipeline por fase, carteira por ramo |
| Clientes | Particulares e empresas, NIF (número de identificação fiscal) único, província, mediador; visão 360 (apólices, sinistros, oportunidades, actividades) |
| Apólices | Número, ramo, prémio anual, capital seguro, vigência, estado |
| Sinistros | Participação, valores reclamado e pago, estado (participado, em análise, aprovado, recusado, pago) |
| Oportunidades | Pipeline comercial: prospecção, proposta, negociação, ganha, perdida |
| Actividades | Chamadas, emails, reuniões, notas e tarefas por cliente |
| Mediadores | Código, contactos, comissão |
| Assistente IA | Perguntas em linguagem natural sobre os dados; regista actividades quando pedido |

Regras aplicadas no servidor: unicidade de NIF, número de apólice, número de sinistro e código de mediador; validação de referências (cliente, apólice, mediador); data de fim posterior à de início, também em alterações parciais; valores não negativos; recusa de eliminação de registos com dependências (ex.: cliente com apólices).

## Agente IA

`crm/agent.py` implementa um ciclo de chamada de ferramentas (tool calling) sobre a API compatível com OpenAI. O modelo nunca acede à base directamente; só usa estas ferramentas:

| Ferramenta | Tipo | Função |
|---|---|---|
| `pesquisar_clientes` | leitura | Pesquisa por nome, NIF ou email |
| `visao_cliente` | leitura | Visão 360 de um cliente |
| `renovacoes` | leitura | Apólices activas a terminar nos próximos N dias |
| `sinistros_abertos` | leitura | Sinistros por fechar, com dias em aberto |
| `pipeline` | leitura | Quantidade e valor por fase |
| `registar_actividade` | escrita | Regista chamada, email, reunião, nota ou tarefa |

Limites: máximo de 6 iterações por pedido, histórico de 20 mensagens, tempo limite de 60 s por chamada ao modelo. A interface mostra que ferramentas o agente usou em cada resposta.

Fornecedor por omissão: GitHub Models (`https://models.github.ai/inference`, modelo `openai/gpt-4o-mini`), coerente com o resto do curso. Para Azure OpenAI ou outro, alterar `CRM_LLM_BASE_URL`, `CRM_LLM_API_KEY` e `CRM_LLM_MODEL`.

## Estrutura

```
crm-app/
├── crm/
│   ├── main.py       # API REST, CRUD genérico, painel, visão 360, chat
│   ├── models.py     # Tabelas (SQLAlchemy)
│   ├── schemas.py    # Validação de entrada e saída (Pydantic)
│   ├── services.py   # Regras de negócio partilhadas pela API e pelo agente
│   ├── agent.py      # Agente IA e ferramentas
│   ├── seed.py       # Dados de demonstração
│   ├── db.py         # Ligação à base de dados
│   └── static/       # Interface web (HTML, CSS, JS)
└── tests/test_api.py # Testes da API e do agente (modelo simulado, sem rede)
```

## Limitações conhecidas antes de produção

| # | Lacuna | Risco | Acção proposta |
|---|---|---|---|
| 1 | Sem autenticação nem perfis | Qualquer pessoa na rede acede e altera dados pessoais de clientes | SSO (início de sessão único) com Entra ID via OIDC; perfis comercial, sinistros, gestão, administrador |
| 2 | Sem trilho de auditoria | Impossível saber quem alterou o quê | Tabela de auditoria por alteração (utilizador, data, antes/depois) |
| 3 | Valores em vírgula flutuante | Arredondamentos em prémios e indemnizações | `DECIMAL(18,2)` ao migrar para SQL Server ou PostgreSQL |
| 4 | SQLite | Concorrência limitada, sem alta disponibilidade | SQL Server com backup Veeam já existente; migrações com Alembic |
| 5 | Dados enviados ao modelo de IA | Dados pessoais saem para um fornecedor externo | Azure OpenAI em região com acordo de tratamento de dados; avaliar à luz da Lei n.º 22/11 de Protecção de Dados Pessoais |
| 6 | Sem integração com o sistema core de seguros | Dupla introdução de apólices e sinistros | Sincronização via API ou base intermédia, com o core como fonte de verdade |

Por omissão o servidor escuta apenas em `127.0.0.1`. Não expor na rede antes de fechar os pontos 1 e 2.
