# Gestor de Pedidos DSI · MHAIS

Aplicação interna onde os colaboradores da MHAIS fazem todos os pedidos à DSI (Direcção de Sistemas de Informação): acessos ao Windows e a plataformas, Anywhere (acessos e apoio), equipamento e gadgets, licenças e software, reparações, instalações e outras intervenções técnicas. Inclui aprovação pela DSI, SLA (prazos de resposta e resolução), inventário de equipamentos e licenças, login com a conta Microsoft e notificações e pedidos por email.

## Instalar num computador novo (um comando)

No PowerShell, de preferência como administrador (para criar a regra de firewall):

```powershell
iwr https://raw.githubusercontent.com/godinhadas/ai-agents-for-beginners/claude/crm-app-ujozhn/portal-dsi/instalar.ps1 -OutFile $env:TEMP\instalar-gpd.ps1
powershell -ExecutionPolicy Bypass -File $env:TEMP\instalar-gpd.ps1
```

O instalador põe o Python e o Git se faltarem (winget), descarrega só a pasta `portal-dsi` para `C:\Projectos\ai-agents-for-beginners`, cria o ambiente, instala as dependências, cria a regra de firewall, os atalhos e o arranque automático, e arranca o portal. Corrido de novo, actualiza a instalação sem apagar dados. Para levar os dados de outro PC, copia `portal.db` e `.env` para a pasta `portal-dsi` com o portal parado.

## Arranque no Windows (PowerShell)

```powershell
cd C:\Projectos\ai-agents-for-beginners\portal-dsi
.\iniciar.ps1              # porta 8010; outra porta: .\iniciar.ps1 -Porta 8020
```

Na primeira execução, o script cria o ambiente virtual, instala as dependências e copia o `.env.example` para `.env`. Abre `http://127.0.0.1:8010`.

Se o PowerShell bloquear o script: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (só para essa janela).

Testes: `.\.venv\Scripts\python.exe -m pytest`

### Arranque diário por cliques (até haver servidor)

| Ficheiro | O que faz |
|---|---|
| `Arrancar Gestor de Pedidos.cmd` | Arranca na rede (porta 8010) numa janela minimizada e abre o browser. Se já estiver a correr, só abre o browser. |
| `Parar Gestor de Pedidos.cmd` | Pára o servidor e fecha a janela minimizada. |
| `instalar-atalhos.ps1` | Corre uma vez: cria no ambiente de trabalho os atalhos **Gestor de Pedidos DSI** e **Parar Gestor de Pedidos** e põe o arranque na pasta de arranque do Windows, para arrancar sozinho depois de reiniciar e entrar no PC. |

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar-atalhos.ps1                         # tudo
powershell -ExecutionPolicy Bypass -File .\instalar-atalhos.ps1 -SemArranqueAutomatico  # só ambiente de trabalho
powershell -ExecutionPolicy Bypass -File .\instalar-atalhos.ps1 -Remover                # apaga os atalhos
```

O arranque automático só corre depois de iniciares sessão no PC. Para correr sem sessão iniciada, é o servidor com serviço do Windows (ver "Instalação no servidor interno").

### Mostrar a um colega (teste na rede da MHAIS)

```powershell
.\iniciar.ps1 -Rede
```

O script mostra o endereço a enviar (por exemplo `http://10.0.0.25:8010`). O colega abre-o no browser, desde que esteja na mesma rede ou na VPN. Se não abrir, falta a regra de firewall que o script indica (uma vez, como administrador); se o ESET tiver firewall própria, a porta também tem de ser permitida lá. Em modo de teste não há palavra-passe: usar só com dados de teste e fechar a janela no fim.

## Perfis

| Perfil | Pode fazer |
|---|---|
| Colaborador | Fazer pedidos para si ou em nome de colegas; acompanhar os pedidos em que é requerente ou beneficiário |
| Helpdesk | Tratar todos os pedidos, atribuir, comentar (inclui notas internas), entregar equipamento, atribuir licenças, gerir equipamentos |
| Administrador DSI | Tudo, mais **aprovar ou recusar** pedidos, utilizadores, catálogo, departamentos e licenças |

## Navegação por perfil

| Perfil | Menus (por esta ordem) | Abre em |
|---|---|---|
| Colaborador | Novo pedido · Os meus pedidos | Novo pedido |
| Helpdesk | Fila de pedidos · Novo pedido · Painel | Fila de pedidos |
| Administrador DSI | Painel · Fila de pedidos · Novo pedido · Administração | Painel |

Todas as páginas seguem o mesmo padrão: título e explicação no topo, acção principal à direita, filtros sempre na mesma ordem (separadores, estado, pesquisa), confirmações e mensagens dentro do portal. Os números a vermelho nos menus indicam o que espera por ti (pedidos para aprovar, sem técnico, ou a aguardar a tua resposta). Em cada pedido, a barra de etapas mostra onde está: Registado, Aprovação DSI, Em tratamento, Resolvido, Fechado.

## Circuito do pedido

1. **Pedido.** Na página inicial, o colaborador escolhe um mosaico (por exemplo "Monitor" ou "Erro no Anywhere") e indica para quem é.
2. **Aprovação.** Os pedidos de acessos, equipamento e licenças são aprovados pela DSI (perfil administrador). Se o pedido for registado por um administrador, fica aprovado de imediato. Avarias, intervenções e apoio no Anywhere seguem directamente para o Helpdesk.
3. **Tratamento.** O Helpdesk assume ou atribui, pode pedir informação ao colaborador, entrega o equipamento ou atribui a licença, e resolve indicando a solução.
4. **Confirmação e fecho.** Quando o técnico resolve, quem pediu recebe a novidade e vê a solução aplicada com dois botões: **Sim, ficou resolvido** (fecha) ou **Não ficou resolvido** (reabre, com o motivo, e avisa o técnico). O técnico não fecha pedidos. Sem resposta, o pedido fecha automaticamente 5 dias depois de resolvido; depois de fechado, quem pediu ainda o pode reabrir durante 5 dias.

### Conversa, novidades, pesquisa e prazos

- **Conversa** e **Histórico** são separadores distintos na página do pedido. A conversa é um chat: mensagens, perguntas do técnico, solução aplicada e motivos de reabertura. Enter envia; Shift+Enter muda de linha. Notas internas aparecem só à DSI, a tracejado.
- **Sino de novidades** no cabeçalho: mensagens e mudanças por ler (pedido assumido, pedido de informação, resolvido, reaberto, confirmado, novo pedido sem técnico, pedido para aprovar). O portal verifica de 30 em 30 segundos, mostra um aviso, marca o pedido na lista com um ponto vermelho e põe o número de novidades no título do separador. Abrir o pedido marca-o como lido. As notificações do Windows só funcionam em `https://` ou `localhost`; no endereço por IP da rede, ficam os avisos dentro do portal.
- **Pesquisa** pelo número parcial (`12`, `012`, `PED-12`), assunto, descrição ou nome do colega. O número exacto aparece primeiro.
- **Prazos** visíveis para todos: na lista (coluna Prazo) e no pedido (primeira resposta e resolução, com o estado No prazo, Em risco, Fora de prazo ou Cumprido).

O catálogo (mosaicos, descrições, ícones, ordem, quais exigem aprovação e as perguntas de cada um) altera-se em Administração > Catálogo, com um editor visual: pergunta, tipo de resposta e uma opção por linha.

## Formulários por cliques

Cada item do catálogo tem perguntas com opções para escolher (por exemplo, em "Desbloquear conta": que conta e o que se passa; em "Instalação de software": a lista de programas padrão, com campo "Outro" para escrever o que não está na lista). O assunto do pedido é gerado a partir das escolhas e a descrição passa a opcional. As perguntas e opções editam-se em Administração > Catálogo, no editor visual de perguntas.

Qualquer colaborador pode pedir para outra pessoa: "Para outra pessoa" e escolher o nome.

## Automação

| Automação | O que faz | Como se activa |
|---|---|---|
| Desbloquear conta no Active Directory | Em "Desbloquear conta" com "Windows / rede", executa `Unlock-ADAccount` no utilizador do pedido e resolve o pedido com o resultado | `PORTAL_AUTOMACAO_AD=1` |

- **Por omissão, com um clique do técnico** ("Executar automaticamente"). Fica registado no histórico quem executou e o resultado.
- **Imediata** (`PORTAL_AUTOMACAO_IMEDIATA=1`): corre sem técnico **só quando o pedido é do próprio**, autenticado com a conta Microsoft. Pedidos de A para B passam sempre por um técnico, para evitar desbloqueios indevidos.
- Requisitos: o portal tem de correr num servidor do domínio, com o módulo ActiveDirectory (RSAT), numa conta de serviço com **permissão delegada apenas para desbloquear contas** (nunca Domain Admin).
- Anywhere: a automação de desbloqueio e perfis depende da API do Anywhere; entra quando houver acesso a ela.

## Módulos

Nesta fase o foco é o **circuito de pedidos**. Os menus de Equipamentos e Licenças (inventário e entregas a partir dos pedidos) estão desligados e activam-se com `PORTAL_INVENTARIO=1` no `.env`.

## Dados iniciais

- A base começa **limpa**: só o catálogo de pedidos e, em modo de teste, o(s) administrador(es) indicados em `PORTAL_ADMINS`.
- Com `PORTAL_SEED=demo` carrega utilizadores, equipamentos e pedidos fictícios, apenas para demonstração.

## SLA

| Prioridade | 1.ª resposta | Resolução | Contagem |
|---|---|---|---|
| Crítica | 30 min | 4 h | horas corridas |
| Alta | 2 h | 8 h | horas úteis |
| Média | 4 h | 2 dias úteis | horas úteis |
| Baixa | 1 dia útil | 5 dias úteis | horas úteis |

Horas úteis: segunda a sexta, das 08:00 às 17:00 (feriados ainda não considerados). O prazo conta a partir da aprovação, quando a há. Só a DSI pode classificar um pedido como crítico.

## Identidade visual (MHAIS Seguros)

| Elemento | Valor | Ficheiro |
|---|---|---|
| Roxo MHAIS (botões, destaques) | `#7A3EC8` | `portal/static/marca/marca.css` |
| Beringela (cabeçalho, barra dos emails) | `#2B0E43` | `marca.css` e `PORTAL_COR_EMAIL_ESCURA` |
| Lilás de fundo | `#F5F3F9` | `marca.css` |
| Logotipo a cores (fundos claros) | | `portal/static/marca/logo.png` |
| Logotipo branco (cabeçalho) | | `portal/static/marca/logo-branco.png` |
| Padrão de cruzes (ecrã de entrada e faixa de boas-vindas) | | `padrao.svg`, `padrao-claro.svg` |
| Ícone do separador | | `favicon.svg` |

Cores retiradas do logotipo e do padrão oficiais. Nome, direcção e contactos do Helpdesk mudam-se no `.env` (`PORTAL_EMPRESA`, `PORTAL_NOME`, `PORTAL_DIRECCAO`, `PORTAL_CONTACTO_EMAIL`, `PORTAL_CONTACTO_TELEFONE`, `PORTAL_HORARIO`).

## Integração com o Microsoft 365

| Função | Como funciona |
|---|---|
| Início de sessão | Conta Microsoft da MHAIS (Entra ID, OpenID Connect). Quem entra pela primeira vez fica como colaborador; os emails em `PORTAL_ADMINS` ficam administradores |
| Colaboradores | Sincronizados do Entra ID a cada 24 h (nome, email, departamento, conta activa). Os perfis Helpdesk e Administrador são geridos no portal |
| Notificações | Emails enviados pela caixa do Helpdesk em cada passo do pedido (registo, aprovação, atribuição, pedido de informação, resolução, comentários públicos). Notas internas nunca geram email |
| Pedidos por email | Emails enviados para a caixa do Helpdesk por colaboradores conhecidos criam pedidos. Respostas com `[PED-000123]` no assunto entram como comentário. Remetentes externos e respostas automáticas são ignorados |

Sem Entra ID configurado, tudo funciona em modo de demonstração: os emails ficam registados como "simulada" em Administração > Integrações.

### Configuração no Entra ID (uma vez, como administrador global)

1. **Registo da aplicação.** Entra admin center > Applications > App registrations > New registration.
   - Nome: `Gestor de Pedidos DSI`; Supported account types: *Accounts in this organizational directory only*.
   - Redirect URI, tipo Web: `https://<endereço do portal>/auth/callback`. Para testes no PC, acrescentar `http://localhost:8010/auth/callback`.
2. **Segredo.** Certificates & secrets > New client secret. Anota o valor e a data de expiração (renovar antes de expirar, ou o login pára).
3. **Permissões.** API permissions > Add > Microsoft Graph > Application permissions: `User.Read.All`, `Mail.Send`, `Mail.ReadWrite`. Depois, **Grant admin consent**. A permissão delegada `User.Read` já vem por omissão.
4. **Limitar o acesso ao correio.** Sem este passo, a aplicação pode ler e enviar a partir de qualquer caixa da MHAIS. No Exchange Online PowerShell:
   ```powershell
   # Grupo de segurança com email, cujo único membro é a caixa do Helpdesk
   New-DistributionGroup -Name "Gestor de Pedidos DSI Caixas" -Type Security -PrimarySmtpAddress portal-dsi-caixas@<dominio> `
     -Members helpdesk@<dominio>
   New-ApplicationAccessPolicy -AppId <ENTRA_CLIENT_ID> -PolicyScopeGroupId portal-dsi-caixas@<dominio> `
     -AccessRight RestrictAccess -Description "Gestor de Pedidos DSI: só a caixa do Helpdesk"
   Test-ApplicationAccessPolicy -AppId <ENTRA_CLIENT_ID> -Identity helpdesk@<dominio>        # Granted
   Test-ApplicationAccessPolicy -AppId <ENTRA_CLIENT_ID> -Identity antonio.godinho@<dominio> # Denied
   ```
   A Microsoft está a substituir as Application Access Policies pelo RBAC for Applications. O efeito é o mesmo e qualquer um dos dois serve.
5. **Caixa do Helpdesk.** Caixa partilhada (por exemplo `helpdesk@<dominio>`), sem licença.
6. **`.env`.** Preencher `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `PORTAL_CAIXA_HELPDESK`, `PORTAL_ADMINS`, `PORTAL_SECRET_KEY` e `PORTAL_URL_BASE`; mudar `PORTAL_AUTH_MODE=entra` e `PORTAL_SEED=0`. Ligar `PORTAL_LER_CAIXA=1` quando quiseres receber pedidos por email.

Verificação: Administração > Integrações > **Correr tarefas agora** e **Sincronizar com o Entra ID**. Em caso de erro, o resultado e a lista de emails mostram a causa.

### Instalação no servidor interno

1. Windows Server com Python 3.12 ou superior; copiar a pasta `portal-dsi` (ou `git clone`) e correr `.\iniciar.ps1` uma vez, para criar o ambiente.
2. Correr o portal como serviço do Windows, por exemplo com NSSM (gestor de serviços), sempre com **um único processo**:
   `nssm install PortalDSI C:\Portal\portal-dsi\.venv\Scripts\python.exe "-m uvicorn portal.main:app --host 127.0.0.1 --port 8010 --proxy-headers"`
   e `AppDirectory` em `C:\Portal\portal-dsi`.
3. IIS como proxy inverso (módulos URL Rewrite e ARR), com o certificado HTTPS interno e o nome `portal-dsi.<dominio>` no DNS. `PORTAL_HTTPS=1` no `.env`.
4. Backup: incluir `portal.db` e `.env` no Veeam. O `.env` contém o segredo da aplicação: acesso NTFS só para administradores e para a conta do serviço.

Ao actualizar a partir da etapa 1a, apaga o `portal.db` de demonstração: a estrutura da base mudou.

## Próximas etapas

| Etapa | Conteúdo |
|---|---|
| 1c | Assistente IA: triagem automática e consultas sobre pedidos, equipamentos e licenças |
| 1d | Migrações da base de dados (Alembic) e SQL Server, relatórios mensais, feriados no SLA, anexos nos pedidos |
| 2 | CRM de clientes integrado com o Anywhere (sistema core) |
