"""Commit 1 · Básico — constantes, tema visual, CSS responsive y utilidades de interfaz.

No depende de los datos: se puede importar y probar por separado.
El punto de entrada de la app es mini_app.py (commit 3).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ================================================================== diseño
CATS = ["Rent", "Food", "Transport", "Household bills", "Leisure"]
GROUP_MAP = {"Suministros": "Household bills", "Transporte": "Transport",
             "Comida (súper)": "Food", "Comer fuera": "Leisure", "Ocio": "Leisure"}
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # validada, orden fijo
CAT_COLORS = dict(zip(CATS, PALETTE))
S1, S2 = PALETTE[0], PALETTE[1]
POS, NEG, MID = "#2a78d6", "#e34948", "#f0efec"        # divergente azul <-> rojo
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SEQ = ["#f0efec", "#cde2fb", "#6da7ec", "#2a78d6", "#104281"]
HOURS_PER_MONTH = 173
LIFESTYLE = {"Basic": 0.75, "Standard": 1.0, "Comfortable": 1.4}
INCOMES = ["Minimum wage (gross)", "Average net salary", "My own salary"]
RENTS = ["Outside city centre", "City centre"]
REGIONS = {
    "Western": ["Austria", "Belgium", "France", "Germany", "Ireland", "Netherlands",
                "Switzerland", "United Kingdom"],
    "Northern & Baltic": ["Denmark", "Finland", "Iceland", "Norway", "Sweden",
                          "Estonia", "Latvia", "Lithuania"],
    "Southern": ["Croatia", "Greece", "Italy", "Malta", "Portugal", "Slovenia", "Spain", "Turkey"],
    "Central & Eastern": ["Bulgaria", "Czech Republic", "Hungary", "Poland", "Romania",
                          "Russia", "Slovakia"],
    "Western Balkans": ["Albania", "Bosnia and Herzegovina", "Kosovo", "Montenegro",
                        "North Macedonia", "Serbia"],
}
REGION_OF = {c: r for r, cs in REGIONS.items() for c in cs}
REGION_COLORS = dict(zip(REGIONS, PALETTE))
CFG = {"displaylogo": False, "modeBarButtons": [["toImage"]],
       "toImageButtonOptions": {"format": "png", "scale": 2}}
SHORT_NAMES = {"Bosnia and Herzegovina": "Bosnia & Herz.", "North Macedonia": "N. Macedonia",
               "United Kingdom": "UK", "Czech Republic": "Czechia", "Netherlands": "Netherlands"}

# Plantilla común de Plotly (se registra una vez por proceso)
pio.templates["col"] = go.layout.Template(layout=dict(
    font=dict(family="Source Sans Pro, Segoe UI, sans-serif", color="#3d3c39", size=13),
    colorway=PALETTE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=13)),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, automargin=True),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, automargin=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None),
    margin=dict(l=8, r=8, t=30, b=8), barcornerradius=3,
    dragmode=False,   # sin zoom por arrastre: en pantallas táctiles el dedo hace scroll
))
pio.templates.default = "plotly_white+col"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --bg: #f5f5f2; --card: #ffffff; --line: #e8e7e1; --ink: #0b0b0b; --ink2: #52514e; --muted: #898781;
  --brand: #2a78d6; --good: #006300; --bad: #c0302f; --radius: 16px;
  --shadow: 0 1px 2px rgba(16,24,40,.04), 0 2px 10px rgba(16,24,40,.05);
  --shadow-hover: 0 2px 4px rgba(16,24,40,.05), 0 10px 28px rgba(16,24,40,.09);
}
.stApp {background: var(--bg);}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .kpi, .hero {
  font-family: 'Inter', 'Source Sans Pro', system-ui, -apple-system, 'Segoe UI', sans-serif;}
.block-container {max-width: 1480px;
  padding: calc(3.75rem + clamp(.4rem, 1.4vw, 1.3rem)) clamp(.85rem, 3vw, 2.6rem) 3rem;}
.stAppDeployButton, footer {display: none;}
header[data-testid="stHeader"] {background: rgba(245,245,242,.86); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);}
[data-testid="stTopNavLink"] {border-radius: 999px !important;}
[data-testid="stSidebar"] {background: #ffffff; border-right: 1px solid var(--line);}
[data-testid="stSidebar"] h3 {font-size: 1.02rem; font-weight: 700; letter-spacing: -.01em;}

/* ---------- tarjetas ---------- */
[class*="st-key-card"] {background: var(--card); border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important; box-shadow: var(--shadow);
  padding: clamp(12px, 1.6vw, 22px) !important; transition: box-shadow .2s ease;}
[class*="st-key-card"]:hover {box-shadow: var(--shadow-hover);}
[class*="st-key-card"] h4 {font-size: clamp(.98rem, 1.1vw, 1.12rem) !important; font-weight: 650;
  color: #1f1e1c; padding: 0 0 .3rem; letter-spacing: -.005em;}
.stApp h2 {font-size: clamp(1.35rem, 2.1vw, 1.85rem) !important; font-weight: 750;
  letter-spacing: -.02em; padding-bottom: .2rem;}
.section-sub {color: var(--ink2); margin: -6px 0 16px; font-size: clamp(.88rem, 1vw, .98rem);}

/* ---------- cabecera ---------- */
.hero {position: relative; overflow: hidden; color: #fff; border-radius: 20px;
  background: radial-gradient(900px 260px at 100% 0%, rgba(255,255,255,.15), transparent 60%),
              linear-gradient(120deg, #0b2f5e 0%, #174f99 52%, #2a78d6 100%);
  padding: clamp(18px, 3vw, 34px) clamp(18px, 3.2vw, 40px) clamp(14px, 2.4vw, 26px);
  margin-bottom: clamp(12px, 1.6vw, 20px); box-shadow: 0 10px 30px rgba(13,54,107,.18);}
.hero::after {content: ""; position: absolute; right: -70px; top: -70px; width: 260px; height: 260px;
  border-radius: 50%; background: rgba(255,255,255,.07);}
.hero::before {content: ""; position: absolute; right: 140px; bottom: -110px; width: 200px; height: 200px;
  border-radius: 50%; background: rgba(255,255,255,.05);}
.hero .eyebrow {text-transform: uppercase; letter-spacing: .14em; font-size: .7rem; font-weight: 600;
  color: #a9c8f2; margin-bottom: 6px; position: relative;}
.hero h1 {color: #fff; font-size: clamp(1.35rem, 3vw, 2.35rem); font-weight: 800; letter-spacing: -.025em;
  margin: 0 0 6px; padding: 0; position: relative; line-height: 1.15;}
.hero p {color: #dbe8fa; margin: 0 0 14px; font-size: clamp(.88rem, 1.2vw, 1.05rem); max-width: 64ch;
  position: relative;}
.chip {display: inline-block; position: relative; background: rgba(255,255,255,.13);
  border: 1px solid rgba(255,255,255,.24); color: #fff; border-radius: 999px;
  padding: 3px 12px; margin: 0 6px 6px 0; font-size: clamp(.72rem, .9vw, .84rem); font-weight: 500;}

/* ---------- KPIs ---------- */
.kpi {background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: clamp(12px, 1.4vw, 18px) clamp(14px, 1.6vw, 20px) clamp(10px, 1.2vw, 16px);
  box-shadow: var(--shadow); height: 100%; position: relative; overflow: hidden;}
.kpi::before {content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--accent, #2a78d6);}
.kpi.good {--accent: #1baf7a;} .kpi.bad {--accent: #e34948;} .kpi.info {--accent: #2a78d6;}
.kpi-label {color: var(--muted); font-size: .7rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .06em; margin-bottom: 6px;}
.kpi-value {color: var(--ink); font-size: clamp(1.2rem, 2.1vw, 1.85rem); font-weight: 750;
  letter-spacing: -.02em; line-height: 1.12; overflow-wrap: anywhere;}
.kpi-sub {font-size: clamp(.74rem, .85vw, .84rem); margin-top: 6px; color: var(--ink2);}
.kpi-sub.good {color: var(--good);} .kpi-sub.bad {color: var(--bad);}

.insight {background: linear-gradient(90deg, #eef5fe, #f8fbff); border: 1px solid #d9e7fb;
  border-left: 4px solid var(--brand); padding: 9px 14px; border-radius: 10px; color: #2c2b29;
  font-size: clamp(.84rem, .95vw, .94rem); margin: 2px 0 12px; line-height: 1.45;}
.foot {color: var(--muted); font-size: .78rem; margin-top: 30px; border-top: 1px solid var(--line);
  padding-top: 12px;}

/* ---------- responsive ---------- */
[class*="st-key-grid"] [data-testid="stHorizontalBlock"],
[class*="st-key-kpis"] [data-testid="stHorizontalBlock"] {flex-wrap: wrap; row-gap: 1rem;}
[class*="st-key-grid"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  min-width: min(100%, 440px);}
[class*="st-key-kpis"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
  min-width: min(100%, 210px);}
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {max-width: 100%;}
[data-testid="stButtonGroup"] [data-rac] {flex-wrap: wrap; row-gap: 6px;}

/* barra lateral: ancho suficiente para que etiquetas y botones no se corten */
@media (min-width: 900px) {
  section[data-testid="stSidebar"][data-collapsed="false"] {min-width: 320px !important;
    max-width: 380px !important;}
}
[data-testid="stSidebar"] [data-baseweb="tag"] {max-width: none !important;}
[data-testid="stSidebar"] [data-baseweb="tag"] span {max-width: none !important; overflow: visible !important;
  text-overflow: clip !important;}
[data-testid="stSidebar"] button p {white-space: nowrap;}

@media (min-width: 1700px) {          /* monitores grandes */
  .block-container {max-width: 1720px;}
}
@media (min-width: 2400px) {          /* 4K o zoom del navegador reducido */
  .block-container {max-width: 92vw;}
}
@media (max-width: 1100px) {          /* portátil pequeño / tablet horizontal */
  [class*="st-key-grid"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: min(100%, 380px);}
}
@media (max-width: 900px) {           /* tablet vertical: KPIs 2×2 */
  [class*="st-key-kpis"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: calc(50% - .5rem) !important; flex: 1 1 calc(50% - .5rem) !important;}
}
@media (max-width: 640px) {           /* móvil */
  .hero {border-radius: 14px;}
  .hero::before {display: none;}
  .hero .eyebrow {font-size: .64rem;}
  [class*="st-key-card"] {border-radius: 12px !important;}
  .kpi {border-radius: 12px;}
  .kpi-label {font-size: .62rem;}
  [class*="st-key-kpis"] [data-testid="stHorizontalBlock"] {row-gap: .6rem;}
}
@media (max-width: 330px) {           /* móviles muy estrechos */
  [class*="st-key-kpis"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 100% !important;}
}
</style>
"""


# ================================================================== página y dispositivo
def setup_page():
    """Configura la página, el CSS y detecta el dispositivo. Se llama al inicio de CADA ejecución
    (Streamlit vuelve a ejecutar el script principal, pero los módulos importados no)."""
    # El servidor no conoce el ancho de pantalla; se usa el User-Agent para un "modo compacto".
    ua = st.context.headers.get("User-Agent", "") if st.context.headers else ""
    mobile = "Mobi" in ua or "iPhone" in ua
    st.session_state["_mobile"] = mobile
    st.session_state["_tablet"] = not mobile and ("iPad" in ua or "Android" in ua or "Tablet" in ua)
    st.session_state["_ids"] = 0          # contador de keys de contenedores, por sesión
    st.set_page_config(page_title="Cost of Living Visualizer", page_icon="💶", layout="wide",
                       initial_sidebar_state="auto")
    st.markdown(CSS, unsafe_allow_html=True)


def is_mobile():
    return st.session_state.get("_mobile", False)


def is_tablet():
    return st.session_state.get("_tablet", False)


def next_id():
    st.session_state["_ids"] = st.session_state.get("_ids", 0) + 1
    return st.session_state["_ids"]


# ================================================================== utilidades de interfaz
def eur(v, sign=False):
    if pd.isna(v):
        return "n/a"
    s = "−" if v < 0 else ("+" if sign else "")
    return f"{s}€{abs(v):,.0f}"


def grid(spec):
    """Fila de columnas que se apila en pantallas estrechas (ver CSS st-key-grid)."""
    return st.container(key=f"grid_{next_id()}").columns(spec)


def card(parent=None):
    """Tarjeta con borde y estilo propio (CSS st-key-card)."""
    return (parent or st).container(border=True, key=f"card_{next_id()}")


def kpi_row(n):
    """Fila de KPIs: 4 en escritorio, 2 en tablet/móvil, 1 en pantallas muy estrechas."""
    return st.container(key=f"kpis_{next_id()}").columns(n)


def kpi(col, label, value, sub="", tone=""):
    col.markdown(f"<div class='kpi {tone or 'info'}'><div class='kpi-label'>{label}</div>"
                 f"<div class='kpi-value'>{value}</div><div class='kpi-sub {tone}'>{sub}</div></div>",
                 unsafe_allow_html=True)


def insight(text):
    st.markdown(f"<div class='insight'>💡 {text}</div>", unsafe_allow_html=True)


def header(title, sub):
    st.markdown(f"## {title}")
    st.markdown(f"<div class='section-sub'>{sub}</div>", unsafe_allow_html=True)


def hero_block(title, subtitle, chips, eyebrow="Cost of Living Visualizer · Europe"):
    st.markdown(f"<div class='hero'><div class='eyebrow'>{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p>"
                + "".join(f"<span class='chip'>{c}</span>" for c in chips) + "</div>",
                unsafe_allow_html=True)


def footer():
    st.markdown("<div class='foot'>Data: Numbeo crowd-sourced prices (europe_allyouneed.csv), "
                "national averages in €, single snapshot. Minimum wage is gross. "
                "Basket: one person, see <i>Data &amp; method</i>. TUS · Data Visualisation · "
                "Cost of Living Visualizer.</div>", unsafe_allow_html=True)


def need_data(df):
    if df.empty:
        st.info("No countries match this scenario — add regions in the sidebar, or choose another "
                "income option (the minimum wage is missing for some countries).", icon="🔎")
        return False
    return True


def show_filter(key):
    default = "Top 10" if is_mobile() else "All"   # en móvil, menos barras de inicio
    v = st.segmented_control("Show", ["All", "Top 10", "Bottom 10"], default=default, key=key,
                             label_visibility="collapsed")
    return v or default


def limit(d, col, mode):
    if mode == "Top 10":
        return d.nlargest(10, col)
    if mode == "Bottom 10":
        return d.nsmallest(10, col)
    return d


def bar_h(n):
    return max(240, (21 if is_mobile() else 23 if is_tablet() else 26) * n + 70)


def pad(values, k=0.2):
    lo, hi = min(values.min(), 0), max(values.max(), 0)
    span = (hi - lo) or 1
    return [lo - span * k if lo < 0 else 0, hi + span * k]


def no_titles(fig):
    """px pone el nombre de la columna como título de eje y de leyenda: aquí no hace falta."""
    fig.update_layout(legend_title_text=None)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return fig


def pca_order(df):
    """Orden por la 1ª componente principal: perfiles parecidos quedan juntos (Topic 1-2 / 4)."""
    z = (df - df.mean()) / df.std(ddof=0).replace(0, 1)
    if len(z) < 2:
        return list(df.index)
    _, _, vt = np.linalg.svd(z.values, full_matrices=False)
    return list(z.index[np.argsort(z.values @ vt[0])])
