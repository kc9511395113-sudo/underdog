"""
Value Screener — Streamlit entry point (US + Hong Kong).

Run locally:
    streamlit run streamlit_app.py

Deploy: Streamlit Community Cloud — see README Streamlit section.
"""
import streamlit as st

st.set_page_config(
    page_title="Value Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Value Screener")
st.markdown(
    """
    Deep-value stock screens for **US** and **Hong Kong** markets.

    | Filter | Threshold |
    |--------|-----------|
    | Forward P/E | < 8 |
    | P/B | < 0.8 |
    | Dividend yield | > 5% |

    Use the sidebar pages:

    - **US Value Screener** — Finviz data, Friday shortlist
    - **HK Value Screener** — HKEX via StockAnalysis, Friday shortlist

    Shortlists refresh automatically on **Fridays at 7:00 AM US Eastern**
    (or click **Refresh data** on each page).
    """
)

col1, col2 = st.columns(2)
with col1:
    st.info("🇺🇸 **United States** — S&P 500 fwd P/E ~22× vs your screen at <8×")
    if st.button("Open US Screener", use_container_width=True):
        st.switch_page("pages/1_US_Value_Screener.py")
with col2:
    st.info("🇭🇰 **Hong Kong** — Hang Seng fwd P/E ~11× vs your screen at <8×")
    if st.button("Open HK Screener", use_container_width=True):
        st.switch_page("pages/2_HK_Value_Screener.py")

st.divider()
st.caption("Not investment advice. For education and research only.")