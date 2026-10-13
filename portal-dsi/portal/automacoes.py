"""Automações: acções técnicas executadas pelo portal, com registo no histórico do pedido.

Regras de segurança:
- cada automação está desligada até ser activada no .env;
- por omissão corre com um clique do técnico ("Executar automaticamente");
- só corre sozinha, sem técnico, se PORTAL_AUTOMACAO_IMEDIATA=1 E o pedido for do próprio
  (quem pede = beneficiário, autenticado com a conta Microsoft). Pedidos de A para B passam sempre por um técnico.

Automações disponíveis:
- desbloquear_ad: desbloqueia a conta no Active Directory (Unlock-ADAccount).
  Requer o portal num servidor do domínio, com o módulo ActiveDirectory (RSAT) e uma conta de serviço
  com permissão delegada só para desbloquear contas (nunca Domain Admin). Activa-se com PORTAL_AUTOMACAO_AD=1.
"""

import json
import logging
import os
import re
import subprocess

log = logging.getLogger("portal.automacoes")
EMAIL_SEGURO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

DESCRICAO = {"desbloquear_ad": "Desbloquear conta no Active Directory"}


def _executar_powershell(script: str) -> tuple[int, str]:
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout or r.stderr or "").strip()


# Ponto de substituição nos testes.
executor = _executar_powershell


def desbloquear_ad(email: str) -> tuple[bool, str]:
    if not EMAIL_SEGURO.match(email):
        return False, "Email do utilizador com formato inválido para automação."
    script = (
        f"$ErrorActionPreference='Stop'; Import-Module ActiveDirectory; "
        f"$u = Get-ADUser -Filter \"UserPrincipalName -eq '{email}' -or mail -eq '{email}'\" -Properties LockedOut; "
        f"if (-not $u) {{ Write-Output 'NAO_ENCONTRADO'; exit 2 }}; "
        f"if (-not $u.LockedOut) {{ Write-Output ('JA_DESBLOQUEADA ' + $u.SamAccountName); exit 0 }}; "
        f"Unlock-ADAccount -Identity $u; Write-Output ('DESBLOQUEADA ' + $u.SamAccountName)"
    )
    try:
        codigo, saida = executor(script)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Não foi possível executar o PowerShell: {exc}"
    if codigo == 0 and saida.startswith("DESBLOQUEADA"):
        return True, f"Conta {saida.split()[-1]} desbloqueada no Active Directory."
    if codigo == 0 and saida.startswith("JA_DESBLOQUEADA"):
        return True, f"A conta {saida.split()[-1]} não estava bloqueada no Active Directory."
    if "NAO_ENCONTRADO" in saida:
        return False, f"Utilizador {email} não encontrado no Active Directory."
    return False, f"Falha no Active Directory: {saida[:300]}"


def activa(nome: str | None) -> bool:
    return nome == "desbloquear_ad" and os.getenv("PORTAL_AUTOMACAO_AD", "0") == "1"


def aplicavel(p) -> bool:
    """A automação do item aplica-se a este pedido em concreto?"""
    if not p.item or not activa(p.item.automacao):
        return False
    dados = json.loads(p.dados or "{}")
    if p.item.automacao == "desbloquear_ad":
        return dados.get("sistema", "Windows / rede") == "Windows / rede"
    return False


def imediata(p) -> bool:
    return (os.getenv("PORTAL_AUTOMACAO_IMEDIATA", "0") == "1" and p.criado_por_id == p.beneficiario_id
            and aplicavel(p))


def executar(p) -> tuple[bool, str]:
    if p.item.automacao == "desbloquear_ad":
        return desbloquear_ad(p.beneficiario.email)
    return False, "Automação desconhecida."
