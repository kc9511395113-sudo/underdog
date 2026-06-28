import streamlit as st

from st_data import get_hk_data
from st_ui import (
    render_criteria,
    render_disclaimer,
    render_near_misses,
    render_results_table,
    render_shortlist,
    render_stats,
)

st.title("🇭🇰 Hong Kong Value Screener")
st.caption(
    "Data: StockAnalysis (HKEX) · Hang Seng ~11× fwd P/E · "
    "Refreshed Fridays 7:00 AM US Eastern"
)

render_criteria()
st.markdown(
    "_Near misses: large caps (>HK$50B) with Fwd P/E < 12, P/B < 1.0, Div > 5%_"
)

col_a, col_b = st.columns([1, 3])
with col_a:
    refresh = st.button("↻ Refresh data", type="primary", use_container_width=True)
with col_b:
    screener = st.session_state.get("hk_screener", {})
    url = (screener.get("screener") or {}).get("list_url", "")
    if url:
        st.markdown(f"[HKEX list on StockAnalysis ↗]({url})")

if refresh:
    with st.spinner("Scanning HK stocks (~3–5 minutes)…"):
        data = get_hk_data(force_refresh=True)
    st.session_state["hk_data"] = data
    st.success("HK data refreshed.")
elif "hk_data" not in st.session_state:
    with st.spinner("Loading HK screener…"):
        st.session_state["hk_data"] = get_hk_data()

data = st.session_state["hk_data"]
st.session_state["hk_screener"] = data

render_stats(data, benchmark_label="Hang Seng Fwd P/E")

st.subheader("Friday shortlist")
render_shortlist(data, link_col="stats_url")

st.subheader("All passing stocks")
render_results_table(data, link_col="stats_url")

render_near_misses(data, link_col="stats_url")
render_disclaimer("StockAnalysis (HKEX)")