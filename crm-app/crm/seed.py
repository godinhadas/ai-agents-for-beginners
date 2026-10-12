"""Dados de demonstração (fictícios). Datas relativas a hoje para o painel ter sempre conteúdo."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Actividade, Apolice, Cliente, Mediador, Oportunidade, Sinistro


def carregar(db: Session) -> bool:
    if db.scalar(select(Cliente.id).limit(1)) is not None:
        return False
    hoje = date.today()
    d = lambda dias: hoje + timedelta(days=dias)  # noqa: E731

    med = [
        Mediador(codigo="MED-001", nome="Kwanza Corretores, Lda", email="geral@kwanzacorretores.example",
                 telefone="+244 923 000 101", comissao_pct=12),
        Mediador(codigo="MED-002", nome="Atlântico Mediação", email="info@atlanticomed.example",
                 telefone="+244 923 000 202", comissao_pct=10),
    ]
    db.add_all(med)
    db.flush()

    cli = [
        Cliente(tipo="empresa", nome="Construções Kalandula, SA", nif="5417000001", email="financeiro@kalandula.example",
                telefone="+244 222 000 001", provincia="Luanda", mediador_id=med[0].id),
        Cliente(tipo="empresa", nome="Transportes Benguela Express, Lda", nif="5417000002",
                email="frota@benguelaexpress.example", telefone="+244 272 000 002", provincia="Benguela",
                mediador_id=med[1].id),
        Cliente(tipo="particular", nome="Mariana Lopes da Silva", nif="004512345LA041", email="mariana.silva@example.ao",
                telefone="+244 923 111 222", provincia="Luanda"),
        Cliente(tipo="particular", nome="João Baptista Neto", nif="003987654HO039", email="jb.neto@example.ao",
                telefone="+244 924 333 444", provincia="Huíla", mediador_id=med[0].id),
        Cliente(tipo="empresa", nome="Clínica Esperança do Lubango", nif="5417000005", email="admin@clinicaesperanca.example",
                telefone="+244 261 000 005", provincia="Huíla", mediador_id=med[1].id),
        Cliente(tipo="particular", nome="Teresa Mbanza Cassoma", nif="006543210UE047", email="teresa.cassoma@example.ao",
                telefone="+244 925 555 666", provincia="Uíge"),
    ]
    db.add_all(cli)
    db.flush()

    ap = [
        Apolice(numero="AUT-2025-0001", cliente_id=cli[1].id, ramo="Automóvel", premio_anual=18_500_000,
                capital_seguro=450_000_000, data_inicio=d(-345), data_fim=d(20)),
        Apolice(numero="AT-2025-0002", cliente_id=cli[0].id, ramo="Acidentes de Trabalho", premio_anual=32_000_000,
                capital_seguro=900_000_000, data_inicio=d(-320), data_fim=d(45)),
        Apolice(numero="MR-2025-0003", cliente_id=cli[0].id, ramo="Multirriscos", premio_anual=12_750_000,
                capital_seguro=1_200_000_000, data_inicio=d(-200), data_fim=d(165)),
        Apolice(numero="SAU-2025-0004", cliente_id=cli[4].id, ramo="Saúde", premio_anual=24_000_000,
                capital_seguro=300_000_000, data_inicio=d(-300), data_fim=d(65)),
        Apolice(numero="AUT-2025-0005", cliente_id=cli[2].id, ramo="Automóvel", premio_anual=480_000,
                capital_seguro=15_000_000, data_inicio=d(-355), data_fim=d(10)),
        Apolice(numero="VID-2025-0006", cliente_id=cli[3].id, ramo="Vida", premio_anual=960_000,
                capital_seguro=50_000_000, data_inicio=d(-100), data_fim=d(265)),
        Apolice(numero="VIA-2025-0007", cliente_id=cli[5].id, ramo="Viagem", premio_anual=85_000,
                capital_seguro=30_000_000, data_inicio=d(-400), data_fim=d(-35), estado="expirada"),
    ]
    db.add_all(ap)
    db.flush()

    db.add_all([
        Sinistro(numero="SIN-2025-0001", apolice_id=ap[0].id, data_ocorrencia=d(-40),
                 descricao="Colisão de camião na EN100, danos na cabine.", valor_reclamado=6_200_000,
                 estado="em_analise"),
        Sinistro(numero="SIN-2025-0002", apolice_id=ap[1].id, data_ocorrencia=d(-12),
                 descricao="Queda em altura em obra no Talatona; trabalhador hospitalizado.",
                 valor_reclamado=3_400_000, estado="participado"),
        Sinistro(numero="SIN-2025-0003", apolice_id=ap[4].id, data_ocorrencia=d(-90),
                 descricao="Quebra de pára-brisas.", valor_reclamado=350_000, valor_pago=350_000, estado="pago"),
    ])
    db.add_all([
        Oportunidade(cliente_id=cli[1].id, titulo="Responsabilidade civil de mercadorias transportadas",
                     ramo="Responsabilidade Civil", valor_estimado=7_500_000, fase="proposta", data_prevista=d(30)),
        Oportunidade(cliente_id=cli[0].id, titulo="Seguro de saúde colectivo (180 colaboradores)", ramo="Saúde",
                     valor_estimado=41_000_000, fase="negociacao", data_prevista=d(25)),
        Oportunidade(cliente_id=cli[4].id, titulo="Multirriscos das instalações da clínica", ramo="Multirriscos",
                     valor_estimado=5_200_000, fase="prospeccao", data_prevista=d(60)),
        Oportunidade(cliente_id=cli[2].id, titulo="Seguro de vida associado a crédito habitação", ramo="Vida",
                     valor_estimado=720_000, fase="ganha", data_prevista=d(-5)),
    ])
    db.add_all([
        Actividade(cliente_id=cli[0].id, tipo="reuniao", assunto="Apresentação da proposta de saúde colectivo",
                   descricao="Reunião com a directora financeira; pediram revisão da franquia.", data=d(-3),
                   concluida=True),
        Actividade(cliente_id=cli[1].id, tipo="chamada", assunto="Ponto de situação do sinistro SIN-2025-0001",
                   data=d(-7), concluida=True),
        Actividade(cliente_id=cli[2].id, tipo="tarefa", assunto="Enviar aviso de renovação da apólice automóvel",
                   data=d(1)),
    ])
    db.commit()
    return True
