"""Tema escuro Vulpes Work + componentes HTML reutilizáveis."""
import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from domain import statuses as S
from domain import timeutil
from domain.text import Safe, esc

ASSETS = Path(__file__).parent / "assets"
C = dict(bg="#060B1C", panel="#0B1226", border="#1B2547", text="#E6EAF5", muted="#8A94B4",
         primary="#4F46E5", green="#22D3A0", blue="#3B82F6", red="#F43F5E", purple="#A78BFA", gray="#64748B")
STATUS_COR = {S.CONCLUIDA: C["green"], S.TESTE: "#F59E0B", S.ANALISE: C["purple"], S.ANDAMENTO: C["blue"],
              S.PENDENTE: C["gray"], S.BLOQUEADA: C["red"]}

CSS = """
:root{--bg:#060B1C;--panel:#0B1226;--border:#1B2547;--text:#E6EAF5;--muted:#8A94B4;--primary:#4F46E5}
.stApp{background:radial-gradient(1100px 480px at 75% -10%,#151D48 0%,var(--bg) 62%);color:var(--text)}
header[data-testid="stHeader"]{background:transparent} #MainMenu,footer{visibility:hidden}
.block-container{padding:1rem 2rem 2rem;max-width:1600px}
h1,h2,h3,h4{color:var(--text)!important;font-weight:700!important}
h4{font-size:1.02rem!important;margin-bottom:.4rem!important}
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--panel);border:1px solid var(--border)!important;border-radius:14px}
section[data-testid="stSidebar"]{background:#080D20;border-right:1px solid var(--border)}
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:.2rem}
section[data-testid="stSidebar"] div[role="radiogroup"] label{padding:.6rem .9rem;border-radius:10px;width:100%;cursor:pointer;color:var(--muted)}
section[data-testid="stSidebar"] div[role="radiogroup"] label>div:first-child{display:none}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#111A38;color:var(--text)}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:var(--primary);color:#fff}
.stButton>button{background:#111A38;border:1px solid var(--border);color:var(--text);border-radius:10px}
.stButton>button:hover{border-color:var(--primary);color:#fff}
.mf-top{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:.2rem 0 1rem;margin-bottom:1rem;border-bottom:1px solid var(--border)}
.mf-brand{display:flex;align-items:center;gap:14px}.mf-brand img{height:56px}
.mf-brand h1{font-size:1.9rem;margin:0;padding:0}
.mf-brand p{margin:0 0 0 14px;padding-left:18px;border-left:1px solid var(--border);color:var(--muted);font-size:.85rem}
.mf-right{display:flex;gap:26px;align-items:center}
.mf-conn{display:flex;flex-direction:column;font-size:.78rem;color:var(--muted);line-height:1.35}.mf-conn b{color:var(--text);font-size:.85rem}
.mf-hero{padding:8px 6px}.mf-hero h2{font-size:1.8rem;margin:0 0 6px}.mf-hero p{color:var(--muted);margin:0}
.mf-how{background:linear-gradient(135deg,#1B2470,#2C2FA3);border:1px solid #3B43C7;border-radius:12px;padding:18px 22px;color:#DCE1FF;font-size:.85rem}
.mf-how b{display:block;color:#fff;font-size:1rem;margin-bottom:4px}
.mf-kpi{display:flex;gap:16px;align-items:center;background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px}
.mf-ic{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:700}
.mf-k-t{color:var(--muted);font-size:.85rem}.mf-k-v{font-size:2rem;font-weight:800;line-height:1.1}.mf-k-s{color:var(--muted);font-size:.75rem}
.mf-badge,.mf-chip{display:inline-block;padding:2px 10px;border-radius:8px;font-size:.72rem;font-weight:600;white-space:nowrap}
.mf-chip{background:#141C3A;border:1px solid var(--border);color:#9DB2FF;font-family:monospace}
.mf-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);font-size:.82rem}
.mf-row .t{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mf-row .m{color:var(--muted);font-size:.74rem;white-space:nowrap}
.mf-bl{display:flex;justify-content:space-between;font-size:.82rem;margin-top:12px}
.mf-bar{height:8px;border-radius:9px;background:#141C3A;margin-top:5px}.mf-bar>span{display:block;height:100%;border-radius:9px}
.mf-muted{color:var(--muted);font-size:.82rem}.mf-link{display:block;padding:8px 0;color:#9DB2FF!important;text-decoration:none;font-size:.85rem}
"""

HERO_LEFT = ('<div class="mf-hero"><h2>🚀 Olá, time! 👋</h2><p>Aqui você acompanha o progresso da sua sprint, relacionando '
             'as issues do Jira com os commits do GitHub — nas branches e na main.</p></div>')
HERO_RIGHT = ('<div class="mf-how"><b>💡 Como funciona?</b>O dashboard coleta as informações do Jira e do GitHub, mostrando como '
              'cada tarefa evolui, quem realizou os commits, em quais branches eles estão e o que ainda precisa ser concluído.</div>')


def logo_b64(nome="logo_header.png"):
    p = ASSETS / nome
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def apply_theme():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def rgba(hex_, a):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def style_fig(fig, altura=300):
    fig.update_layout(height=altura, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=C["muted"]), margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    fig.update_xaxes(gridcolor=C["border"], zeroline=False)
    fig.update_yaxes(gridcolor=C["border"], zeroline=False)
    return fig


def badge(status):
    cor = STATUS_COR.get(status, C["gray"])
    return Safe(f'<span class="mf-badge" style="color:{cor};background:{rgba(cor, .14)};border:1px solid {rgba(cor, .5)}">{esc(status)}</span>')


def chip(texto):
    return Safe(f'<span class="mf-chip">{esc(texto)}</span>')


def kpi(titulo, valor, sub, cor, icone):
    return Safe(f'<div class="mf-kpi"><div class="mf-ic" style="background:{rgba(cor, .2)};color:{cor}">{esc(icone)}</div>'
                f'<div><div class="mf-k-t">{esc(titulo)}</div><div class="mf-k-v">{esc(valor)}</div><div class="mf-k-s">{esc(sub)}</div></div></div>')


def bar(label, n, total, cor):
    p = (n / total * 100) if total else 0
    return Safe(f'<div class="mf-bl"><span>{esc(label)}</span><b>{p:.0f}%</b></div>'
                f'<div class="mf-bar"><span style="width:{p}%;background:{cor}"></span></div>')


def row(*celulas):
    """Linha de lista. Cada célula é (conteúdo, classe): 't' ocupa o espaço livre, 'm' é texto secundário.
    Texto comum é ESCAPADO; só `Safe` (chip/badge/...) entra como HTML."""
    return Safe('<div class="mf-row">' + "".join(f'<span class="{c}">{esc(h)}</span>' for h, c in celulas) + "</div>")


def ago(ts):
    if ts is None or pd.isna(ts):
        return ""
    ts = timeutil.parse_ts(ts) if not isinstance(ts, pd.Timestamp) else ts
    if pd.isna(ts):
        return ""
    ts = ts.tz_localize(timeutil.TZ) if ts.tzinfo is None else ts
    seg = max((timeutil.now() - ts).total_seconds(), 0)
    if seg < 3600: return f"{int(seg // 60)}min atrás"
    if seg < 86400: return f"{int(seg // 3600)}h atrás"
    return f"{int(seg // 86400)}d atrás"


_ESTADO = {"ok": ("Conectado", "green"), "partial": ("Parcial", "purple"), "stale": ("Dados antigos", "purple"),
           "error": ("Falha", "red")}


def header(atualizado, jira_state, gh_state):
    """`*_state`: 'ok' | 'partial' | 'stale' | 'error' (SourceView.state)."""
    def conn(nome, estado, icone):
        txt, cor = _ESTADO[estado]
        return (f'<div class="mf-conn"><b>{icone} {esc(nome)}</b>'
                f'<span style="color:{C[cor]}">● {txt}</span></div>')
    st.markdown(
        f'<div class="mf-top"><div class="mf-brand"><img src="data:image/png;base64,{logo_b64()}"/><h1>Vulpes Work</h1>'
        f'<p>Conectando Jira e GitHub<br>para um time mais produtivo.</p></div>'
        f'<div class="mf-right"><div class="mf-conn"><span style="color:{C["green"]}">● Última atualização</span>'
        f'<b>{esc(atualizado)}</b></div>{conn("Jira", jira_state, "◆")}{conn("GitHub", gh_state, "⌥")}</div></div>',
        unsafe_allow_html=True)


def sidebar_footer():
    return (f'<div style="margin-top:2.5rem"><img src="data:image/png;base64,{logo_b64()}" style="height:70px"/>'
            f'<p class="mf-muted" style="font-size:.95rem;margin-top:.6rem">Grandes resultados<br>nascem de boas<br>conexões.</p>'
            f'<b style="color:#8B9BFF">Vulpes Work</b></div>')
