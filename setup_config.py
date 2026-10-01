"""Lista os nomes (slugs) dos usuários atribuíveis do Jira, para preencher `dev_mapping` no config.json."""
import requests
from requests.auth import HTTPBasicAuth

from domain.people import slugify
from settings import load_settings


def listar_usuarios(s, page_size=50):
    """Pagina /user/assignable/search (o padrão da API são só 50 por página)."""
    auth, out, start = HTTPBasicAuth(s.jira.email, s.jira.token), [], 0
    while True:
        r = requests.get(f"https://{s.jira.domain}/rest/api/3/user/assignable/search",
                         params={"project": s.jira.project, "startAt": start, "maxResults": page_size},
                         auth=auth, headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        page = r.json()
        out += page
        if not page:
            return out
        start += len(page)


if __name__ == "__main__":
    s = load_settings()
    if not s.ready:
        raise SystemExit(f"Variáveis ausentes: {', '.join(s.missing_env)} (preencha o .env)")
    try:
        nomes = [slugify(u["displayName"]) for u in listar_usuarios(s) if u.get("accountType") == "atlassian"]
    except requests.RequestException as e:
        raise SystemExit(f"Erro ao buscar usuários do Jira: {e}") from e
    print("Nome dos autores no Jira:")
    print(nomes)
