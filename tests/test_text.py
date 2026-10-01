import pandas as pd

from domain.text import Safe, esc, literal_contains, md_esc


def test_esc_escapes_dangerous_html():
    assert esc('<img src=x onerror="alert(1)">') == "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    assert esc("a & b") == "a &amp; b"
    assert esc("it's") == "it&#x27;s"


def test_esc_handles_none_and_nan():
    assert esc(None) == ""
    assert esc(float("nan")) == ""
    assert esc(pd.NA) == ""


def test_safe_is_not_escaped_twice():
    html_ok = Safe("<b>ok</b>")
    assert esc(html_ok) == "<b>ok</b>"
    assert esc(esc("<x>")) == "&lt;x&gt;"  # esc devolve Safe: não escapa duas vezes


def test_md_esc_neutralizes_markdown_links_and_latex():
    out = md_esc("[click](http://evil) `code` $x$ *b*")
    assert "[" not in out.replace("\\[", "") and "$" not in out.replace("\\$", "")


def test_literal_contains_treats_regex_chars_literally():
    s = pd.Series(["fix (login) bug", "cadastro [v2]", "a*b", None, "normal"])
    assert literal_contains(s, "(login)").tolist() == [True, False, False, False, False]
    assert literal_contains(s, "[v2]").tolist() == [False, True, False, False, False]
    assert literal_contains(s, "*").tolist() == [False, False, True, False, False]
    assert literal_contains(s, "NORMAL").tolist() == [False, False, False, False, True]  # case-insensitive
    assert literal_contains(s, "+").tolist() == [False] * 5  # não levanta re.error
