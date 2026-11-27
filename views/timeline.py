"""Timeline: eventos cronológicos da Sprint (criação, status, worklog, commit, PR, conclusão)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from domain import timeline as T
from services.mgmt import Mgmt
from ui_components import style_fig
from views import common as V
from views.now import JIRA_KEY


def render(m: Mgmt, domain: str) -> None:
    st.caption("Primeira visão cronológica da Sprint, montada com o que o Jira e o GitHub fornecem. Não é uma reconstrução perfeita: "
               "revisor e o momento em que a PR saiu de rascunho não são coletados. " + V.tz_note())
    for note in [*m.notes, *m.alert_notes]:
        st.warning(note)
    tl = m.timeline
    if tl.empty:
        st.info("Nenhum evento no recorte atual.")
        return
    si = m.sprint_info
    f1, f2, f3 = st.columns([2, 1, 1])
    types = f1.multiselect("Tipos de evento", T.EVENT_TYPES, default=T.EVENT_TYPES, key="tl_types")
    people = sorted({p for p in tl["person"].dropna()}, key=V.pessoa)
    who = f2.selectbox("Pessoa", ["Todas"] + people, format_func=lambda x: x if x == "Todas" else V.pessoa(x), key="tl_who")
    everything = f3.checkbox("Mostrar fora da janela da Sprint", value=si is None, key="tl_all",
                             help="Por padrão, só os eventos entre o início da Sprint e hoje (ou o fim dela).")
    sel = tl[tl["type"].isin(types)]
    if who != "Todas":
        sel = sel[sel["person"] == who]
    if si is not None and not everything and not pd.isna(si["start"]):
        end = si["end"] if si["state"] == "closed" and not pd.isna(si["end"]) else m.now
        sel = sel[(sel["ts"] >= si["start"]) & (sel["ts"] <= end)]
    if sel.empty:
        st.info("Nenhum evento com esses filtros.")
        return
    plot = sel.assign(Quando=sel["ts"].dt.tz_localize(None), Tipo=sel["type"], Item=sel["key"], Pessoa=sel["person"].map(V.pessoa), Detalhe=sel["detail"])
    fig = px.scatter(plot, x="Quando", y="Tipo", color="Tipo", hover_data={"Item": True, "Pessoa": True, "Detalhe": True, "Tipo": False, "Quando": "|%d/%m %H:%M"},
                     category_orders={"Tipo": T.EVENT_TYPES[::-1]})
    fig.update_traces(marker=dict(size=10, opacity=0.8))
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title=None)
    st.plotly_chart(style_fig(fig, 340), use_container_width=True)
    st.markdown(f"**{len(sel)} evento(s)** · mais recentes primeiro")
    rows = sel.iloc[::-1]
    st.dataframe(pd.DataFrame({
        "Quando": rows["ts"].dt.strftime("%d/%m %H:%M"), "Tipo": rows["type"], "Item": rows["key"], "Título": rows["title"],
        "Pessoa": rows["person"].map(V.pessoa), "Detalhe": rows["detail"],
        "Jira": [V.jira_url(domain, k) if JIRA_KEY.match(str(k)) else None for k in rows["key"]], "GitHub": rows["url"]}),
        hide_index=True, use_container_width=True,
        column_config={"Jira": V.jira_col(), "GitHub": st.column_config.LinkColumn("GitHub", display_text=r"github\.com/(.+)$")})
