"""Data — CSV loading, session state with a shareable URL, the scenario
sidebar and cost-of-living calculations by country.

"""
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from app_base import CATS, HOURS_PER_MONTH, INCOMES, LIFESTYLE, REGION_OF, REGIONS, RENTS
from costs import (
    BASKET_CATEGORIES,
    BASKET_COLUMNS,
    BASKET_GROUP,
    BASKET_ITEM,
    BASKET_QUANTITY,
    DEFAULT_BASKET,
    HOUSEHOLD_BILLS,
    LEISURE,
    MIN_WAGE,
    NET_SALARY,
    RENT,
    RENT_IN,
    RENT_OUT,
    load_prices,
)

PRICES = Path(__file__).parent / "data" / "europe_allyouneed.csv"

DEFAULTS = {"income": INCOMES[0], "salary": 2000, "rent": RENTS[0], "sharers": 1,
            "lifestyle": "Standard", "regions": list(REGIONS), "highlight": ["Ireland", "Spain"],
            "focus": True}
# Streamlit clears widget state when switching pages, so keep a separate copy.
KEEP = [*DEFAULTS, "country", "ca", "cb"]


@st.cache_data
def get_prices():
    """Load prices in long and wide country-by-item formats once."""
    return load_prices(PRICES)


def all_countries():
    return sorted(get_prices()[1].index)


# ================================================================== State and URL
def init_state():
    ss = st.session_state
    ALL = all_countries()
    if "init" not in ss:  # On first load, URL parameters override the defaults.
        qp = st.query_params
        for k, v in DEFAULTS.items():
            ss[k] = list(v) if isinstance(v, list) else v
        try:
            if qp.get("income") in INCOMES: ss.income = qp["income"]
            if qp.get("rent") in RENTS: ss.rent = qp["rent"]
            if qp.get("lifestyle") in LIFESTYLE: ss.lifestyle = qp["lifestyle"]
            if "salary" in qp: ss.salary = int(min(15000, max(300, int(qp["salary"]))))
            if "sharers" in qp: ss.sharers = int(min(4, max(1, int(qp["sharers"]))))
            if "regions" in qp: ss.regions = [r for r in qp["regions"].split(",") if r in REGIONS]
            if "hl" in qp: ss.highlight = [c for c in qp["hl"].split(",") if c in ALL]
        except ValueError:
            pass
        ss.country, ss.ca, ss.cb = "Ireland", "Ireland", "Spain"
        ss.selv = 0
        ss.init = True
    store = ss.setdefault("_store", {})
    for k in KEEP:
        if k in ss:
            store[k] = ss[k]
        elif k in store:
            ss[k] = store[k]


def reset():
    for k, v in DEFAULTS.items():
        st.session_state[k] = list(v) if isinstance(v, list) else v
    st.query_params.clear()


def scenario_params():
    ss = st.session_state
    return {"income": ss.income, "rent": ss.rent or RENTS[0], "lifestyle": ss.lifestyle,
            "salary": str(ss.salary), "sharers": str(ss.sharers),
            "regions": ",".join(ss.regions), "hl": ",".join(ss.highlight)}


def toggle_highlight(name):
    hl = list(st.session_state.highlight)
    hl.remove(name) if name in hl else hl.append(name)
    st.session_state.highlight = hl


def point_country(p):
    """Get the country name from a selected Plotly point."""
    ALL = all_countries()
    for cand in (p.get("location"), p.get("customdata"), p.get("y"), p.get("x")):
        if isinstance(cand, (list, tuple)) and cand:
            cand = cand[0]
        if isinstance(cand, str) and cand in ALL:
            return cand
    return None


def on_pick(key, mode="toggle"):
    """Toggle a country's highlight or open its profile from the map."""
    ss = st.session_state
    ev = ss.get(key)
    pts = (ev or {}).get("selection", {}).get("points", [])
    name = point_country(pts[0]) if pts else None
    if name:
        if mode == "profile":
            ss.country, ss.goto = name, True
        else:
            toggle_highlight(name)
    ss.selv += 1  # A new key redraws the chart and clears the selection.


# ================================================================== Sidebar
def sidebar():
    ss = st.session_state
    with st.sidebar:
        st.markdown("### ⚙️ Your scenario")
        st.radio("Income", INCOMES, key="income",
                 help="Minimum wage is the statutory gross monthly wage (missing where there is none). "
                      "Average net salary is after tax.")
        st.number_input("My monthly net salary (€)", 300, 15000, step=50, key="salary",
                        disabled=ss.income != "My own salary")
        st.segmented_control("Rent (1-bed apartment)", RENTS, key="rent",
                             selection_mode="single")
        st.slider("People sharing rent & bills", 1, 4, key="sharers",
                  help="Divides rent and household bills, e.g. students sharing a flat.")
        st.select_slider("Lifestyle (food & leisure)", list(LIFESTYLE), key="lifestyle",
                         help="Scales grocery, eating-out and leisure quantities: "
                              + ", ".join(f"{k} ×{v}" for k, v in LIFESTYLE.items()))
        st.divider()
        st.multiselect("Regions", list(REGIONS), key="regions")
        st.multiselect("Highlight countries", all_countries(), key="highlight",
                       help="Tip: click any bar or point in a chart to add/remove it here.")
        st.toggle("Focus mode: dim the other countries", key="focus",
                  help="Cross-highlighting (Topic 3): keeps every country visible but fades those "
                       "you have not highlighted, so attention goes to your selection.")
        c1, c2 = st.columns(2)
        c1.button("↺ Reset", on_click=reset, width="stretch")
        c2.link_button("🔗 Share", "?" + urlencode(scenario_params()), width="stretch",
                       help="Opens this exact scenario as a link you can copy and send.")


# ================================================================== Calculations
def compute(rent_item, sharers, lifestyle, income_mode, custom_income):
    """Return one row per country with monthly costs by category, total cost, income and metrics."""
    wide = get_prices()[1]
    basket = pd.DataFrame(DEFAULT_BASKET, columns=BASKET_COLUMNS)
    basket["category"] = basket[BASKET_GROUP].map(BASKET_CATEGORIES)
    basket.loc[basket["category"].isin(["Food", LEISURE]), BASKET_QUANTITY] *= LIFESTYLE[lifestyle]
    t = pd.DataFrame({RENT: wide[rent_item] / sharers})
    for cat, g in basket.groupby("category"):
        t[cat] = (wide[g[BASKET_ITEM]] * g[BASKET_QUANTITY].values).sum(axis=1)
    t[HOUSEHOLD_BILLS] /= sharers
    t = t[CATS].copy()
    t["Total cost"] = t[CATS].sum(axis=1)
    t["Minimum wage"] = wide[MIN_WAGE]
    t["Average net salary"] = wide[NET_SALARY]
    t["Income"] = {INCOMES[0]: t["Minimum wage"], INCOMES[1]: t["Average net salary"],
                   INCOMES[2]: pd.Series(float(custom_income), index=t.index)}[income_mode]
    t["Remaining"] = t["Income"] - t["Total cost"]
    t["Cost % of income"] = t["Total cost"] / t["Income"] * 100
    t["Rent % of income"] = t[RENT] / t["Income"] * 100
    t["Rent hours (min wage)"] = t[RENT] / (t["Minimum wage"] / HOURS_PER_MONTH)
    t["Region"] = t.index.map(REGION_OF)
    return t


def scenario_chips(n_countries):
    """Return labels that summarise the scenario in the header."""
    ss = st.session_state
    rent = ss.rent or RENTS[0]
    chips = [ss.income, f"Rent: {rent.lower()}",
             f"{ss.sharers} sharing" if ss.sharers > 1 else "Living alone",
             f"{ss.lifestyle} lifestyle", f"{n_countries} countries"]
    if ss.income == "My own salary":
        chips[0] = f"My salary: €{ss.salary:,}"
    return chips


def load_scenario():
    """Set up state and the sidebar, then calculate costs. Called by mini_app.py on each run."""
    init_state()
    sidebar()
    ss = st.session_state
    long_prices, wide = get_prices()
    rent_choice = ss.rent or RENTS[0]       # The segmented control can have no selection.
    st.query_params.update(scenario_params())
    full = compute(RENT_OUT if rent_choice == RENTS[0] else RENT_IN, ss.sharers, ss.lifestyle,
                   ss.income, ss.salary)
    t = full[full["Region"].isin(ss.regions)]
    return SimpleNamespace(long_prices=long_prices, wide=wide, ALL=all_countries(), full=full, t=t,
                           ti=t.dropna(subset=["Income"]), HL=set(ss.highlight), rent_choice=rent_choice)
