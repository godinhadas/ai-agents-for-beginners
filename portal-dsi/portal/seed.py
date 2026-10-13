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


def carregar_catalogo(db: Session) -> bool:
    if db.scalar(select(ItemCatalogo.id).limit(1)) is not None:
        return False
    for ordem, (tipo, nome, desc, icone, aprov, prio) in enumerate(CATALOGO, start=1):
        db.add(ItemCatalogo(tipo=tipo, nome=nome, descricao=desc, icone=icone, requer_aprovacao=aprov,
                            prioridade_padrao=prio, ordem=ordem * 10))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


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
                  item_id=_item(db, "Email, Outlook ou Teams"))
    wf.executar(db, hd1, p1, "assumir", {})
    wf.comentar(db, hd1, p1, "Vou verificar o perfil do Outlook e o registo no Entra ID.")
    wf.criar(db, c2, titulo="Preciso de um segundo monitor", descricao="Para trabalhar com o simulador e o email.",
             item_id=_item(db, "Monitor"))
    wf.criar(db, c3, titulo="Erro ao emitir recibo no Anywhere",
             descricao="Ao emitir o recibo da apólice aparece 'erro de validação'.", item_id=_item(db, "Erro no Anywhere"))
    p4 = wf.criar(db, c3, titulo="Impressora do piso 2 não imprime", descricao="Fica em fila de espera.",
                  item_id=_item(db, "Impressão"))
    antigo = agora() - timedelta(days=9)  # para o painel mostrar um pedido fora de prazo
    p4.criado_em = p4.sla_inicio = antigo
    p4.prazo_resposta, p4.prazo_resolucao = sla.prazos(p4.prioridade, antigo)
    db.commit()
    p5 = wf.criar(db, c4, titulo="Excel bloqueia ao abrir ficheiros grandes", descricao="Ficheiro de 80 MB.",
                  item_id=_item(db, "Computador lento ou com erros"))
    wf.executar(db, hd2, p5, "assumir", {})
    wf.executar(db, hd2, p5, "resolver", {"motivo": "Instalada versão 64 bits do Office e reparado o ficheiro."})


def carregar(db: Session) -> None:
    carregar_catalogo(db)
    if os.getenv("PORTAL_SEED", "0") == "demo":
        carregar_demo(db)
    if os.getenv("PORTAL_AUTH_MODE", "dev") == "dev":
        garantir_administrador(db)
