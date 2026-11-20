# a file that claude generated to preview the app's theme and components

import streamlit as st
import plotly.graph_objects as go
from app_base import *

setup_page()
hero_block("How far does a salary go in Europe?", "Preview of the app's theme and components",
           ["Average net salary", "Living alone", "37 countries"])

c = kpi_row(4)
kpi(c[0], "Income covers costs", "33 / 37", "89% of countries", "good")
kpi(c[1], "Median monthly cost", eur(1132), "range €510 – €2,537")
kpi(c[2], "Most money left", "Switzerland", eur(4017, True) + " / month", "good")
kpi(c[3], "Least money left", "Kosovo", eur(27, True) + " / month", "bad")

insight("This is what an insight box looks like.")
left, right = grid(2)
with card(left):
    st.markdown("#### A card with a chart")
    st.plotly_chart(go.Figure(go.Bar(x=CATS, y=[900, 250, 60, 200, 180],
                                     marker_color=[CAT_COLORS[c] for c in CATS])), theme=None)
with card(right):
    st.markdown("#### Colour palette")
    for name, colour in CAT_COLORS.items():
        st.markdown(f"<span style='color:{colour}'>■</span> {name} `{colour}`", unsafe_allow_html=True)
footer()