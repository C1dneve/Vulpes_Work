"""Página Issues, com seleção delegada ao contexto de composição do app."""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

from domain.text import literal_contains
from ui_components import STATUS_COR

SummaryBuilder = Callable[[pd.DataFrame], pd.DataFrame]
TaskSelected = Callable[[str], None]


def render(
    items: pd.DataFrame,
    *,
    summarize: SummaryBuilder,
    on_task_selected: TaskSelected,
) -> None:
    """Renderiza a lista filtrável de issues e delega a abertura do detalhe."""
    first, second = st.columns([2, 1])
    status = first.multiselect("Status", list(STATUS_COR), default=list(STATUS_COR))
    search = second.text_input("Buscar", placeholder="ID ou texto")
    view = summarize(items[items["status_group"].isin(status)])
    if search:  # Busca literal: caracteres como (, [, * e + não são interpretados como regex.
        view = view[
            literal_contains(view["Task"], search)
            | literal_contains(view["Resumo"], search)
            | literal_contains(view["User Story"], search)
        ]

    st.caption("Clique em uma linha para ver os detalhes e os commits (com as branches) da task.")
    event = st.dataframe(
        view.drop(columns="subtask_key"),
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if event.selection.rows:
        key = view.iloc[event.selection.rows[0]]["subtask_key"]
        on_task_selected(str(key))
