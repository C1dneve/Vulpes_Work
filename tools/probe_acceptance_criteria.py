#!/usr/bin/env python3
"""Lê critérios de aceite do Jira Cloud usando somente requisições GET.

O relatório salvo contém apenas hash curto da issue, tipo, classificação, contagens e motivos.
Nunca grava descrição ADF, nomes de pessoas, e-mails, tokens ou a chave original da issue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from requests.auth import HTTPBasicAuth

# Ao executar o arquivo diretamente, Python coloca tools/ (e não a raiz) em sys.path.
# Adicionamos somente a raiz deste projeto para resolver os pacotes locais.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.http import HttpClient  # noqa: E402
from settings import load_settings  # noqa: E402
from tools.validate_real_apis import Redactor  # noqa: E402

LIST_TYPES = {"taskList", "bulletList", "orderedList"}


@dataclass(frozen=True)
class Extraction:
    classification: str
    item_count: int
    invalid_item_count: int
    reasons: tuple[str, ...]


def normalize_heading(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]", "", without_accents)


def node_text(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    pieces: list[str] = []
    if isinstance(node.get("text"), str):
        pieces.append(node["text"])
    for child in node.get("content", []) if isinstance(node.get("content"), list) else []:
        if isinstance(child, dict) and child.get("type") not in LIST_TYPES:
            pieces.append(node_text(child))
    return " ".join(piece for piece in pieces if piece).strip()


def _list_items(node: Any):
    if not isinstance(node, dict) or node.get("type") not in LIST_TYPES:
        return
    children = node.get("content", [])
    if not isinstance(children, list):
        return
    for item in children:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"listItem", "taskItem"}:
            yield node_text(item)
            nested = item.get("content", [])
            if isinstance(nested, list):
                for child in nested:
                    if isinstance(child, dict) and child.get("type") in LIST_TYPES:
                        yield from _list_items(child)
        elif item.get("type") in LIST_TYPES:
            yield from _list_items(item)


def extract_acceptance_criteria(description: Any) -> Extraction:
    """Localiza a seção e coleta itens de listas ADF, inclusive aninhadas."""
    content = description.get("content", []) if isinstance(description, dict) else []
    if not isinstance(content, list):
        content = []
    section_index = None
    for index, block in enumerate(content):
        if isinstance(block, dict) and block.get("type") == "heading":
            if normalize_heading(node_text(block)) == "criteriosdeaceite":
                section_index = index
                break
    if section_index is None:
        return Extraction("sem_secao", 0, 0, ("secao_ausente",))

    items: list[str] = []
    for block in content[section_index + 1:]:
        if isinstance(block, dict) and block.get("type") == "heading":
            break
        if isinstance(block, dict) and block.get("type") in LIST_TYPES:
            items.extend(_list_items(block))
    if not items:
        return Extraction("secao_vazia", 0, 0, ("nenhum_item_de_lista",))

    invalid_reasons: list[str] = []
    invalid_count = 0
    for item in items:
        if not item.strip():
            invalid_count += 1
            invalid_reasons.append("item_vazio")
        elif not re.search(r"[\w]", item, flags=re.UNICODE):
            invalid_count += 1
            invalid_reasons.append("somente_pontuacao")
    unique_reasons = tuple(dict.fromkeys(invalid_reasons))
    classification = "ok_com_itens_invalidos" if invalid_count else "ok"
    return Extraction(classification, len(items), invalid_count, unique_reasons)


def issue_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica a estrutura da seção de critérios de aceite no Jira Cloud (somente GET).")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--keys", help="Chaves separadas por vírgula, por exemplo PROJ-1,PROJ-2")
    source.add_argument("--jql", help="JQL para selecionar issues; somente leitura")
    parser.add_argument("--max", type=int, default=20, dest="max_issues", help="Limite de issues para --jql (máximo 20; padrão 20)")
    parser.add_argument("--output-dir", type=Path, default=Path("tools/validation_output"), help=argparse.SUPPRESS)
    return parser


def _load_keys(http: HttpClient, domain: str, args: argparse.Namespace) -> list[str]:
    base = f"https://{domain}/rest/api/3"
    if args.keys:
        keys = [key.strip() for key in args.keys.split(",") if key.strip()]
    else:
        if args.max_issues < 1 or args.max_issues > 20:
            raise ValueError("--max deve estar entre 1 e 20")
        response = http.get_json(f"{base}/search/jql", params={
            "jql": args.jql,
            "maxResults": args.max_issues,
            "fields": "issuetype",
        })
        issues = response.get("issues", []) if isinstance(response, dict) else []
        keys = [str(issue["key"]) for issue in issues if isinstance(issue, dict) and issue.get("key")]
    if len(keys) > 20:
        raise ValueError("o limite desta ferramenta é de 20 issues")
    if not keys:
        raise ValueError("nenhuma issue foi encontrada")
    return keys


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    if not settings.ready:
        raise RuntimeError("Variáveis obrigatórias ausentes: " + ", ".join(settings.missing_env))
    redactor = Redactor()
    redactor.add(settings.jira.token, settings.jira.email)
    http = HttpClient("Jira", headers={"Accept": "application/json"},
                      auth=HTTPBasicAuth(settings.jira.email, settings.jira.token))
    base = f"https://{settings.jira.domain}/rest/api/3"
    keys = _load_keys(http, settings.jira.domain, args)
    results: list[dict[str, Any]] = []

    for key in keys:
        try:
            issue = http.get_json(f"{base}/issue/{quote(key, safe='')}", params={"fields": "description,issuetype"})
            fields = issue.get("fields", {}) if isinstance(issue, dict) else {}
            issue_type = fields.get("issuetype") if isinstance(fields, dict) else None
            type_name = issue_type.get("name", "desconhecido") if isinstance(issue_type, dict) else "desconhecido"
            extraction = extract_acceptance_criteria(fields.get("description") if isinstance(fields, dict) else None)
            result = {
                "issue_hash": issue_hash(key),
                "type": redactor(str(type_name))[:60],
                **asdict(extraction),
            }
            result["reasons"] = list(result["reasons"])
            results.append(result)
        except Exception:
            # Não propagar corpo de erro da API nem URLs/credenciais para o relatório.
            results.append({
                "issue_hash": issue_hash(key),
                "type": "desconhecido",
                "classification": "falha_api",
                "item_count": 0,
                "invalid_item_count": 0,
                "reasons": ["nao_foi_possivel_ler_issue"],
            })

    total = len(results)
    valid = sum(item["classification"] == "ok" for item in results)
    with_section = sum(item["classification"] in {"ok", "ok_com_itens_invalidos"} for item in results)
    return {
        "total_issues": total,
        "totals": {
            "sem_secao": sum(item["classification"] == "sem_secao" for item in results),
            "secao_vazia": sum(item["classification"] == "secao_vazia" for item in results),
            "ok": valid,
            "ok_com_itens_invalidos": sum(item["classification"] == "ok_com_itens_invalidos" for item in results),
            "falha_api": sum(item["classification"] == "falha_api" for item in results),
        },
        "percentages": {
            "com_secao": round(with_section * 100 / total, 1) if total else 0.0,
            "ok_sem_itens_invalidos": round(valid * 100 / total, 1) if total else 0.0,
        },
        "issues": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_probe(args)
    except Exception:
        print("Falha na leitura sanitizada; confira as variáveis obrigatórias e a conectividade local.", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "acceptance_criteria.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Issues analisadas: {report['total_issues']}")
    print("Classificações: " + ", ".join(f"{name}={count}" for name, count in report["totals"].items()))
    print(f"Issues com seção: {report['percentages']['com_secao']}%")
    print(f"Issues sem itens inválidos: {report['percentages']['ok_sem_itens_invalidos']}%")
    print(f"Relatório sanitizado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
