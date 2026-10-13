# Portal DSI MHAIS

Portal interno de pedidos à DSI (Direcção de Sistemas de Informação): incidentes, equipamentos, licenças e acessos, com aprovação da chefia, SLA (prazos de resposta e resolução) e inventário de equipamentos e licenças.

## Arranque no Windows (PowerShell)

```powershell
cd C:\Projectos\ai-agents-for-beginners\portal-dsi
.\iniciar.ps1              # porta 8010; outra porta: .\iniciar.ps1 -Porta 8020
```

Na primeira execução, o script cria o ambiente virtual, instala as dependências e copia o `.env.example` para `.env`. Abre `http://127.0.0.1:8010`.

Se o PowerShell bloquear o script: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (só para essa janela).

Testes: `.\.venv\Scripts\python.exe -m pytest`

## Perfis

| Perfil | Pode fazer |
|---|---|
| Colaborador | Criar pedidos para si ou em nome de colegas; acompanhar os pedidos em que é requerente ou beneficiário |
| Chefia | O mesmo, mais aprovar ou recusar os pedidos da equipa e ver os pedidos da equipa |
| Helpdesk | Tratar todos os pedidos, atribuir, comentar (inclui notas internas), entregar equipamento, atribuir licenças, gerir equipamentos |
| Administrador DSI | Tudo, mais utilizadores, catálogo, departamentos e licenças |

## Circuito do pedido

1. **Criação.** O colaborador escolhe um item do catálogo e indica para quem é o pedido.
2. **Aprovação.** Se o item exige aprovação (equipamento, licença, acesso), o pedido vai para a chefia directa do beneficiário. Sem chefia definida, vai para o administrador DSI. Se quem pede já é o aprovador, o pedido fica aprovado automaticamente.
3. **Tratamento.** O Helpdesk assume ou atribui, pode pedir informação ao colaborador, entrega o equipamento ou atribui a licença, e resolve indicando a solução.
4. **Fecho.** O colaborador confirma e fecha, ou reabre. O pedido fecha automaticamente 5 dias depois de resolvido.

Tudo fica no histórico do pedido: quem fez o quê e quando.

## SLA

| Prioridade | 1.ª resposta | Resolução | Contagem |
|---|---|---|---|
| Crítica | 30 min | 4 h | horas corridas |
| Alta | 2 h | 8 h | horas úteis |
| Média | 4 h | 2 dias úteis | horas úteis |
| Baixa | 1 dia útil | 5 dias úteis | horas úteis |

Horas úteis: segunda a sexta, das 08:00 às 17:00 (feriados ainda não considerados). O prazo conta a partir da aprovação, quando a há. Só a DSI pode classificar um pedido como crítico.

## Estado actual e próximos passos

Esta é a etapa 1a, em modo de demonstração: entra-se escolhendo o utilizador numa lista, sem palavra-passe. **Não usar com dados reais nem pôr na rede** até concluir a etapa 1b.

| Etapa | Conteúdo |
|---|---|
| 1b | Início de sessão com conta Microsoft (Entra ID), sincronização de colaboradores e chefias, notificações por email, criação de pedidos por email, instalação num servidor interno com HTTPS |
| 1c | Assistente IA: triagem automática e consultas sobre pedidos, equipamentos e licenças |
| 2 | CRM de clientes integrado com o Anywhere (sistema core) |
