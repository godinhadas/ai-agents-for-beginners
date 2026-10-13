"""Dados de demonstração (fictícios, excepto a estrutura típica da MHAIS)."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import pedidos as wf, sla
from .models import Departamento, Equipamento, ItemCatalogo, Licenca, AtribuicaoLicenca, Utilizador, agora


def carregar(db: Session) -> bool:
    """Carrega a demonstração só numa base vazia. Seguro se dois arranques correrem em simultâneo."""
    if any(db.scalar(select(m.id).limit(1)) is not None for m in (Utilizador, Departamento, ItemCatalogo)):
        return False
    try:
        _carregar(db)
    except IntegrityError:
        db.rollback()  # outro processo carregou primeiro
        return False
    return True


def _carregar(db: Session) -> None:

    dep = {n: Departamento(nome=n) for n in
           ("DSI", "Comercial", "Sinistros", "Financeira", "Recursos Humanos", "Administração")}
    db.add_all(dep.values())
    db.flush()

    def u(nome, email, d, perfil="colaborador", chefia=None):
        x = Utilizador(nome=nome, email=f"{email}@mhais.example", departamento_id=dep[d].id, perfil=perfil,
                       chefia_id=chefia.id if chefia else None)
        db.add(x)
        db.flush()
        return x

    admin = u("António Godinho", "antonio.godinho", "DSI", "admin")
    hd1 = u("Paulo Cassule", "paulo.cassule", "DSI", "helpdesk", admin)
    hd2 = u("Edna Muhongo", "edna.muhongo", "DSI", "helpdesk", admin)
    dir_com = u("Helena Tavares", "helena.tavares", "Comercial", "chefia")
    dir_sin = u("Mateus Kiala", "mateus.kiala", "Sinistros", "chefia")
    dir_fin = u("Rosa Ndala", "rosa.ndala", "Financeira", "chefia")
    c1 = u("Joana Sebastião", "joana.sebastiao", "Comercial", chefia=dir_com)
    c2 = u("Ricardo Manuel", "ricardo.manuel", "Comercial", chefia=dir_com)
    c3 = u("Wilson Capitango", "wilson.capitango", "Sinistros", chefia=dir_sin)
    c4 = u("Teresa Lukeny", "teresa.lukeny", "Financeira", chefia=dir_fin)
    u("Domingos Pedro", "domingos.pedro", "Recursos Humanos")

    cat = {}
    for nome, tipo, aprov, prio in [
        ("Avaria ou erro em computador", "incidente", False, "media"),
        ("Problema com impressora", "incidente", False, "baixa"),
        ("Email / Outlook não funciona", "incidente", False, "alta"),
        ("Sem acesso à rede ou internet", "incidente", False, "alta"),
        ("Portátil novo ou substituição", "equipamento", True, "media"),
        ("Monitor", "equipamento", True, "baixa"),
        ("Pen drive", "equipamento", True, "baixa"),
        ("Periférico (rato, teclado, headset)", "equipamento", True, "baixa"),
        ("Licença Microsoft 365", "licenca", True, "media"),
        ("Licença Power BI Pro", "licenca", True, "media"),
        ("Outro software", "licenca", True, "media"),
        ("Acesso a pasta partilhada", "acesso", True, "media"),
        ("Acesso VPN", "acesso", True, "media"),
        ("Acesso a aplicação de negócio", "acesso", True, "media"),
        ("Dúvida ou pedido de informação", "informacao", False, "baixa"),
    ]:
        cat[nome] = ItemCatalogo(nome=nome, tipo=tipo, requer_aprovacao=aprov, prioridade_padrao=prio)
    db.add_all(cat.values())

    hoje = date.today()
    eqs = [
        Equipamento(etiqueta="MH-PC-001", tipo="Portátil", marca="Dell", modelo="Latitude 5450", numero_serie="DL5450A01",
                    estado="atribuido", utilizador_id=c1.id, data_compra=hoje - timedelta(days=200),
                    garantia_ate=hoje + timedelta(days=895), fornecedor="Fornecedor A"),
        Equipamento(etiqueta="MH-PC-002", tipo="Portátil", marca="Dell", modelo="Latitude 5450", numero_serie="DL5450A02",
                    estado="atribuido", utilizador_id=c3.id, data_compra=hoje - timedelta(days=200),
                    garantia_ate=hoje + timedelta(days=895), fornecedor="Fornecedor A"),
        Equipamento(etiqueta="MH-PC-003", tipo="Portátil", marca="HP", modelo="EliteBook 840 G11", numero_serie="HP840B03",
                    estado="stock", data_compra=hoje - timedelta(days=30), garantia_ate=hoje + timedelta(days=1065),
                    fornecedor="Fornecedor B"),
        Equipamento(etiqueta="MH-PC-004", tipo="Portátil", marca="HP", modelo="EliteBook 840 G9", numero_serie="HP840B04",
                    estado="reparacao", data_compra=hoje - timedelta(days=1040), garantia_ate=hoje + timedelta(days=55),
                    fornecedor="Fornecedor B", notas="Teclado com teclas a falhar"),
        Equipamento(etiqueta="MH-MON-001", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C01",
                    estado="atribuido", utilizador_id=c1.id, garantia_ate=hoje + timedelta(days=700)),
        Equipamento(etiqueta="MH-MON-002", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C02",
                    estado="stock", garantia_ate=hoje + timedelta(days=700)),
        Equipamento(etiqueta="MH-MON-003", tipo="Monitor", marca="Dell", modelo="P2425H", numero_serie="DLP24C03",
                    estado="stock", garantia_ate=hoje + timedelta(days=700)),
        Equipamento(etiqueta="MH-USB-001", tipo="Pen drive", marca="Kingston", modelo="DataTraveler 64 GB (cifrada)",
                    estado="stock"),
        Equipamento(etiqueta="MH-USB-002", tipo="Pen drive", marca="Kingston", modelo="DataTraveler 64 GB (cifrada)",
                    estado="stock"),
        Equipamento(etiqueta="MH-IMP-001", tipo="Impressora", marca="HP", modelo="LaserJet Pro MFP 4102",
                    numero_serie="HPLJ4102D1", estado="atribuido", utilizador_id=dir_com.id,
                    garantia_ate=hoje + timedelta(days=80)),
    ]
    db.add_all(eqs)

    m365 = Licenca(produto="Microsoft 365 Business Premium", fornecedor="Microsoft (CSP)", quantidade=50,
                   custo_anual=None, renovacao_em=hoje + timedelta(days=45))
    pbi = Licenca(produto="Power BI Pro", fornecedor="Microsoft (CSP)", quantidade=3, renovacao_em=hoje + timedelta(days=45))
    eset = Licenca(produto="ESET PROTECT Entry", fornecedor="ESET", quantidade=50, renovacao_em=hoje + timedelta(days=210))
    acrobat = Licenca(produto="Adobe Acrobat Pro", fornecedor="Adobe", quantidade=2, renovacao_em=hoje + timedelta(days=120))
    db.add_all([m365, pbi, eset, acrobat])
    db.flush()
    todos = db.scalars(select(Utilizador)).all()
    for x in todos:
        db.add(AtribuicaoLicenca(licenca_id=m365.id, utilizador_id=x.id))
        db.add(AtribuicaoLicenca(licenca_id=eset.id, utilizador_id=x.id))
    for x in (admin, dir_fin, c4):
        db.add(AtribuicaoLicenca(licenca_id=pbi.id, utilizador_id=x.id))
    db.add(AtribuicaoLicenca(licenca_id=acrobat.id, utilizador_id=dir_com.id))
    db.commit()

    # Pedidos de exemplo, criados pelo próprio circuito para ficarem coerentes.
    p1 = wf.criar(db, c1, titulo="Outlook pede a palavra-passe repetidamente",
                  descricao="Desde ontem o Outlook pede credenciais de 5 em 5 minutos.",
                  item_id=cat["Email / Outlook não funciona"].id)
    wf.executar(db, hd1, p1, "assumir", {})
    wf.comentar(db, hd1, p1, "Vou verificar o perfil do Outlook e o registo no Entra ID.")

    wf.criar(db, c2, titulo="Preciso de um segundo monitor",
             descricao="Para trabalhar com o simulador de prémios e o email em simultâneo.",
             item_id=cat["Monitor"].id)

    wf.criar(db, dir_com, beneficiario_id=c2.id, titulo="Acesso à pasta Comercial\\Propostas 2026",
             descricao="O Ricardo precisa de acesso de escrita à pasta das propostas.",
             item_id=cat["Acesso a pasta partilhada"].id)

    p4 = wf.criar(db, c3, titulo="Impressora do piso 2 não imprime",
                  descricao="Fica em fila de espera e não sai nada.", item_id=cat["Problema com impressora"].id)
    # Simula um pedido antigo para o painel mostrar SLA violado.
    antigo = agora() - timedelta(days=9)
    p4.criado_em = antigo
    p4.sla_inicio = antigo
    p4.prazo_resposta, p4.prazo_resolucao = sla.prazos(p4.prioridade, antigo)
    db.commit()

    p5 = wf.criar(db, c4, titulo="Excel bloqueia ao abrir ficheiros grandes",
                  descricao="Ficheiro de reconciliação bancária com 80 MB.", item_id=cat["Avaria ou erro em computador"].id)
    wf.executar(db, hd2, p5, "assumir", {})
    wf.executar(db, hd2, p5, "resolver", {"motivo": "Instalada versão 64 bits do Office e reparado o ficheiro."})
