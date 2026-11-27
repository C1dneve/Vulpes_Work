from types import SimpleNamespace

import pandas as pd

from views import people as people_view


def test_people_displays_data_notes_even_when_there_are_no_people(monkeypatch):
    warnings: list[str] = []
    infos: list[str] = []
    monkeypatch.setattr(people_view.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(people_view.st, "warning", warnings.append)
    monkeypatch.setattr(people_view.st, "info", infos.append)

    note = "GitHub: carga parcial; alertas podem ter falso positivo."
    alert_note = "Alertas de PR desativados: GitHub indisponível."
    management = SimpleNamespace(notes=[note], alert_notes=[alert_note], people=pd.DataFrame())

    people_view.render(management, "example.atlassian.net")

    assert warnings == [note, alert_note]
    assert infos == ["Nenhuma pessoa com tasks ou worklogs no recorte atual."]
