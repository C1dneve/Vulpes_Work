from types import SimpleNamespace

import pandas as pd

from domain import timeline as T
from views import timeline as timeline_view


def test_timeline_displays_data_notes_even_when_there_are_no_events(monkeypatch):
    warnings: list[str] = []
    infos: list[str] = []
    monkeypatch.setattr(timeline_view.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(timeline_view.st, "warning", warnings.append)
    monkeypatch.setattr(timeline_view.st, "info", infos.append)
    monkeypatch.setattr(timeline_view.V, "tz_note", lambda: "")

    note = "GitHub: exibindo dados antigos; a busca atual falhou."
    alert_note = "Alertas Jira↔GitHub limitados: GitHub indisponível."
    management = SimpleNamespace(
        notes=[note],
        alert_notes=[alert_note],
        timeline=pd.DataFrame(columns=T.TL_COLS),
    )

    timeline_view.render(management, "example.atlassian.net")

    assert warnings == [note, alert_note]
    assert infos == ["Nenhum evento no recorte atual."]
