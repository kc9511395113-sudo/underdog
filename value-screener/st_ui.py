"""Shared Streamlit UI for US and HK screeners."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st


def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%a, %b %d %Y %H:%M %Z")
    except ValueError:
        return iso


def render_criteria():
    st.markdown(
        """
        **Custom screen (same logic for US & HK)**

        - **Forward P/E** < 8
        - **P/B** < 0.8
        - **Dividend yield** > 5%
        - Sorted by **lowest forward P/E**
        """
    )


def render_stats(data: dict, *, benchmark_label: str):
    sc = data.get("screener", {})
    counts = data.get("counts", {})
    meta = data.get("meta", {})

    c1, c2, c3, c4 = st.columns(4)
    bench_val = sc.get("sp500_forward_pe") or sc.get("hang_seng_forward_pe")
    c1.metric(benchmark_label, f"{bench_val}×" if bench_val else "—")
    c2.metric("Universe", counts.get("universe") or counts.get("scanned") or "—")
    c3.metric("Passing", counts.get("passing") or len(data.get("results", [])))
    c4.metric("Near misses", counts.get("near_misses") or len(data.get("near_misses", [])))

    st.caption(
        f"Last updated: **{fmt_dt(meta.get('last_updated'))}** · "
        f"Next scheduled refresh: **{fmt_dt(meta.get('next_refresh'))}** "
        f"(Fridays 7:00 AM US Eastern)"
    )


def render_shortlist(data: dict, *, link_col: str = "finviz_url"):
    shortlist = data.get("shortlist", {})
    for key in ("1", "2", "3"):
        tier = shortlist.get(key)
        if not tier:
            continue
        with st.expander(f"{tier['label']}: {tier['title']} ({len(tier['stocks'])} stocks)", expanded=(key == "1")):
            st.caption(tier["description"])
            if not tier["stocks"]:
                st.info("No stocks in this tier.")
                continue
            for s in tier["stocks"]:
                url = s.get(link_col) or s.get("stats_url") or s.get("quote_url") or "#"
                note = f" — _{s['note']}_" if s.get("note") else ""
                st.markdown(
                    f"**[{s['ticker']}]({url})** {s.get('company', '')}{note}  \n"
                    f"Fwd **{s['fpe_n']}×** · P/B **{s['pb_n']}** · Div **{s['div_n']}%** · "
                    f"Wk inflow **{s.get('week_flow', '—')}** · {s.get('mcap', '')}"
                )


def render_results_table(data: dict, *, link_col: str = "finviz_url"):
    rows = data.get("results", [])
    if not rows:
        st.warning("No stocks pass all three criteria right now.")
        return
    df = pd.DataFrame([
        {
            "Ticker": r["ticker"],
            "Company": r.get("company", ""),
            "Type": r.get("type", ""),
            "Tier": f"T{r.get('tier', '')}",
            "Fwd P/E": r["fpe_n"],
            "P/B": r["pb_n"],
            "Div %": r["div_n"],
            "Wk Net Inflow": r.get("week_flow", "—"),
            "Mkt Cap": r.get("mcap", ""),
            "Link": r.get(link_col) or r.get("stats_url") or "",
        }
        for r in rows
    ])
    flow_note = data.get("screener", {}).get("week_flow_note")
    if flow_note:
        st.caption(flow_note)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="Open"),
            "Fwd P/E": st.column_config.NumberColumn(format="%.2f"),
            "P/B": st.column_config.NumberColumn(format="%.2f"),
            "Div %": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_near_misses(data: dict, *, link_col: str = "finviz_url"):
    near = data.get("near_misses", [])
    if not near:
        return
    st.subheader("Near misses")
    st.caption("Large caps that pass a relaxed screen (see page subtitle).")
    df = pd.DataFrame([
        {
            "Ticker": r["ticker"],
            "Company": r.get("company", ""),
            "Fwd P/E": r["fpe_n"],
            "P/B": r["pb_n"],
            "Div %": r["div_n"],
            "Wk Net Inflow": r.get("week_flow", "—"),
            "Mkt Cap": r.get("mcap", ""),
            "Link": r.get(link_col) or r.get("stats_url") or "",
        }
        for r in near
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_disclaimer(source: str):
    st.divider()
    st.caption(
        f"Research tool only — not investment advice. Data: {source}. "
        "Verify before trading."
    )