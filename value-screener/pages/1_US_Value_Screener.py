import streamlit as st

from st_data import get_us_data
from st_ui import (
    render_criteria,
    render_disclaimer,
    render_near_misses,
    render_results_table,
    render_shortlist,
    render_stats,
)

st.title("🇺🇸 US Value Screener")
st.caption("Data: Finviz · Refreshed Fridays 7:00 AM US Eastern")

render_criteria()

col_a, col_b = st.columns([1, 3])
with col_a:
    refresh = st.button("↻ Refresh data", type="primary", use_container_width=True)
with col_b:
    screener = st.session_state.get("us_screener", {})
    url = (screener.get("screener") or {}).get("finviz_url", "")
    if url:
        st.markdown(f"[Open Finviz screener ↗]({url})")

if refresh:
    with st.spinner("Scraping Finviz (~2 minutes)…"):
        data = get_us_data(force_refresh=True)
    st.session_state["us_data"] = data
    st.success("US data refreshed.")
elif "us_data" not in st.session_state:
    with st.spinner("Loading US screener…"):
        st.session_state["us_data"] = get_us_data()

data = st.session_state["us_data"]
st.session_state["us_screener"] = data

render_stats(data, benchmark_label="S&P 500 Fwd P/E")

st.subheader("Friday shortlist")
render_shortlist(data, link_col="finviz_url")

st.subheader("All passing stocks")
render_results_table(data, link_col="finviz_url")

render_near_misses(data, link_col="finviz_url")
render_disclaimer("Finviz")