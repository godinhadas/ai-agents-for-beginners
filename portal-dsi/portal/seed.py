"""Dados iniciais.

- catálogo base: sempre que o catálogo está vazio (é configuração, não são dados de teste);
- primeiro administrador: em modo dev, se não houver utilizadores, a partir de PORTAL_ADMINS;
- demonstração: só com PORTAL_SEED=demo (utilizadores, equipamentos e pedidos fictícios).
"""

import os
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import pedidos as wf, sla
from .models import AtribuicaoLicenca, Departamento, Equipamento, ItemCatalogo, Licenca, Utilizador, agora

# (tipo, nome, descrição curta, ícone, requer aprovação da DSI, prioridade por omissão)
CATALOGO = [
    ("acesso", "Desbloquear conta ou repor palavra-passe", "Não consigo entrar no Windows ou no email", "cadeado", False, "alta"),
    ("acesso", "Nova conta ou alteração de permissões", "Conta de rede, grupos e permissões no Windows", "utilizador", True, "media"),
    ("acesso", "Pasta partilhada", "Acesso de leitura ou escrita a uma pasta", "pasta", True, "media"),
    ("acesso", "VPN e acesso remoto", "Trabalhar fora do escritório", "globo", True, "media"),
    ("acesso", "Email, Teams ou grupos", "Caixas partilhadas, listas de distribuição, equipas", "email", True, "media"),
    ("acesso", "Outra plataforma", "Portais de parceiros, bancos, AGT, outras aplicações", "chave", True, "media"),
    ("anywhere", "Acesso ou perfil no Anywhere", "Novo utilizador, perfil ou permissões", "chave", True, "media"),
    ("anywhere", "Erro no Anywhere", "Mensagem de erro, bloqueio ou lentidão", "alerta", False, "alta"),
    ("anywhere", "Apoio em apólices, sinistros ou recibos", "Dúvida ou correcção no Anywhere", "escudo", False, "media"),
    ("equipamento", "Computador", "Portátil ou desktop, novo ou substituição", "portatil", True, "media"),
    ("equipamento", "Monitor", "Monitor adicional ou substituição", "monitor", True, "baixa"),
    ("equipamento", "Periféricos", "Rato, teclado, headset, webcam, docking station", "rato", True, "baixa"),
    ("equipamento", "Pen drive ou disco externo", "Armazenamento cifrado", "pen", True, "baixa"),
    ("equipamento", "Telemóvel ou gadget", "Telemóvel, tablet, carregadores, acessórios", "telemovel", True, "baixa"),
    ("licenca", "Licença Microsoft 365", "Office, Power BI, Visio, Project", "nuvem", True, "media"),
    ("licenca", "Instalação de software", "Programa necessário para o trabalho", "descarregar", True, "media"),
    ("licenca", "Outra licença", "Adobe, antivírus, outras aplicações", "insignia", True, "media"),
    ("intervencao", "Avaria ou reparação", "Equipamento que não liga, partido ou com defeito", "ferramenta", False, "media"),
    ("intervencao", "Instalação ou configuração", "Montar posto de trabalho, impressora, aplicação", "definicoes", False, "media"),
    ("intervencao", "Computador lento ou com erros", "Bloqueios, erros, vírus", "alerta", False, "media"),
    ("intervencao", "Internet, rede ou Wi-Fi", "Sem ligação ou ligação instável", "wifi", False, "alta"),
    ("intervencao", "Email, Outlook ou Teams", "Não envia, não recebe, não abre", "email", False, "alta"),
    ("intervencao", "Impressão", "Impressora, digitalização, consumíveis", "impressora", False, "baixa"),
    ("outro", "Outro pedido", "Não encontrei o que procuro", "ajuda", False, "baixa"),
]


def _o(id_, rotulo, opcoes, obrigatorio=True):
    return {"id": id_, "rotulo": rotulo, "tipo": "opcoes", "opcoes": opcoes, "obrigatorio": obrigatorio}


def _m(id_, rotulo, opcoes, outro=True, obrigatorio=True):
    return {"id": id_, "rotulo": rotulo, "tipo": "multi", "opcoes": opcoes, "outro": outro, "obrigatorio": obrigatorio}


def _t(id_, rotulo, obrigatorio=True, ajuda=""):
    return {"id": id_, "rotulo": rotulo, "tipo": "texto", "obrigatorio": obrigatorio, "ajuda": ajuda}


MODULOS_ANYWHERE = ["Apólices", "Sinistros", "Recibos e cobranças", "Clientes", "Mediadores", "Relatórios", "Outro"]
RAMOS = ["Automóvel", "Saúde", "Vida", "Multirriscos", "Acidentes de Trabalho", "Viagem", "Outro"]
# Lista inicial de software padrão: ajustar em Administração > Catálogo > Instalação de software.
SOFTWARE_PADRAO = ["Adobe Acrobat Reader", "Google Chrome", "Mozilla Firefox", "7-Zip", "Microsoft Teams",
                   "Zoom", "Power BI Desktop", "AnyDesk", "VLC", "Notepad++", "Java"]

# nome do item: (campos do formulário, automação)
FORMULARIOS = {
    "Desbloquear conta ou repor palavra-passe": (
        [_o("sistema", "Que conta?", ["Windows / rede", "Email / Microsoft 365", "Anywhere", "Outra aplicação"]),
         _o("situacao", "O que se passa?", ["Conta bloqueada", "Esqueci a palavra-passe", "Palavra-passe expirada"])],
        "desbloquear_ad"),
    "Nova conta ou alteração de permissões": (
        [_o("pedido", "O que é preciso?", ["Nova conta (novo colaborador)", "Alterar permissões",
                                           "Desactivar conta (saída)"]),
         {"id": "data", "rotulo": "A partir de", "tipo": "data", "obrigatorio": False},
         _t("igual_a", "Mesmas permissões que", False, "Nome de um colega com o mesmo perfil")], None),
    "Pasta partilhada": (
        [_t("pasta", "Que pasta?", True, "Ex.: \\\\servidor\\Comercial\\Propostas"),
         _o("acesso", "Tipo de acesso", ["Leitura", "Leitura e escrita"])], None),
    "VPN e acesso remoto": ([_o("periodo", "Por quanto tempo?", ["Permanente", "Temporário"])], None),
    "Email, Teams ou grupos": (
        [_o("o_que", "O que é preciso?", ["Acesso a caixa partilhada", "Entrar numa lista de distribuição",
                                          "Entrar numa equipa do Teams", "Criar caixa, lista ou equipa"]),
         _t("nome", "Qual?", True, "Nome da caixa, lista ou equipa")], None),
    "Outra plataforma": ([_t("plataforma", "Que plataforma?", True, "Ex.: portal do banco, AGT, ARSEG")], None),
    "Acesso ou perfil no Anywhere": (
        [_o("o_que", "O que é preciso?", ["Novo utilizador", "Alterar perfil ou permissões",
                                          "Desbloquear utilizador", "Desactivar utilizador"]),
         _m("modulos", "Módulos", MODULOS_ANYWHERE[:-1], outro=False, obrigatorio=False),
         _t("igual_a", "Mesmo perfil que", False, "Nome de um colega com o mesmo perfil")], None),
    "Erro no Anywhere": (
        [_o("modulo", "Onde aconteceu?", MODULOS_ANYWHERE),
         _o("ramo", "Ramo", RAMOS, obrigatorio=False),
         _o("impacto", "Impacto", ["Estou parado", "Consigo contornar", "Só informativo"])], None),
    "Apoio em apólices, sinistros ou recibos": (
        [_o("modulo", "Assunto", MODULOS_ANYWHERE), _o("ramo", "Ramo", RAMOS, obrigatorio=False),
         _t("referencia", "Nº de apólice, sinistro ou recibo", False)], None),
    "Computador": (
        [_o("o_que", "O que é preciso?", ["Novo", "Substituição", "Empréstimo temporário"]),
         _o("tipo", "Tipo", ["Portátil", "Desktop"])], None),
    "Monitor": ([_o("quantidade", "Quantos?", ["1 monitor", "2 monitores"])], None),
    "Periféricos": ([_m("itens", "O que é preciso?", ["Rato", "Teclado", "Headset", "Webcam", "Docking station",
                                                      "Carregador"])], None),
    "Pen drive ou disco externo": ([_o("capacidade", "Capacidade", ["32 GB", "64 GB", "128 GB", "Disco externo 1 TB"])],
                                   None),
    "Telemóvel ou gadget": ([_m("itens", "O que é preciso?", ["Telemóvel", "Tablet", "Carregador", "Capa",
                                                              "Power bank", "Cartão SIM"])], None),
    "Licença Microsoft 365": ([_m("licencas", "Que licença?", ["Microsoft 365 (Office)", "Power BI Pro", "Visio",
                                                               "Project", "Copilot"])], None),
    "Instalação de software": ([_m("software", "Que programas?", SOFTWARE_PADRAO)], None),
    "Outra licença": ([_t("produto", "Que licença ou programa?", True)], None),
    "Avaria ou reparação": (
        [_o("equipamento", "Que equipamento?", ["Portátil", "Desktop", "Monitor", "Impressora", "Telemóvel", "Outro"]),
         _t("etiqueta", "Etiqueta ou nº de série", False)], None),
    "Instalação ou configuração": (
        [_o("o_que", "O que é preciso?", ["Posto de trabalho novo", "Impressora", "Aplicação", "Outro"])], None),
    "Computador lento ou com erros": (
        [_m("sintomas", "O que acontece?", ["Muito lento", "Bloqueia", "Mensagens de erro", "Suspeita de vírus",
                                           "Não arranca"])], None),
    "Internet, rede ou Wi-Fi": (
        [_o("onde", "Onde?", ["Só no meu posto", "Em todo o piso ou sala", "Wi-Fi", "VPN fora do escritório"])], None),
    "Email, Outlook ou Teams": (
        [_o("aplicacao", "Que aplicação?", ["Outlook", "Teams", "OneDrive / SharePoint"]),
         _m("sintomas", "O que acontece?", ["Não envia", "Não recebe", "Pede palavra-passe", "Não abre"])], None),
    "Impressão": (
        [_o("o_que", "O que se passa?", ["Não imprime", "Não digitaliza", "Papel encravado",
                                         "Falta toner ou consumível", "Instalar impressora"])], None),
}


def carregar_catalogo(db: Session) -> bool:
    """Cria o catálogo numa base vazia; numa base existente, só completa formulários em falta."""
    import json

    existe = db.scalar(select(ItemCatalogo.id).limit(1)) is not None
    if not existe:
        for ordem, (tipo, nome, desc, icone, aprov, prio) in enumerate(CATALOGO, start=1):
            db.add(ItemCatalogo(tipo=tipo, nome=nome, descricao=desc, icone=icone, requer_aprovacao=aprov,
                                prioridade_padrao=prio, ordem=ordem * 10))
        db.flush()
    for item in db.scalars(select(ItemCatalogo).where(ItemCatalogo.campos.is_(None))):
        if item.nome in FORMULARIOS:
            campos, automacao = FORMULARIOS[item.nome]
            item.campos = json.dumps(campos, ensure_ascii=False)
            item.automacao = item.automacao or automacao
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return not existe


def garantir_administrador(db: Session) -> None:
    """Em modo dev numa base vazia, cria o(s) administrador(es) para se conseguir entrar."""
    if db.scalar(select(Utilizador.id).limit(1)) is not None:
        return
    emails = [e.strip().lower() for e in os.getenv("PORTAL_ADMINS", "").split(",") if e.strip()]
    for email in emails or ["admin@dsi.local"]:
        nome = email.split("@")[0].replace(".", " ").title() if emails else "Administrador DSI"
        db.add(Utilizador(nome=nome, email=email, perfil="admin"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def carregar_demo(db: Session) -> bool:
    """Demonstração com dados fictícios. Só numa base sem utilizadores."""
    if db.scalar(select(Utilizador.id).limit(1)) is not None:
        return False
    try:
        _demo(db)
    except IntegrityError:
        db.rollback()
        return False
    return True


def _item(db: Session, nome: str) -> int:
    return db.scalar(select(ItemCatalogo.id).where(ItemCatalogo.nome == nome))


def _demo(db: Session) -> None:
    dep = {n: Departamento(nome=n) for n in ("DSI", "Comercial", "Sinistros", "Financeira", "Recursos Humanos")}
    db.add_all(dep.values())
    db.flush()

    def u(nome, email, d, perfil="colaborador"):
        x = Utilizador(nome=nome, email=f"{email}@mhais.example", departamento_id=dep[d].id, perfil=perfil)
        db.add(x)
        db.flush()
        return x

    admin = u("António Godinho", "antonio.godinho", "DSI", "admin")
    hd1 = u("Paulo Cassule", "paulo.cassule", "DSI", "helpdesk")
    hd2 = u("Edna Muhongo", "edna.muhongo", "DSI", "helpdesk")
    c1 = u("Joana Sebastião", "joana.sebastiao", "Comercial")
    c2 = u("Ricardo Manuel", "ricardo.manuel", "Comercial")
    c3 = u("Wilson Capitango", "wilson.capitango", "Sinistros")
    c4 = u("Teresa Lukeny", "teresa.lukeny", "Financeira")
    u("Domingos Pedro", "domingos.pedro", "Recursos Humanos")

    hoje = date.today()
    db.add_all([
        Equipamento(etiqueta="MH-PC-001", tipo="Portátil", marca="Dell", modelo="Latitude 5450", numero_serie="DL5450A01",
                    estado="atribuido", utilizador_id=c1.id, garantia_ate=hoje + timedelta(days=895)),
        Equipamento(etiqueta="MH-PC-002", tipo="Portátil", marca="HP", modelo="EliteBook 840", numero_serie="HP840B03",
                    estado="stock", garantia_ate=hoje + timedelta(days=1065)),
        Equipamento(etiqueta="MH-PC-003", tipo="Portátil", marca="HP", modelo="EliteBook 840", numero_serie="HP840B04",
                    estado="reparacao", garantia_ate=hoje + timedelta(days=55), notas="Teclado com teclas a falhar"),
        Equipamento(etiqueta="MH-MON-001", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C01",
                    estado="atribuido", utilizador_id=c1.id),
        Equipamento(etiqueta="MH-MON-002", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C02", estado="stock"),
        Equipamento(etiqueta="MH-MON-003", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C03", estado="stock"),
        Equipamento(etiqueta="MH-USB-001", tipo="Pen drive", marca="Kingston", modelo="64 GB cifrada", estado="stock"),
    ])
    m365 = Licenca(produto="Microsoft 365 Business Premium", quantidade=50, renovacao_em=hoje + timedelta(days=45))
    pbi = Licenca(produto="Power BI Pro", quantidade=3, renovacao_em=hoje + timedelta(days=45))
    db.add_all([m365, pbi])
    db.flush()
    for x in db.scalars(select(Utilizador)).all():
        db.add(AtribuicaoLicenca(licenca_id=m365.id, utilizador_id=x.id))
    for x in (admin, c4, hd1):
        db.add(AtribuicaoLicenca(licenca_id=pbi.id, utilizador_id=x.id))
    db.commit()

    p1 = wf.criar(db, c1, titulo="Outlook pede a palavra-passe repetidamente",
                  descricao="Desde ontem o Outlook pede credenciais de 5 em 5 minutos.",
                  item_id=_item(db, "Email, Outlook ou Teams"),
                  dados={"aplicacao": "Outlook", "sintomas": ["Pede palavra-passe"]})
    wf.executar(db, hd1, p1, "assumir", {})
    wf.comentar(db, hd1, p1, "Vou verificar o perfil do Outlook e o registo no Entra ID.")
    wf.criar(db, c2, titulo="Preciso de um segundo monitor", descricao="Para trabalhar com o simulador e o email.",
             item_id=_item(db, "Monitor"), dados={"quantidade": "1 monitor"})
    wf.criar(db, c3, titulo="Erro ao emitir recibo no Anywhere",
             descricao="Ao emitir o recibo da apólice aparece 'erro de validação'.", item_id=_item(db, "Erro no Anywhere"),
             dados={"modulo": "Recibos e cobranças", "impacto": "Consigo contornar"})
    p4 = wf.criar(db, c3, titulo="Impressora do piso 2 não imprime", descricao="Fica em fila de espera.",
                  item_id=_item(db, "Impressão"), dados={"o_que": "Não imprime"})
    antigo = agora() - timedelta(days=9)  # para o painel mostrar um pedido fora de prazo
    p4.criado_em = p4.sla_inicio = antigo
    p4.prazo_resposta, p4.prazo_resolucao = sla.prazos(p4.prioridade, antigo)
    db.commit()
    p5 = wf.criar(db, c4, titulo="Excel bloqueia ao abrir ficheiros grandes", descricao="Ficheiro de 80 MB.",
                  item_id=_item(db, "Computador lento ou com erros"),
                  dados={"sintomas": ["Bloqueia"]})
    wf.executar(db, hd2, p5, "assumir", {})
    wf.executar(db, hd2, p5, "resolver", {"motivo": "Instalada versão 64 bits do Office e reparado o ficheiro."})


def carregar(db: Session) -> None:
    carregar_catalogo(db)
    if os.getenv("PORTAL_SEED", "0") == "demo":
        carregar_demo(db)
    if os.getenv("PORTAL_AUTH_MODE", "dev") == "dev":
        garantir_administrador(db)
