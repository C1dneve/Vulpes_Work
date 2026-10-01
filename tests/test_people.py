import pandas as pd

from domain.people import is_bot, nome_exibicao, simplify, slugify, suggest_matches, unmapped_authors


def test_slugify_and_display():
    assert slugify("Vitor Assis Hasman Diniz") == "vitor-assis-hasman-diniz"
    assert slugify("Márcio Álvaro") == "marcio-alvaro"
    assert slugify(None) == "nenhum" and slugify("") == "nenhum"
    assert nome_exibicao("cid-daniel-neves") == "Cid Daniel Neves" and nome_exibicao("nenhum") == "Nenhum"


def test_bots_are_detected_not_treated_as_developers():
    assert is_bot("dependabot[bot]")
    assert is_bot("github-actions[bot]")
    assert is_bot("someone", author_type="Bot")
    assert is_bot("renovate")
    assert is_bot("acme-ci", extra=("acme-ci",))
    assert not is_bot("samuelmartins00", "Samuel Martins")


def test_mapping_is_separator_insensitive(mapper):
    assert mapper.github("SamuelMartins00").slug == "samuel-martins"
    assert mapper.github("samuel-martins-00").mapped  # simplify iguala login com/sem separador
    assert mapper.jira("Samuel Martins") == "samuel-martins"


def test_unmapped_author_is_flagged_not_guessed(mapper):
    a = mapper.github(None, "Pedro P.")
    assert not a.mapped and a.slug == "pedro-p"


def test_known_slug_counts_as_mapped(mapper):
    assert mapper.github("pedro-pereira-rodrigues").mapped


def test_suggestions(mapper):
    slugs = sorted(mapper.known_slugs)
    top = suggest_matches(None, "Pedro P.", slugs)
    assert top and top[0][0] == "pedro-pereira-rodrigues"
    assert suggest_matches("zzzzz", None, slugs) == []


def test_unmapped_authors_panel_ignores_bots_and_merges():
    df = pd.DataFrame([
        {"author_login": None, "author_name": "Pedro P.", "author_email": "p@x", "author_mapped": False, "kind": "human"},
        {"author_login": None, "author_name": "Pedro P.", "author_email": "p@x", "author_mapped": False, "kind": "human"},
        {"author_login": "dependabot[bot]", "author_name": "d", "author_email": "d@x", "author_mapped": False, "kind": "bot"},
        {"author_login": "ok", "author_name": "Ok", "author_email": "o@x", "author_mapped": True, "kind": "human"},
    ])
    out = unmapped_authors(df)
    assert len(out) == 1 and out.iloc[0]["commits"] == 2 and out.iloc[0]["author_name"] == "Pedro P."


def test_simplify():
    assert simplify("Guilherme-Leite1701") == "guilhermeleite1701"
