"""Cliente mínimo do Microsoft Graph com credenciais da aplicação (client credentials).

Permissões de aplicação necessárias no registo da app no Entra ID:
- User.Read.All          sincronizar colaboradores, departamentos e chefias
- Mail.Send              enviar notificações a partir da caixa do Helpdesk
- Mail.ReadWrite         ler a caixa do Helpdesk e marcar emails como lidos
Recomenda-se limitar Mail.* à caixa do Helpdesk com uma Application Access Policy
(ou RBAC for Applications) no Exchange Online.
"""

import os

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphIndisponivel(RuntimeError):
    pass


def configurado() -> bool:
    return all(os.getenv(v) for v in ("ENTRA_TENANT_ID", "ENTRA_CLIENT_ID", "ENTRA_CLIENT_SECRET"))


class Graph:
    def __init__(self):
        if not configurado():
            raise GraphIndisponivel("Defina ENTRA_TENANT_ID, ENTRA_CLIENT_ID e ENTRA_CLIENT_SECRET no .env.")
        import msal

        self._app = msal.ConfidentialClientApplication(
            os.environ["ENTRA_CLIENT_ID"],
            authority=f"https://login.microsoftonline.com/{os.environ['ENTRA_TENANT_ID']}",
            client_credential=os.environ["ENTRA_CLIENT_SECRET"],
        )
        self._http = httpx.Client(timeout=30)

    def _token(self) -> str:
        r = self._app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in r:
            raise GraphIndisponivel(f"Falha a obter token do Graph: {r.get('error_description') or r.get('error')}")
        return r["access_token"]

    def _pedido(self, metodo: str, caminho: str, **kw) -> httpx.Response:
        url = caminho if caminho.startswith("http") else GRAPH + caminho
        headers = {"Authorization": f"Bearer {self._token()}", **kw.pop("headers", {})}
        r = self._http.request(metodo, url, headers=headers, **kw)
        if r.status_code >= 400:
            raise GraphIndisponivel(f"Graph {metodo} {caminho}: {r.status_code} {r.text[:300]}")
        return r

    def get(self, caminho: str, params: dict | None = None, headers: dict | None = None) -> dict:
        return self._pedido("GET", caminho, params=params, headers=headers or {}).json()

    def get_todos(self, caminho: str, params: dict | None = None, headers: dict | None = None) -> list[dict]:
        """Segue a paginação (@odata.nextLink)."""
        itens, pagina = [], self.get(caminho, params, headers)
        while True:
            itens += pagina.get("value", [])
            if not (seguinte := pagina.get("@odata.nextLink")):
                return itens
            pagina = self.get(seguinte, headers=headers)

    def get_opcional(self, caminho: str, params: dict | None = None) -> dict | None:
        """GET que devolve None em 404 (ex.: utilizador sem chefia)."""
        url = GRAPH + caminho
        r = self._http.get(url, params=params, headers={"Authorization": f"Bearer {self._token()}"})
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise GraphIndisponivel(f"Graph GET {caminho}: {r.status_code} {r.text[:300]}")
        return r.json()

    def post(self, caminho: str, corpo: dict) -> None:
        self._pedido("POST", caminho, json=corpo)

    def patch(self, caminho: str, corpo: dict) -> None:
        self._pedido("PATCH", caminho, json=corpo)
