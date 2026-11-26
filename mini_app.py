"""Cost of Living Visualizer — interactive app entry point.

Run from any folder:
    python mini_app.py            (from the repository folder)

The app is split into three modules, one per commit:
  1. app_base.py — theme, responsive CSS, Plotly template and interface helpers
  2. app_data.py — CSV loading, session state and URL, sidebar and scenario calculations
  3. mini_app.py — Plotly Express charts, pages and navigation

Click a country on the map to open its profile. Click a bar or point to highlight the
country across all charts. The app saves the scenario in a shareable URL.
"""
import subprocess
import sys
from functools import partial
from pathlib import Path

HERE = Path(__file__).parent

# Running this file directly launches Streamlit from this folder so it reads .streamlit/config.toml.
# Extra arguments such as --server.port 8502 are passed to Streamlit.
if __name__ == "__main__":
    from streamlit import runtime
    if not runtime.exists():
        sys.exit(subprocess.call(
            [sys.executable, "-m", "streamlit", "run", *sys.argv[1:], str(Path(__file__).resolve())],
            cwd=HERE))

sys.path.insert(0, str(HERE))   # Make app_base, app_data and costs importable from any folder.

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import app_base
import app_data
from app_base import *          # noqa: F401,F403  Design constants and interface helpers
from app_data import on_pick, toggle_highlight
from costs import (
    BASKET_CATEGORIES,
    BASKET_COLUMNS,
    BASKET_GROUP,
    BASKET_ITEM,
    BASKET_QUANTITY,
    DEFAULT_BASKET,
    RENT_IN,
    RENT_OUT,
)

# ================================================================== Commits 1 and 2: page setup and data
app_base.setup_page()
MOBILE, TABLET = app_base.is_mobile(), app_base.is_tablet()
_S = app_data.load_scenario()
long_prices, wide, ALL = _S.long_prices, _S.wide, _S.ALL
full, t, ti, HL, rent_choice = _S.full, _S.t, _S.ti, _S.HL, _S.rent_choice
ss = st.session_state


# ================================================================== Chart helpers
def hero(title, subtitle, eyebrow="Cost of Living Visualizer · Europe"):
    hero_block(title, subtitle, app_data.scenario_chips(len(t)), eyebrow)


def chart(fig, key=None, pick=None, config=None):
    """Show a chart. Set pick to 'toggle' or 'profile' to make countries clickable."""
    # Use a white background to match the card. A transparent chart picks up Streamlit's grey theme.
    fig.update_layout(font_family="Inter, Source Sans Pro, Segoe UI, sans-serif",
                      paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
    if MOBILE:   # Use smaller text and shorter fixed-height charts on mobile.
        fig.update_layout(font_size=11, legend_font_size=11, hoverlabel_font_size=12)
        h = fig.layout.height
        if h and h <= 460:
            fig.update_layout(height=max(240, int(h * 0.85)))
    elif TABLET:
        fig.update_layout(font_size=12)
    if pick:
        k = f"{key}_{ss.selv}"
        st.plotly_chart(fig, width="stretch", config=config or CFG, theme=None, key=k,
                        on_select=partial(on_pick, k, pick), selection_mode="points")
    else:
        st.plotly_chart(fig, width="stretch", config=config or CFG, theme=None, key=key)


def label(c):
    """Abbreviate country labels on mobile and bold highlighted countries."""
    name = SHORT_NAMES.get(c, c) if MOBILE else c
    return f"<b>{name}</b>" if c in HL else name


def ticks(fig, index):
    fig.update_yaxes(tickvals=list(index), ticktext=[label(c) for c in index])


def outline(index):
    """Add a dark outline to bars for highlighted countries."""
    return dict(width=[2 if c in HL else 0 for c in index], color=INK)


def fade(index, low=0.35):
    """Dim marks for other countries in focus mode."""
    index = list(index)
    if not ss.get("focus", True) or not (HL & set(index)):
        return 1
    return [1 if c in HL else low for c in index]


def px_hbar(d, x, colors, text=None, hover=None, custom=()):
    """Draw horizontal bars with per-country colour, outline and opacity using px.bar."""
    df = d.reset_index()
    df = df.rename(columns={df.columns[0]: "_key"})
    fig = px.bar(df, x=x, y="_key", orientation="h", text=text, custom_data=["_key", *custom])
    fig.update_traces(marker_color=colors, marker_line=outline(df["_key"]),
                      marker_opacity=fade(df["_key"]), textposition="outside", cliponaxis=False,
                      hovertemplate=hover)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return fig


# ================================================================== Pages
def page_overview():
    hero("How far does a salary go in Europe?",
         "Can a salary cover the essentials across Europe? Pick your scenario "
         + ("in the » menu" if MOBILE else "in the sidebar (»)") + " — every chart updates instantly.")
    if not need_data(ti):
        return
    c = kpi_row(4)
    covers = int((ti["Remaining"] >= 0).sum())
    kpi(c[0], "Income covers living costs", f"{covers} / {len(ti)}",
        f"{covers / len(ti):.0%} of countries", "good" if covers / len(ti) >= .5 else "bad")
    kpi(c[1], "Median monthly cost", eur(t["Total cost"].median()),
        f"range {eur(t['Total cost'].min())} – {eur(t['Total cost'].max())}")
    best, worst = ti["Remaining"].idxmax(), ti["Remaining"].idxmin()
    kpi(c[2], "Most money left", best, eur(ti.at[best, "Remaining"], True) + " / month", "good")
    kpi(c[3], "Least money left", worst, eur(ti.at[worst, "Remaining"], True) + " / month",
        "bad" if ti.at[worst, "Remaining"] < 0 else "")
    st.write("")

    left, right = grid([3, 2])   # Show the map and rankings side by side on wide screens.
    with card(left):
        st.markdown("#### Affordability map")
        m1, m2 = st.columns([3, 2])
        metric = m1.segmented_control(
            "Map metric", ["Money left", "Cost % of income", "Rent % of income", "Monthly cost"],
            default="Money left", key="map_metric", label_visibility="collapsed") or "Money left"
        labels_mode = m2.segmented_control(
            "Labels", ["Highlighted", "All", "None"], default="All" if not MOBILE else "Highlighted",
            key="map_labels", label_visibility="collapsed",
            help="Write the value on top of each country: only the ones you highlighted, all, or none.") \
            or "Highlighted"
        col, mid, lower_good, fmt = {
            "Money left": ("Remaining", 0, False, "€"),
            "Cost % of income": ("Cost % of income", 100, True, "%"),
            "Rent % of income": ("Rent % of income", 40, True, "%"),
            "Monthly cost": ("Total cost", None, True, "€")}[metric]
        d = (t if col == "Total cost" else ti).reset_index()
        d["rank"] = d[col].rank(ascending=lower_good, method="min").astype(int)
        show = (lambda v: eur(v, mid == 0)) if fmt == "€" else (lambda v: f"{v:.0f}%")
        d["value"] = d[col].map(show)
        if mid is None:
            scale, rng = SEQ, (d[col].min(), d[col].max())
        else:
            lim = (d[col] - mid).abs().max()
            scale = [(0, NEG), (.5, MID), (1, POS)] if not lower_good else [(0, POS), (.5, MID), (1, NEG)]
            rng = (mid - lim, mid + lim)

        fig = px.choropleth(d, locations="country", locationmode="country names", color=col,
                            range_color=rng, color_continuous_scale=scale,
                            custom_data=["country", "value", "rank", "Total cost", "Income", "Remaining"])
        # Use thin white borders and emphasise highlighted countries with thicker, dark borders.
        fig.update_traces(
            marker_line_color=[INK if c in HL else "white" for c in d["country"]],
            marker_line_width=[2.2 if c in HL else 0.7 for c in d["country"]],
            hovertemplate="<b>%{customdata[0]}</b><br>" + metric + ": <b>%{customdata[1]}</b> "
                          "(#%{customdata[2]} of " + str(len(d)) + ")"
                          "<br>Monthly cost €%{customdata[3]:,.0f} · income €%{customdata[4]:,.0f}"
                          "<br><i>Click to open the country profile</i><extra></extra>")

        # Use px.scatter_geo in text mode to label country centroids with their values.
        lab = {"All": d, "Highlighted": d[d["country"].isin(HL)], "None": d.iloc[0:0]}[labels_mode]
        if len(lab):
            txt = px.scatter_geo(lab, locations="country", locationmode="country names", text="value",
                                 custom_data=["country", "value", "rank", "Total cost", "Income", "Remaining"])
            txt.update_traces(mode="text", textfont=dict(size=10 if labels_mode == "All" else 12,
                                                         color=INK, family="Inter, sans-serif"),
                              hovertemplate=fig.data[0].hovertemplate)
            fig.add_traces(txt.data)

        # Use a conformal conic projection and fixed bounds for Europe.
        # Automatic bounds would show the whole globe because Russia crosses the 180° meridian.
        fig.update_geos(projection_type="conic conformal", projection_parallels=[43, 62],
                        projection_rotation=dict(lon=15), lataxis_range=[34, 71.5],
                        lonaxis_range=[-25, 45], visible=False,
                        showland=True, landcolor="#ecebe6", showcountries=True, countrycolor="#ffffff",
                        countrywidth=0.6, showocean=True, oceancolor="#eef4fb", showlakes=False,
                        showcoastlines=False, showframe=False, bgcolor="rgba(0,0,0,0)")
        cb_ticks = dict(tickprefix="€" if fmt == "€" else "", ticksuffix="%" if fmt == "%" else "")
        fig.update_layout(
            height=330 if MOBILE else 520 if TABLET else 600, margin=dict(l=0, r=0, t=0, b=0),
            dragmode=False if MOBILE else "pan",
            coloraxis_colorbar=dict(orientation="h", x=0.5, xanchor="center", y=-0.01, yanchor="top",
                                    len=0.9 if MOBILE else 0.6, thickness=10, title=dict(
                                        text=metric, side="top", font=dict(size=12)),
                                    outlinewidth=0, **cb_ticks))
        chart(fig, "map", pick="profile", config={**CFG, "modeBarButtons": [["zoomInGeo", "zoomOutGeo", "resetGeo", "toImage"]]})
        lead = {"Money left": "Blue = money left over each month, red = a monthly deficit.",
                "Cost % of income": "Blue = costs take less than 100% of income, red = more.",
                "Rent % of income": "Red = above the 40% housing-cost overburden threshold.",
                "Monthly cost": "Darker = more expensive to live in."}[metric]
        tip = "Tap" if MOBILE else "Drag to move, use + / − to zoom, and click"
        st.caption(f"{lead} {tip} a country to open its profile. Dark outline = highlighted countries. "
                   "Light grey = no data for this option (Kosovo is not in the base map).")


    for title, data, good in (("🏆 Most money left", ti.nlargest(5, "Remaining"), True),
                              ("⚠️ Least money left", ti.nsmallest(5, "Remaining"), False)):
        with card(right):
            st.markdown(f"#### {title}")
            dd = data.iloc[::-1]  # Put the first result at the top.
            fig = px_hbar(dd, "Remaining", colors=[POS if v >= 0 else NEG for v in dd["Remaining"]],
                          text=[eur(v, True) for v in dd["Remaining"]],
                          hover="%{y}: %{x:,.0f} € left<extra></extra>")
            fig.update_xaxes(range=pad(ti["Remaining"]), tickprefix="€")
            fig.update_layout(height=250, margin=dict(t=8))
            ticks(fig, dd.index)
            chart(fig, f"top_{good}", pick="toggle")
    footer()


def page_affordability():
    header("Affordability", "Does the selected income cover the monthly cost of living?")
    if not need_data(ti):
        return
    deficit = ti[ti["Remaining"] < 0]
    if len(deficit):
        w = deficit["Remaining"].idxmin()
        insight(f"In <b>{len(deficit)} of {len(ti)}</b> countries the {ss.income.lower()} does not cover "
                f"the basket. The largest gap is <b>{w}</b> ({eur(deficit.at[w, 'Remaining'], True)} a month).")
    else:
        insight(f"The {ss.income.lower()} covers the basket in <b>all {len(ti)}</b> countries. "
                f"Median left over: <b>{eur(ti['Remaining'].median())}</b>.")
    mode = show_filter("aff_show")
    c1, c2 = grid(2)
    with card(c1):
        st.markdown("#### Income vs monthly cost")
        d = limit(ti, "Income", mode).sort_values("Income")
        long = (d.reset_index()
                .melt(id_vars="country", value_vars=["Total cost", "Income"], var_name="Series", value_name="€")
                .replace({"Series": {"Total cost": "Monthly cost"}}))
        # Grouped bars: income next to monthly cost for each country.
        fig = px.bar(long, x="€", y="country", color="Series", orientation="h", barmode="group",
                     color_discrete_map={"Monthly cost": S2, "Income": S1}, custom_data=["country"],
                     category_orders={"Series": ["Monthly cost", "Income"]})
        fig.update_traces(marker_opacity=fade(d.index),
                          hovertemplate="%{y}: %{fullData.name} €%{x:,.0f}<extra></extra>")
        fig.update_layout(bargap=.28, bargroupgap=.06, height=bar_h(len(d) * 1.4),
                          legend_traceorder="reversed")
        no_titles(fig)
        fig.update_xaxes(tickprefix="€")
        ticks(fig, d.index)
        chart(fig, "aff_group", pick="toggle")
    with card(c2):
        st.markdown("#### Money left after costs")
        d = limit(ti, "Remaining", mode).sort_values("Remaining")
        fig = px_hbar(d, "Remaining", colors=[POS if v >= 0 else NEG for v in d["Remaining"]],
                      text=[eur(v, True) for v in d["Remaining"]], custom=("Income", "Total cost"),
                      hover="<b>%{y}</b><br>Left €%{x:,.0f}<br>Income €%{customdata[1]:,.0f} − "
                            "cost €%{customdata[2]:,.0f}<extra></extra>")
        fig.add_vline(x=0, line_color=INK2, line_width=1)
        fig.update_xaxes(tickprefix="€", range=pad(d["Remaining"]))
        fig.update_layout(height=bar_h(len(d) * 1.4), showlegend=False)
        ticks(fig, d.index)
        chart(fig, "aff_left", pick="toggle")
    if ss.income == INCOMES[0]:
        st.caption("ℹ️ The minimum wage is gross — after tax the real amount left is lower. "
                   "Click a bar to highlight that country everywhere.")
    footer()


def page_salary():
    header("Salary explorer", "How much do you need to earn — and how far does a salary go?")
    if not need_data(t):
        return
    with card():
        st.markdown("#### Which countries become affordable as the net salary rises?")
        d = t.sort_values("Total cost")
        steps = list(range(600, 4201, 200))
        lo, hi = steps[0] - d["Total cost"].max(), steps[-1] - d["Total cost"].min()

        def title(sal):
            n = int((sal - d["Total cost"] >= 0).sum())
            if MOBILE:   # Shorten labels on narrow screens.
                return f"€{sal:,} → covers {n} of {len(d)}"
            return f"Net salary €{sal:,} → covers costs in {n} of {len(d)} countries"

        # Use px.bar with animation_frame to show one frame per salary.
        long = pd.DataFrame([{"country": c, "Salary": sal, "Left": sal - v}
                             for sal in steps for c, v in d["Total cost"].items()])
        lim = max(abs(lo), abs(hi))
        fig = px.bar(long, x="Left", y="country", orientation="h", animation_frame="Salary",
                     color="Left", range_color=(-lim, lim), range_x=[lo * 1.05, hi * 1.05],
                     # Use red below zero and blue at zero or above in every frame.
                     color_continuous_scale=[(0, NEG), (0.4999, NEG), (0.5, POS), (1, POS)],
                     custom_data=["country"])
        hover = "%{y}: %{x:,.0f} € left<extra></extra>"
        start = min(steps, key=lambda sal: abs(sal - 1400))
        idx = steps.index(start)
        fig.update_traces(marker_line=outline(d.index), marker_opacity=fade(d.index), hovertemplate=hover)
        for fr, sal in zip(fig.frames, steps):
            fr.data[0].hovertemplate = hover
            fr.layout.title = dict(text=title(sal), x=0.01)
        fig.data[0].x = fig.frames[idx].data[0].x               # Start the animation at about €1,400.
        fig.data[0].marker.color = fig.frames[idx].data[0].marker.color
        # Place the controls above the chart, with Play and Pause to the left of the salary slider.
        anim = {"frame": {"duration": 600, "redraw": True}, "mode": "immediate", "fromcurrent": True,
                "transition": {"duration": 300, "easing": "cubic-in-out"}}
        stop = {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}
        fig.layout.updatemenus = [dict(
            type="buttons", direction="left", showactive=False, x=0, xanchor="left", y=1.0,
            yanchor="bottom", pad=dict(t=0, b=8, r=8), font=dict(size=13),
            bgcolor="#ffffff", bordercolor=GRID,
            buttons=[dict(label="▶ Play", method="animate", args=[None, anim]),
                     dict(label="❚❚ Pause", method="animate", args=[[None], stop])])]
        slider = fig.layout.sliders[0]
        slider.update(active=idx, x=0 if MOBILE else 0.2, len=1 if MOBILE else 0.8,
                      y=1.0 if not MOBILE else 1.0, yanchor="bottom",
                      pad=dict(t=0, b=MOBILE and 44 or 6, l=0, r=0),
                      currentvalue=dict(visible=False), transition=dict(duration=0),
                      font=dict(size=11), tickcolor=MUTED, bordercolor=GRID, bgcolor="#f3f2ee")
        for stp in slider.steps:
            stp.label = f"{int(stp.label) / 1000:.1f}k" if MOBILE else f"€{int(stp.label):,}"
            stp.args[1].update(stop)
        fig.add_vline(x=0, line_color=INK2, line_width=1)
        fig.update_layout(
            title=dict(text=title(start), x=0.01, xref="container", y=1, yref="container", yanchor="top",
                       pad=dict(t=6), font=dict(size=15)),
            coloraxis_showscale=False, height=bar_h(len(d)) + 150,
            margin=dict(t=150 if MOBILE else 110, b=10),
            # Keep square corners to avoid oversized arcs during Plotly frame transitions.
            barcornerradius=0)
        fig.update_xaxes(tickprefix="€", title="Money left per month")
        fig.update_yaxes(title=None)
        ticks(fig, d.index)
        chart(fig, "anim")
        st.caption("Press ▶ Play above the chart or drag the salary slider. Countries are sorted by "
                   "monthly cost (cheapest at the bottom); red = the salary does not cover the basket.")

    with card():
        st.markdown("#### Are countries with higher minimum wages also more expensive?")
        a1, a2, a3 = st.columns(3)
        xcol = a1.selectbox("X axis", ["Total cost", "Rent", "Food", "Household bills"], key="sc_x")
        ycol = a2.selectbox("Y axis", ["Minimum wage", "Average net salary"], key="sc_y",
                            help="Minimum wage is the main income measure; "
                                 "average net salary is kept for comparison.")
        trend = a3.selectbox("Summary line", ["Linear fit", "None"], key="sc_trend")
        d = t.dropna(subset=[xcol, ycol]).reset_index()
        if len(d) < 3:
            st.info("Not enough countries with data for this pair of variables.")
            footer()
            return
        pear = d[xcol].corr(d[ycol])
        spear = d[xcol].corr(d[ycol], method="spearman")
        insight(f"Pearson r = <b>{pear:.2f}</b> (linear) · Spearman ρ = <b>{spear:.2f}</b> (monotonic, "
                f"rank-based) across {len(d)} countries. Association is not causation.")
        topv = max(d[xcol].max(), d[ycol].max()) * 1.05
        d["label"] = [c if c in HL else "" for c in d["country"]]
        fig = px.scatter(d, x=xcol, y=ycol, color="Region", text="label", custom_data=["country"],
                         color_discrete_map=REGION_COLORS,
                         category_orders={"Region": [r for r in REGIONS if r in set(d["Region"])]})
        for tr in fig.data:                       # Set marker size and opacity by country for highlighting and focus mode.
            names = [cd[0] for cd in tr.customdata]
            tr.marker.size = [16 if c in HL else 11 for c in names]
            tr.marker.opacity = fade(names)
        fig.update_traces(textposition="top center", textfont=dict(color=INK, size=12),
                          marker_line=dict(color="white", width=2),
                          hovertemplate="<b>%{customdata[0]}</b><br>" + xcol + " €%{x:,.0f}<br>" + ycol +
                                        " €%{y:,.0f}<extra></extra>")
        if xcol == "Total cost":
            fig.add_scatter(x=[0, topv], y=[0, topv], mode="lines", name="Salary = cost",
                            line=dict(color=MUTED, dash="dash", width=1), hoverinfo="skip")
        if trend == "Linear fit":
            slope, icpt = np.polyfit(d[xcol], d[ycol], 1)
            xs = np.array([d[xcol].min(), d[xcol].max()])
            fig.add_scatter(x=xs, y=slope * xs + icpt, mode="lines", name="Linear fit",
                            line=dict(color=INK2, width=1.5), hoverinfo="skip")
        fig.update_layout(legend_title_text=None)
        fig.update_xaxes(title=f"{xcol} (€ / month)", tickprefix="€", range=[0, d[xcol].max() * 1.1])
        fig.update_yaxes(title=f"{ycol} (€ / month)", tickprefix="€", range=[0, d[ycol].max() * 1.1])
        fig.update_layout(height=460 if MOBILE else 580, legend=dict(y=1.02))
        chart(fig, "scatter", pick="toggle")
        st.caption("Points above the dashed line earn more than the basket costs. "
                   "Click a point to highlight it.")
    footer()


def page_costs():
    header("Living costs", "What makes one country more expensive than another?")
    if not need_data(t):
        return
    share = t[CATS].div(t["Total cost"], axis=0) * 100
    top_rent = share["Rent"].idxmax()
    n_rent = int((share.idxmax(axis=1) == "Rent").sum())
    insight(f"Rent is the biggest expense in <b>{n_rent} of {len(share)}</b> countries, taking from "
            f"<b>{share['Rent'].min():.0f}%</b> to <b>{share['Rent'].max():.0f}%</b> of the monthly cost "
            f"(highest in {top_rent}).")
    c1, c2 = grid([3, 2])
    with card(c1):
        h1, h2 = st.columns([3, 2])
        h1.markdown("#### Monthly cost by category")
        unit = h2.segmented_control("Unit", ["€ / month", "% of total"], default="€ / month",
                                    key="cost_unit", label_visibility="collapsed") or "€ / month"
        d = t.sort_values("Total cost")
        long = d.reset_index().melt(id_vars="country", value_vars=CATS, var_name="Category", value_name="€")
        fig = px.bar(long, x="€", y="country", color="Category", orientation="h", barmode="stack",
                     color_discrete_map=CAT_COLORS, category_orders={"Category": CATS},
                     custom_data=["country"])
        fig.update_traces(marker_line=dict(color="white", width=1),
                          hovertemplate="%{y} · %{fullData.name}" + (": %{x:.0f}%" if unit != "€ / month"
                                                                     else ": €%{x:,.0f}") + "<extra></extra>")
        fig.update_layout(bargap=.22, height=bar_h(len(d)),
                          barnorm="percent" if unit == "% of total" else None)
        no_titles(fig)
        fig.update_xaxes(tickprefix="" if unit == "% of total" else "€",
                         ticksuffix="%" if unit == "% of total" else "")
        ticks(fig, d.index)
        chart(fig, "stack", pick="toggle")
    with card(c2):
        h1, h2 = st.columns([3, 2])
        h1.markdown("#### Share of the budget")
        how = h2.selectbox("Order rows by", ["Rent share", "Total cost", "Region", "A–Z", "Similarity"],
                           key="heat_order", label_visibility="collapsed",
                           help="Reordering rows changes which patterns become visible. "
                                "'Similarity' places countries with a similar budget profile together.")
        order = {"Rent share": list(share["Rent"].sort_values(ascending=False).index),
                 "Total cost": list(t["Total cost"].sort_values(ascending=False).index),
                 "Region": list(t.assign(_r=share["Rent"]).sort_values(["Region", "_r"],
                                                                        ascending=[True, False]).index),
                 "A–Z": sorted(share.index),
                 "Similarity": pca_order(share)}[how]
        sh = share.loc[order]
        fig = px.imshow(sh, color_continuous_scale=SEQ, aspect="auto", text_auto=".0f",
                        labels=dict(color="%", x="", y=""))
        fig.update_traces(hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>", xgap=2, ygap=2)
        fig.update_xaxes(side="top")
        fig.update_layout(height=bar_h(len(sh)), coloraxis_colorbar=dict(ticksuffix="%", thickness=10))
        fig.update_yaxes(tickvals=list(sh.index),
                         ticktext=[label(c) for c in sh.index])
        chart(fig, "heat")
        st.caption("Malta's transport share is 0%: public transport is free for residents.")

    with card():
        st.markdown("#### Housing cost overburden: rent as % of income")
        if need_data(ti):
            d = ti.sort_values("Rent % of income")
            over = int((d["Rent % of income"] > 40).sum())
            insight(f"<b>{over} of {len(d)}</b> countries are above the 40% housing-cost overburden threshold.")
            fig = px_hbar(d, "Rent % of income",
                          colors=[NEG if v > 40 else POS for v in d["Rent % of income"]],
                          text=[f"{v:.0f}%" for v in d["Rent % of income"]],
                          hover="%{y}: %{x:.1f}% of income<extra></extra>")
            fig.add_vline(x=40, line_dash="dash", line_color=INK2, annotation_text="40% threshold",
                          annotation_position="top right", annotation_font_color=INK2)
            fig.update_xaxes(ticksuffix="%", range=pad(d["Rent % of income"]))
            fig.update_layout(height=bar_h(len(d)), margin=dict(t=30))
            ticks(fig, d.index)
            chart(fig, "rent_pct", pick="toggle")

    with card():
        st.markdown("#### City centre vs outside: 1-bed rent")
        r = pd.DataFrame({"Outside": wide.loc[t.index, RENT_OUT],
                          "Centre": wide.loc[t.index, RENT_IN]}).sort_values("Centre")
        premium = (r["Centre"] / r["Outside"] - 1) * 100
        insight(f"Living in the city centre costs a median <b>{premium.median():.0f}%</b> more, "
                f"from {premium.min():.0f}% to {premium.max():.0f}% ({premium.idxmax()}).")
        # Dumbbell chart: one line per country joining outside-centre and city-centre rent.
        lx, ly = [], []
        for c in r.index:
            lx += [r.at[c, "Outside"], r.at[c, "Centre"], None]
            ly += [c, c, None]
        fig = go.Figure()
        fig.add_scatter(x=lx, y=ly, mode="lines", line=dict(color=GRID, width=3),
                        hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=r["Outside"], y=list(r.index), mode="markers", name="Outside city centre",
                        marker=dict(color=SEQ[2], size=10, opacity=fade(r.index)),
                        hovertemplate="%{y}: €%{x:,.0f} outside the centre<extra></extra>")
        fig.add_scatter(x=r["Centre"], y=list(r.index), mode="markers", name="City centre",
                        marker=dict(color=SEQ[4], size=10, opacity=fade(r.index)), customdata=premium.values,
                        hovertemplate="%{y}: €%{x:,.0f} in the centre (+%{customdata:.0f}%)<extra></extra>")
        fig.update_layout(height=bar_h(len(r)), legend=dict(orientation="h", y=1.0, yanchor="bottom"))
        no_titles(fig)
        fig.update_xaxes(tickprefix="€", rangemode="tozero")
        ticks(fig, r.index)
        chart(fig, "rent_centre")
        st.caption("Answers the group's question of how to show rent when it depends on location. "
                   "The sidebar's rent option switches every other chart between the two.")
    footer()


def page_distribution():
    header("Distributions", "What does the whole population of countries look like?")
    if not need_data(t):
        return
    metrics = {"Monthly cost": ("Total cost", t, "€"), "Money left": ("Remaining", ti, "€"),
               "Rent": ("Rent", t, "€"), "Rent % of income": ("Rent % of income", ti, "%")}
    metric = st.segmented_control("Variable", list(metrics), default="Monthly cost", key="dist_metric",
                                  label_visibility="collapsed") or "Monthly cost"
    col, src, unit = metrics[metric]
    d = src.dropna(subset=[col])
    if not need_data(d):
        return
    fmt = (lambda v: eur(v)) if unit == "€" else (lambda v: f"{v:.0f}%")
    mean, med, skew = d[col].mean(), d[col].median(), d[col].skew()
    shape = ("right-skewed: a few high values pull the mean above the median" if skew > 0.5 else
             "left-skewed: a few low values pull the mean below the median" if skew < -0.5 else
             "roughly symmetric")
    insight(f"Median <b>{fmt(med)}</b>, mean <b>{fmt(mean)}</b>, spread (SD) {fmt(d[col].std())} "
            f"across {len(d)} countries. The distribution is <b>{shape}</b>.")
    pre, suf = ("€", "") if unit == "€" else ("", "%")

    c1, c2 = grid(2)
    with card(c1):
        h1, h2 = st.columns([3, 2])
        h1.markdown("#### Histogram")
        bins = h2.slider("Bins", 3, 20, 8, key="dist_bins",
                         help="Bin width is part of the model: too few bins merge structure, "
                              "too many turn noise into features.")
        fig = px.histogram(d.reset_index(), x=col, nbins=bins, color_discrete_sequence=[S1])
        fig.update_traces(marker_line=dict(color="white", width=1),
                          hovertemplate=f"{pre}%{{x}}{suf}: %{{y}} countries<extra></extra>")
        # Stagger the label heights to avoid overlaps.
        fig.add_vline(x=med, line_dash="dash", line_color=INK2)
        fig.add_annotation(x=med, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                           text=f"median {fmt(med)}", font=dict(color=INK2, size=11))
        for i, c in enumerate([c for c in ss.highlight if c in d.index][:4]):
            fig.add_vline(x=d.at[c, col], line_color=S2, line_width=2)
            fig.add_annotation(x=d.at[c, col], y=0.94 - 0.08 * i, yref="paper", showarrow=False,
                               xanchor="left", xshift=4, text=f"<b>{c}</b>",
                               font=dict(color=INK, size=11), bgcolor="rgba(255,255,255,.85)")
        fig.update_xaxes(tickprefix=pre, ticksuffix=suf, title=metric)
        fig.update_yaxes(title="Countries")
        fig.update_layout(height=400, bargap=0.02, showlegend=False, margin=dict(t=34))
        chart(fig, "hist")
    with card(c2):
        st.markdown("#### By region (box plot)")
        # Show every country as a point on the box plot.
        common = dict(x="Region", y=col, color="Region", color_discrete_map=REGION_COLORS,
                      custom_data=["country"],
                      category_orders={"Region": [r for r in REGIONS if r in set(d["Region"])]})
        fig = px.box(d.reset_index(), points="all", **common)
        fig.update_traces(jitter=0.4, pointpos=0, fillcolor="rgba(0,0,0,0)", line_width=1.5)
        fig.update_traces(marker_size=7,
                          hovertemplate="%{customdata[0]}: " + pre + "%{y:,.0f}" + suf + "<extra></extra>")
        fig.update_xaxes(title=None)
        fig.update_yaxes(tickprefix=pre, ticksuffix=suf, title=metric)
        fig.update_xaxes(tickangle=-20 if MOBILE else 0)
        fig.update_layout(height=400, showlegend=False, margin=dict(t=10))
        chart(fig, "dist_groups", pick="toggle")
        st.caption("Each dot is a country — click one to highlight it everywhere.")

    footer()


def page_profile():
    st.selectbox("Country", ALL, key="country")
    name = ss.country
    row = full.loc[name]
    hero(f"{name}", "Living costs for your scenario", eyebrow=f"Country profile · {REGION_OF.get(name, '')}")
    c = kpi_row(4)
    med = full["Total cost"].median()
    diff = (row["Total cost"] / med - 1) * 100
    kpi(c[0], "Monthly cost", eur(row["Total cost"]), f"{diff:+.0f}% vs European median",
        "bad" if diff > 0 else "good")
    kpi(c[1], f"Income ({ss.income.split(' (')[0].lower()})", eur(row["Income"]),
        "minimum wage is gross" if ss.income == INCOMES[0] else "")
    kpi(c[2], "Money left each month", eur(row["Remaining"], True),
        f"{row['Cost % of income']:.0f}% of income spent" if pd.notna(row["Income"]) else "no income data",
        "good" if row["Remaining"] >= 0 else "bad")
    rank = full["Remaining"].rank(ascending=False)
    kpi(c[3], "Affordability rank",
        f"#{rank[name]:.0f}" if pd.notna(row["Remaining"]) else "n/a",
        f"of {int(full['Remaining'].notna().sum())} countries (1 = most money left)")
    st.write("")

    c1, c2 = grid([2, 3])
    with card(c1):
        st.markdown("#### Where the money goes")
        # Donut chart: the five parts add up to the monthly cost.
        fig = px.pie(names=CATS, values=row[CATS].values, color=CATS, hole=.62,
                     color_discrete_map=CAT_COLORS)
        fig.update_traces(sort=False, direction="clockwise", textinfo="percent",
                          textfont=dict(color="white"), marker_line=dict(color="white", width=2),
                          hovertemplate="%{label}: €%{value:,.0f} (%{percent})<extra></extra>")
        fig.add_annotation(text=f"<b style='font-size:20px'>{eur(row['Total cost'])}</b><br>per month",
                           showarrow=False)
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                          legend=dict(orientation="v", x=1.0, y=0.5, yanchor="middle"))
        chart(fig, "donut")
    with card(c2):
        st.markdown("#### Everyday prices vs the European median")
        items = {"1-bed rent (outside)": RENT_OUT, "1-bed rent (centre)": RENT_IN,
                 "Utilities (85 m²)": DEFAULT_BASKET[0][0], "Internet": DEFAULT_BASKET[1][0],
                 "Transport pass": "Monthly Public Transport Pass (Regular Price)",
                 "Cheap restaurant meal": "Meal at an Inexpensive Restaurant",
                 "Cappuccino": "Cappuccino (Regular Size)", "Milk 1 L": "Milk (Regular, 1 Liter)",
                 "Bread 500 g": "Fresh White Bread (500 g Loaf)", "Chicken 1 kg": "Chicken Fillets (1 kg)",
                 "Gym membership": "Monthly Fitness Club Membership",
                 "Cinema ticket": "Cinema Ticket (International Release)"}
        diffs = pd.Series({k: (wide.at[name, v] / wide[v].median() - 1) * 100
                           for k, v in items.items()}).sort_values()
        fig = px.bar(x=diffs.values, y=diffs.index, orientation="h",
                     text=[f"{v:+.0f}%" for v in diffs.values])
        fig.update_traces(marker_color=[NEG if v > 0 else POS for v in diffs.values],
                          textposition="outside", cliponaxis=False,
                          customdata=[[wide.at[name, items[k]], wide[items[k]].median()] for k in diffs.index],
                          hovertemplate="%{y}: €%{customdata[0]:,.2f} vs median €%{customdata[1]:,.2f}"
                                        "<extra></extra>")
        no_titles(fig)
        fig.add_vline(x=0, line_color=INK2, line_width=1)
        fig.update_xaxes(ticksuffix="%", range=pad(diffs))
        fig.update_layout(height=380, showlegend=False)
        chart(fig, "items")
        st.caption("Red = more expensive than the European median, blue = cheaper.")
    with card():
        st.markdown("#### Countries with a similar cost of living")
        sim = (full["Total cost"] - row["Total cost"]).abs().drop(name).nsmallest(6).index
        pk = f"sim_{name}"
        st.pills("Open a similar country", list(sim), key=pk, label_visibility="collapsed",
                 on_change=lambda: ss.update(country=ss[pk]) if ss.get(pk) else None)
        tbl = full.loc[[name, *sim], ["Total cost", "Rent", "Average net salary", "Remaining"]]
        st.dataframe(tbl, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="€%.0f") for k in tbl.columns})
        b1, b2 = st.columns(2)
        b1.button(f"⭐ {'Remove' if name in HL else 'Highlight'} {name}", width="stretch",
                  on_click=toggle_highlight, args=(name,))
        if b2.button("⚖️ Compare with…", width="stretch"):
            ss.ca = name
            st.switch_page(PAGES["compare"])
    footer()


def page_compare():
    header("Compare two countries", "Side-by-side costs, prices and the salary you'd need")
    a1, a2, a3 = st.columns([2, 2, 1])
    a1.selectbox("Country A", ALL, key="ca")
    a2.selectbox("Country B", ALL, key="cb")
    a3.write("")
    a3.button("⇄ Swap", width="stretch",
              on_click=lambda: ss.update(ca=ss.cb, cb=ss.ca))
    ca, cb = ss.ca, ss.cb
    A, B = full.loc[ca], full.loc[cb]

    with card():
        sal = st.number_input(f"If I earn this net per month in {ca} (€)", 300, 20000,
                              int(round(A["Average net salary"], -1)), 50, key=f"cmp_sal_{ca}")
        factor = B["Total cost"] / A["Total cost"]
        c = kpi_row(3)
        kpi(c[0], f"Equivalent salary in {cb}", eur(sal * factor),
            f"{(factor - 1) * 100:+.0f}% cost of living vs {ca}", "bad" if factor > 1 else "good")
        kpi(c[1], f"Left over in {ca}", eur(sal - A["Total cost"], True), "same lifestyle",
            "good" if sal >= A["Total cost"] else "bad")
        kpi(c[2], f"Left over in {cb} (same salary)", eur(sal - B["Total cost"], True),
            f"average net salary there: {eur(B['Average net salary'])}",
            "good" if sal >= B["Total cost"] else "bad")

    c1, c2 = grid([2, 3])
    with card(c1):
        st.markdown("#### Monthly basket")
        cols = CATS + ["Total cost"]
        long = pd.DataFrame({"Category": cols * 2, "Country": [ca] * len(cols) + [cb] * len(cols),
                             "€": list(A[cols]) + list(B[cols])})
        # Grouped bars: one pair of bars per category.
        fig = px.bar(long, x="Category", y="€", color="Country", barmode="group",
                     color_discrete_map={ca: S1, cb: S2})
        fig.update_traces(hovertemplate="%{fullData.name} · %{x}: €%{y:,.0f}<extra></extra>")
        fig.update_layout(bargap=.3, bargroupgap=.06, height=420)
        no_titles(fig)
        fig.update_yaxes(tickprefix="€")
        chart(fig, "cmp_cats")
    with card(c2):
        h1, h2 = st.columns([2, 2])
        h1.markdown("#### Item prices")
        cats = sorted(long_prices["category"].unique())
        cat = h2.selectbox("Category", cats, index=cats.index("groceries"), key="cmp_cat",
                           format_func=lambda s: s.replace("_", " ").capitalize(),
                           label_visibility="collapsed")
        items = long_prices[(long_prices["category"] == cat) & long_prices["country"].isin([ca, cb])]
        p = items.pivot(index="item", columns="country", values="price_eur")
        if ca == cb or p.shape[1] < 2:
            st.info("Choose two different countries to compare prices.")
        else:
            p = p[[ca, cb]].dropna()
            p["diff"] = (p[cb] / p[ca] - 1) * 100
            p = p.sort_values("diff")
            cheaper = int((p["diff"] < 0).sum())
            insight(f"<b>{cheaper} of {len(p)}</b> {cat.replace('_', ' ')} items are cheaper in {cb}. "
                    f"Median difference: <b>{p['diff'].median():+.0f}%</b>.")
            fig = px.bar(p.reset_index(), x="diff", y="item", orientation="h",
                         text=[f"{v:+.0f}%" for v in p["diff"]], custom_data=[ca, cb])
            fig.update_traces(marker_color=[NEG if v > 0 else POS for v in p["diff"]],
                              textposition="outside", cliponaxis=False,
                              hovertemplate="%{y}<br>" + ca + ": €%{customdata[0]:,.2f}<br>" + cb +
                                            ": €%{customdata[1]:,.2f}<br>Difference %{x:+.0f}%<extra></extra>")
            no_titles(fig)
            fig.add_vline(x=0, line_color=INK2, line_width=1)
            fig.update_xaxes(ticksuffix="%", range=pad(p["diff"]),
                             title=f"Price in {cb} vs {ca}")
            fig.update_layout(height=max(320, 30 * len(p) + 80), showlegend=False)
            chart(fig, "cmp_items")
            st.caption(f"Red = more expensive in {cb}, blue = cheaper. Hover for exact prices.")
    footer()


def page_data():
    header("Data & method", "The numbers behind every chart, and how they are calculated")
    with card():
        q = st.text_input("Search country", placeholder="e.g. Ireland", label_visibility="collapsed")
        table = t.drop(columns=["Rent hours (min wage)"]).sort_values("Remaining", ascending=False)
        if q:
            table = table[table.index.str.contains(q, case=False)]
        money = CATS + ["Total cost", "Minimum wage", "Average net salary", "Income", "Remaining"]
        cfg = {c: st.column_config.NumberColumn(format="€%.0f") for c in money}
        cfg |= {"Cost % of income": st.column_config.ProgressColumn(
                    format="%.0f%%", min_value=0, max_value=float(max(150, t["Cost % of income"].max()))),
                "Rent % of income": st.column_config.ProgressColumn(
                    format="%.0f%%", min_value=0, max_value=100)}
        st.dataframe(table, width="stretch", height=520, column_config=cfg)
        st.download_button("⬇ Download this scenario (CSV)", table.round(2).to_csv().encode("utf-8-sig"),
                           "cost_of_living_scenario.csv", "text/csv")
    c1, c2 = grid(2)
    with card(c1):
        st.markdown("#### Monthly basket (one person)")
        basket = pd.DataFrame(DEFAULT_BASKET, columns=BASKET_COLUMNS)
        basket["Category"] = basket[BASKET_GROUP].map(BASKET_CATEGORIES)
        basket_display = basket[["Category", BASKET_ITEM, BASKET_QUANTITY]].rename(
            columns={BASKET_ITEM: "Item", BASKET_QUANTITY: "Quantity / month"})
        st.dataframe(basket_display, hide_index=True, width="stretch", height=420)
    with card():
        st.markdown("#### Chart guide: which chart answers which question")
        guide = pd.DataFrame([
            ("Overview", "Choropleth map", "Where?", "See affordability across Europe at a glance"),
            ("Overview", "Top / bottom 5 bars", "Compare", "Quick summary of the best and worst countries"),
            ("Affordability", "Grouped bar", "Compare", "Can the income cover the monthly cost?"),
            ("Affordability", "Diverging bar", "Compare", "How much is left (or missing) each month"),
            ("Salary explorer", "Animated bar", "Compare across salaries",
             "Which countries become affordable as the salary rises"),
            ("Salary explorer", "Scatter + linear fit", "Relate",
             "Are countries with higher wages also more expensive?"),
            ("Living costs", "Stacked bar", "Compare / part-to-whole", "What makes up the monthly cost"),
            ("Living costs", "Heatmap", "Compare (2 keys)", "Which part of the budget is largest in each country"),
            ("Living costs", "Bar + 40% line", "Compare", "How much of the income goes on rent"),
            ("Living costs", "Dumbbell: centre vs outside rent", "Compare",
             "How much more the city centre costs"),
            ("Distributions", "Histogram", "Distribute", "Spread of values across countries"),
            ("Distributions", "Box plot by region", "Distribute", "Compare regions"),
            ("Country profile", "Donut / pie", "Part-to-whole", "Where one country's money goes"),
            ("Country profile", "Prices vs median bar", "Compare", "Which everyday items are cheap or expensive"),
            ("Compare", "Grouped bar · % difference bar", "Compare", "Choose between two countries"),
        ], columns=["Page", "Chart", "Question", "Why it is in"])
        st.dataframe(guide, hide_index=True, width="stretch")
        st.caption("Explored in the analysis notebook but not used here: treemap / sunburst and parallel "
                   "coordinates (hard for a general audience to read), the salary coverage line (line charts "
                   "are kept for change over time and the data is a single snapshot) and the Q-Q check (an "
                   "analysis check, not a chart for users). Similarity matrix, violin / strip / ECDF and "
                   "hours-to-pay-rent views were also left out to avoid overwhelming the user.")
    with card(c2):
        st.markdown("#### Method & limitations")
        st.markdown(f"""
- **Monthly cost** = rent of a 1-bed apartment + the basket on the left, priced with each
  country's Numbeo average. Rent and household bills are divided by the people sharing.
- **Lifestyle** scales food and leisure quantities (Basic ×0.75 · Standard ×1 · Comfortable ×1.4).
- **Money left** = income − monthly cost. **Rent %** uses Eurostat's 40% housing-cost
  overburden threshold as a reference.
- **Limitations:** prices are crowd-sourced and a single snapshot; the minimum wage is
  *gross* and missing in {int(full['Minimum wage'].isna().sum())} countries; utilities are for an
  85 m² flat, so they overstate a 1-bed; national averages hide big city–rural gaps.
""")
    footer()


# ================================================================== Navigation
PAGES = {
    "overview": st.Page(page_overview, title="Overview", icon=":material/public:", default=True),
    "afford": st.Page(page_affordability, title="Affordability", icon=":material/account_balance_wallet:",
                      url_path="affordability"),
    "salary": st.Page(page_salary, title="Salary explorer", icon=":material/trending_up:",
                      url_path="salary"),
    "costs": st.Page(page_costs, title="Living costs", icon=":material/shopping_cart:", url_path="costs"),
    "dist": st.Page(page_distribution, title="Distributions", icon=":material/bar_chart:",
                    url_path="distributions"),
    "profile": st.Page(page_profile, title="Country profile", icon=":material/flag:", url_path="country"),
    "compare": st.Page(page_compare, title="Compare", icon=":material/compare_arrows:", url_path="compare"),
    "data": st.Page(page_data, title="Data & method", icon=":material/table_chart:", url_path="data"),
}
nav = st.navigation(list(PAGES.values()), position="top")
if ss.pop("goto", False):          # A map click opens the country profile.
    st.switch_page(PAGES["profile"])
if not ss.regions:
    st.warning("Select at least one region in the sidebar.", icon="🗺️")
nav.run()
