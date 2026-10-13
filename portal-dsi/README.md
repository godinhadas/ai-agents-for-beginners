# Portal DSI MHAIS

Portal interno de pedidos à DSI (Direcção de Sistemas de Informação): incidentes, equipamentos, licenças e acessos, com aprovação da chefia, SLA (prazos de resposta e resolução), inventário de equipamentos e licenças, login com a conta Microsoft e notificações e pedidos por email.

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

## Integração com o Microsoft 365

| Função | Como funciona |
|---|---|
| Início de sessão | Conta Microsoft da MHAIS (Entra ID, OpenID Connect). Quem entra pela primeira vez fica como colaborador; os emails em `PORTAL_ADMINS` ficam administradores |
| Colaboradores e chefias | Sincronizados do Entra ID a cada 24 h (nome, email, departamento, chefia, conta activa). Quem tem subordinados passa a chefia. Os perfis Helpdesk e Administrador são geridos no portal |
| Notificações | Emails enviados pela caixa do Helpdesk em cada passo do pedido (registo, aprovação, atribuição, pedido de informação, resolução, comentários públicos). Notas internas nunca geram email |
| Pedidos por email | Emails enviados para a caixa do Helpdesk por colaboradores conhecidos criam pedidos. Respostas com `[PED-000123]` no assunto entram como comentário. Remetentes externos e respostas automáticas são ignorados |

Sem Entra ID configurado, tudo funciona em modo de demonstração: os emails ficam registados como "simulada" em Administração > Integrações.

### Configuração no Entra ID (uma vez, como administrador global)

1. **Registo da aplicação.** Entra admin center > Applications > App registrations > New registration.
   - Nome: `Portal DSI`; Supported account types: *Accounts in this organizational directory only*.
   - Redirect URI, tipo Web: `https://<endereço do portal>/auth/callback`. Para testes no PC, acrescentar `http://localhost:8010/auth/callback`.
2. **Segredo.** Certificates & secrets > New client secret. Anota o valor e a data de expiração (renovar antes de expirar, ou o login pára).
3. **Permissões.** API permissions > Add > Microsoft Graph > Application permissions: `User.Read.All`, `Mail.Send`, `Mail.ReadWrite`. Depois, **Grant admin consent**. A permissão delegada `User.Read` já vem por omissão.
4. **Limitar o acesso ao correio.** Sem este passo, a aplicação pode ler e enviar a partir de qualquer caixa da MHAIS. No Exchange Online PowerShell:
   ```powershell
   # Grupo de segurança com email, cujo único membro é a caixa do Helpdesk
   New-DistributionGroup -Name "Portal DSI Caixas" -Type Security -PrimarySmtpAddress portal-dsi-caixas@<dominio> `
     -Members helpdesk@<dominio>
   New-ApplicationAccessPolicy -AppId <ENTRA_CLIENT_ID> -PolicyScopeGroupId portal-dsi-caixas@<dominio> `
     -AccessRight RestrictAccess -Description "Portal DSI: só a caixa do Helpdesk"
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
