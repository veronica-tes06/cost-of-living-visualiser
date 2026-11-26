import streamlit as st
import app_data
from app_base import setup_page, header, card, footer

setup_page()
S = app_data.load_scenario()   # builds the sidebar and calculates every country
header("Pushed code preview", "Sidebar and calculations from app_data.py — no charts yet")
with card():
    st.dataframe(S.t.round(0), width="stretch", height=600)
footer()