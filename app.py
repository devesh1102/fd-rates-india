"""
Streamlit UI for Indian Bank FD Rates Fetcher.
Run with: streamlit run app.py
pandas>=2.2 uses Styler.map() not Styler.applymap()
"""

import sys
import threading
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.database import get_all_banks, get_best_rates, get_rates, has_data, init_db
from src.scrapers import SCRAPERS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="🏦 FD Rates India",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Init DB on startup
# ---------------------------------------------------------------------------
init_db()

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .rate-high   { color: #00c853; font-weight: bold; }
    .rate-mid    { color: #ffd600; font-weight: bold; }
    .rate-low    { color: #ff6d00; }
    .stDataFrame { font-size: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------




def tenure_to_days(tenure: str) -> int:
    import re
    s = tenure.lower().strip()
    m = re.search(r"(\d+)\s*(day|week|month|year)", s)
    if not m:
        return 365
    val, unit = int(m.group(1)), m.group(2)
    if "day" in unit:   return val
    if "week" in unit:  return val * 7
    if "month" in unit: return val * 30
    return val * 365


JS_BANKS: set[str] = set()          # all 9 banks now supported
HTML_BANKS = list(SCRAPERS.keys())

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🏦 FD Rates India")
st.sidebar.caption("Live rates from official bank websites")
st.sidebar.caption("v1.1 · pandas 2.x fix")

page = st.sidebar.radio(
    "Navigate",
    ["📥 Fetch Rates", "📊 Bank Explorer", "🏆 Best Rates", "📈 Compare Banks"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown("**9 Banks — Live Data**")
for k in SCRAPERS:
    full_name, url, _ = SCRAPERS[k]
    st.sidebar.markdown(f"✅ [{full_name}]({url})")

# ---------------------------------------------------------------------------
# PAGE: Fetch Rates
# ---------------------------------------------------------------------------
if page == "📥 Fetch Rates":
    st.title("📥 Fetch Latest FD Rates")
    st.markdown("Scrape live rates directly from official bank websites.")

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.multiselect(
            "Select banks to fetch",
            options=HTML_BANKS,
            default=HTML_BANKS,
            format_func=lambda k: SCRAPERS[k][0],
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_btn = st.button("🚀 Fetch Selected Banks", use_container_width=True, type="primary")

    if fetch_btn and selected:
        results = {}
        progress = st.progress(0, text="Starting…")
        log = st.empty()
        lines = []

        for i, key in enumerate(selected):
            full_name, url, scrape_fn = SCRAPERS[key]
            progress.progress((i) / len(selected), text=f"Fetching {full_name}…")
            try:
                rows = scrape_fn()
                if rows:
                    from src.database import upsert_rates
                    saved = upsert_rates(key, full_name, rows, url)
                    results[key] = ("success", saved)
                    lines.append(f"✅ **{full_name}** — {saved} rows saved")
                else:
                    results[key] = ("empty", 0)
                    lines.append(f"⚠️ **{full_name}** — 0 rows returned")
            except NotImplementedError:
                results[key] = ("skip", 0)
                lines.append(f"⏭️ **{full_name}** — JS-rendered, skipped")
            except Exception as e:
                results[key] = ("error", str(e))
                lines.append(f"❌ **{full_name}** — {e}")
            log.markdown("\n\n".join(lines))

        progress.progress(1.0, text="Done!")
        st.divider()
        ok = sum(1 for v in results.values() if v[0] == "success")
        total_rows = sum(v[1] for v in results.values() if v[0] == "success")
        st.success(f"Fetched **{ok}** banks · **{total_rows}** rows saved to database")

    elif fetch_btn and not selected:
        st.warning("Please select at least one bank.")

    # Show DB status
    st.divider()
    st.subheader("Database Status")
    if has_data():
        banks_in_db = get_all_banks()
        cols = st.columns(len(banks_in_db) if banks_in_db else 1)
        for i, b in enumerate(banks_in_db):
            rates = get_rates(b["bank"])
            with cols[i % len(cols)]:
                st.metric(b["full_name"], f"{len(rates)} rows", b["bank"])
    else:
        st.info("No data yet. Fetch rates above to get started.")

# ---------------------------------------------------------------------------
# PAGE: Bank Explorer
# ---------------------------------------------------------------------------
elif page == "📊 Bank Explorer":
    st.title("📊 Bank Rate Explorer")

    if not has_data():
        st.warning("No data in database. Go to **📥 Fetch Rates** first.")
        st.stop()

    banks_in_db = get_all_banks()
    bank_keys = [b["bank"] for b in banks_in_db]
    bank_names = {b["bank"]: b["full_name"] for b in banks_in_db}

    selected_bank = st.selectbox(
        "Select Bank",
        options=bank_keys,
        format_func=lambda k: bank_names.get(k, k),
    )

    if selected_bank:
        rates = get_rates(selected_bank)
        if not rates:
            st.info(f"No data for {selected_bank}.")
            st.stop()

        df = pd.DataFrame(rates)[
            ["tenure_label", "regular_rate", "senior_rate", "last_updated", "source_url"]
        ].rename(
            columns={
                "tenure_label": "Tenure",
                "regular_rate": "Regular (%)",
                "senior_rate": "Senior Citizen (%)",
                "last_updated": "Last Updated",
                "source_url": "Source URL",
            }
        )

        full_name = bank_names.get(selected_bank, selected_bank)
        last_updated = df["Last Updated"].iloc[0] if len(df) else "—"
        source_url = df["Source URL"].iloc[0] if len(df) else None

        col1, col2, col3 = st.columns(3)
        col1.metric("Bank", full_name)
        col2.metric("Peak Regular Rate", f"{df['Regular (%)'].max():.2f}%")
        col3.metric("Peak Senior Rate", f"{df['Senior Citizen (%)'].max():.2f}%")

        if source_url:
            st.markdown(
                f"🔗 **Source:** [{source_url}]({source_url})",
                unsafe_allow_html=False,
            )

        st.divider()

        # Styled table
        st.subheader(f"Rate Table  ·  *updated {last_updated}*")
        st.dataframe(
            df.drop(columns=["Last Updated", "Source URL"]),
            use_container_width=True,
            hide_index=True,
            height=min(60 + len(df) * 38, 600),
        )

        # Bar chart
        st.subheader("Rate Chart")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Regular",
            x=df["Tenure"],
            y=df["Regular (%)"],
            marker_color="#1976d2",
        ))
        fig.add_trace(go.Bar(
            name="Senior Citizen",
            x=df["Tenure"],
            y=df["Senior Citizen (%)"],
            marker_color="#43a047",
        ))
        fig.update_layout(
            barmode="group",
            xaxis_tickangle=-35,
            yaxis_title="Rate (%)",
            yaxis_range=[0, max(df["Senior Citizen (%)"].max() + 0.5, 9)],
            legend=dict(orientation="h", y=1.1),
            height=420,
            margin=dict(l=40, r=20, t=20, b=120),
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white",
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Best Rates
# ---------------------------------------------------------------------------
elif page == "🏆 Best Rates":
    st.title("🏆 Best FD Rates")

    if not has_data():
        st.warning("No data in database. Go to **📥 Fetch Rates** first.")
        st.stop()

    mode = st.radio(
        "Compare mode",
        ["🔍 By Tenure", "🌐 All Tenures (Best Rates)"],
        horizontal=True,
    )

    st.divider()

    # -------------------------------------------------------------------
    # MODE 1: All Tenures — best rate each bank offers, no tenure filter
    # -------------------------------------------------------------------
    if mode == "🌐 All Tenures (Best Rates)":
        st.markdown("**Best rate each bank offers across all tenures — no filter applied.**")

        banks_in_db = get_all_banks()
        bank_keys = [b["bank"] for b in banks_in_db]
        bank_names = {b["bank"]: b["full_name"] for b in banks_in_db}

        rows = []
        for k in bank_keys:
            for r in get_rates(k):
                rows.append({
                    "Bank": k,
                    "Full Name": bank_names.get(k, k),
                    "Tenure": r["tenure_label"],
                    "Regular (%)": r["regular_rate"],
                    "Senior (%)": r["senior_rate"],
                })

        df_all = pd.DataFrame(rows)

        # Best regular row per bank
        best_reg = (
            df_all.loc[df_all.groupby("Bank")["Regular (%)"].idxmax()]
            [["Bank", "Full Name", "Tenure", "Regular (%)"]]
            .rename(columns={"Tenure": "Best Regular Tenure"})
            .sort_values("Regular (%)", ascending=False)
            .reset_index(drop=True)
        )
        best_reg.index += 1

        # Best senior row per bank
        best_sen = (
            df_all.loc[df_all.groupby("Bank")["Senior (%)"].idxmax()]
            [["Bank", "Full Name", "Tenure", "Senior (%)"]]
            .rename(columns={"Tenure": "Best Senior Tenure"})
            .sort_values("Senior (%)", ascending=False)
            .reset_index(drop=True)
        )
        best_sen.index += 1

        col_r, col_s = st.columns(2)

        with col_r:
            st.subheader("💼 Best Regular Rates")
            st.dataframe(
                best_reg,
                use_container_width=True,
                height=min(60 + len(best_reg) * 38, 400),
            )
            fig = go.Figure(go.Bar(
                x=best_reg["Bank"],
                y=best_reg["Regular (%)"],
                text=best_reg["Regular (%)"].map(lambda v: f"{v:.2f}%"),
                textposition="outside",
                marker_color=[
                    "#ffd700" if i == 0 else "#c0c0c0" if i == 1 else "#cd7f32" if i == 2 else "#1976d2"
                    for i in range(len(best_reg))
                ],
                customdata=best_reg["Best Regular Tenure"],
                hovertemplate="%{x}<br>Rate: %{y:.2f}%<br>Tenure: %{customdata}<extra></extra>",
            ))
            fig.update_layout(
                yaxis_range=[best_reg["Regular (%)"].min() - 0.5, best_reg["Regular (%)"].max() + 0.8],
                yaxis_title="Rate (%)",
                height=320,
                margin=dict(l=40, r=10, t=10, b=40),
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_s:
            st.subheader("👴 Best Senior Citizen Rates")
            st.dataframe(
                best_sen,
                use_container_width=True,
                height=min(60 + len(best_sen) * 38, 400),
            )
            fig = go.Figure(go.Bar(
                x=best_sen["Bank"],
                y=best_sen["Senior (%)"],
                text=best_sen["Senior (%)"].map(lambda v: f"{v:.2f}%"),
                textposition="outside",
                marker_color=[
                    "#ffd700" if i == 0 else "#c0c0c0" if i == 1 else "#cd7f32" if i == 2 else "#43a047"
                    for i in range(len(best_sen))
                ],
                customdata=best_sen["Best Senior Tenure"],
                hovertemplate="%{x}<br>Rate: %{y:.2f}%<br>Tenure: %{customdata}<extra></extra>",
            ))
            fig.update_layout(
                yaxis_range=[best_sen["Senior (%)"].min() - 0.5, best_sen["Senior (%)"].max() + 0.8],
                yaxis_title="Rate (%)",
                height=320,
                margin=dict(l=40, r=10, t=10, b=40),
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Combined grouped bar
        st.subheader("📊 Regular vs Senior — Peak Rate Per Bank")
        merged = best_reg[["Bank", "Full Name", "Regular (%)"]].merge(
            best_sen[["Bank", "Senior (%)"]],
            on="Bank",
        ).sort_values("Senior (%)", ascending=False)

        fig_comb = go.Figure()
        fig_comb.add_trace(go.Bar(
            name="Regular",
            x=merged["Bank"],
            y=merged["Regular (%)"],
            text=merged["Regular (%)"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            marker_color="#1976d2",
        ))
        fig_comb.add_trace(go.Bar(
            name="Senior Citizen",
            x=merged["Bank"],
            y=merged["Senior (%)"],
            text=merged["Senior (%)"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            marker_color="#43a047",
        ))
        fig_comb.update_layout(
            barmode="group",
            yaxis_title="Rate (%)",
            yaxis_range=[merged["Regular (%)"].min() - 0.5, merged["Senior (%)"].max() + 0.8],
            legend=dict(orientation="h", y=1.1),
            height=380,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white",
        )
        st.plotly_chart(fig_comb, use_container_width=True)

    # -------------------------------------------------------------------
    # MODE 2: Filter by tenure
    # -------------------------------------------------------------------
    else:
        st.markdown("Find the highest rates for a specific tenure.")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tenure_options = [
                "7 days", "30 days", "3 months", "6 months",
                "1 year", "2 years", "3 years", "5 years",
            ]
            tenure_input = st.selectbox("Tenure", tenure_options, index=4)
        with col2:
            citizen_type = st.radio(
                "Customer Type", ["Both", "Regular", "Senior Citizen"],
                horizontal=True,
            )
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            top_n = st.number_input("Top N", min_value=3, max_value=20, value=10)

        days = tenure_to_days(tenure_input)
        ct_map = {"Both": "regular", "Regular": "regular", "Senior Citizen": "senior"}
        types_to_show = ["regular", "senior"] if citizen_type == "Both" else [ct_map[citizen_type]]

        for ct in types_to_show:
            results = get_best_rates(days, ct)
            if not results:
                st.info(f"No results found for **{tenure_input}** ({ct}). Try a broader tenure.")
                continue

            label = "Senior Citizen" if ct == "senior" else "Regular"
            st.subheader(f"{'🥇' if ct == 'regular' else '👴'} Top {top_n} — {label} rates for ~{tenure_input}")

            df = pd.DataFrame(results[:top_n]).rename(
                columns={
                    "bank": "Bank",
                    "full_name": "Full Name",
                    "tenure_label": "Matching Tenure Bucket",
                    "rate": "Rate (%)",
                }
            )[["Bank", "Full Name", "Matching Tenure Bucket", "Rate (%)"]]
            df.index = range(1, len(df) + 1)

            st.dataframe(
                df,
                use_container_width=True,
                height=min(60 + len(df) * 38, 500),
            )

            top3 = df.head(3)
            fig = go.Figure(go.Bar(
                x=top3["Bank"],
                y=top3["Rate (%)"],
                text=top3["Rate (%)"].map(lambda v: f"{v:.2f}%"),
                textposition="outside",
                marker_color=["#ffd700", "#c0c0c0", "#cd7f32"],
            ))
            fig.update_layout(
                yaxis_range=[df["Rate (%)"].min() - 0.5, df["Rate (%)"].max() + 0.5],
                yaxis_title="Rate (%)",
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Compare Banks
# ---------------------------------------------------------------------------
elif page == "📈 Compare Banks":
    st.title("📈 Compare Banks")
    st.markdown("Side-by-side rate comparison across tenures.")

    if not has_data():
        st.warning("No data in database. Go to **📥 Fetch Rates** first.")
        st.stop()

    banks_in_db = get_all_banks()
    bank_keys = [b["bank"] for b in banks_in_db]
    bank_names = {b["bank"]: b["full_name"] for b in banks_in_db}

    col1, col2 = st.columns([3, 2])
    with col1:
        selected_banks = st.multiselect(
            "Banks to compare",
            options=bank_keys,
            default=bank_keys,
            format_func=lambda k: bank_names.get(k, k),
        )
    with col2:
        rate_type = st.radio("Rate type", ["Regular", "Senior Citizen", "Both"], horizontal=True)

    if not selected_banks:
        st.info("Select at least one bank above.")
        st.stop()

    # Build full dataset
    all_data = []
    for k in selected_banks:
        for r in get_rates(k):
            all_data.append({
                "Bank": k,
                "Full Name": bank_names.get(k, k),
                "Tenure": r["tenure_label"],
                "Days Min": r["tenure_days_min"],
                "Regular (%)": r["regular_rate"],
                "Senior Citizen (%)": r["senior_rate"],
            })

    if not all_data:
        st.info("No data found.")
        st.stop()

    df_all = pd.DataFrame(all_data)

    # -----------------------------------------------------------------------
    # SECTION 1 — Peak Rates (always shown)
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("🏅 Highest Rates — Regular vs Senior Citizen")
    st.caption("Peak rate each bank offers across all tenures")

    peak_df = (
        df_all.groupby(["Bank", "Full Name"])
        .agg(
            regular_peak=("Regular (%)", "max"),
            senior_peak=("Senior Citizen (%)", "max"),
        )
        .reset_index()
        .sort_values("senior_peak", ascending=False)
        .rename(columns={
            "regular_peak": "Best Regular (%)",
            "senior_peak": "Best Senior (%)",
        })
    )
    peak_df["Extra for Senior"] = (
        peak_df["Best Senior (%)"] - peak_df["Best Regular (%)"]
    ).round(2).map(lambda v: f"+{v:.2f}%" if pd.notna(v) else "—")

    col_tbl, col_chart = st.columns([1, 2])

    with col_tbl:
        st.dataframe(
            peak_df,
            use_container_width=True,
            hide_index=True,
            height=min(60 + len(peak_df) * 38, 420),
        )

    with col_chart:
        fig_peak = go.Figure()
        fig_peak.add_trace(go.Bar(
            name="Regular",
            x=peak_df["Bank"],
            y=peak_df["Best Regular (%)"],
            text=peak_df["Best Regular (%)"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            marker_color="#1976d2",
        ))
        fig_peak.add_trace(go.Bar(
            name="Senior Citizen",
            x=peak_df["Bank"],
            y=peak_df["Best Senior (%)"],
            text=peak_df["Best Senior (%)"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            marker_color="#43a047",
        ))
        fig_peak.update_layout(
            barmode="group",
            yaxis_title="Rate (%)",
            yaxis_range=[
                max(0, peak_df["Best Regular (%)"].min() - 1),
                peak_df["Best Senior (%)"].max() + 0.8,
            ],
            legend=dict(orientation="h", y=1.12),
            height=360,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white",
        )
        st.plotly_chart(fig_peak, use_container_width=True)

    # Winner callouts
    best_reg_row = peak_df.loc[peak_df["Best Regular (%)"].idxmax()]
    best_sen_row = peak_df.loc[peak_df["Best Senior (%)"].idxmax()]
    c1, c2 = st.columns(2)
    c1.success(
        f"🥇 **Best Regular:** {best_reg_row['Full Name']}  \n"
        f"**{best_reg_row['Best Regular (%)']:.2f}%**"
    )
    c2.success(
        f"🥇 **Best Senior Citizen:** {best_sen_row['Full Name']}  \n"
        f"**{best_sen_row['Best Senior (%)']:.2f}%**"
    )

    # -----------------------------------------------------------------------
    # SECTION 2 — Heatmap / line charts by rate type
    # -----------------------------------------------------------------------
    st.divider()
    rate_col = "Senior Citizen (%)" if rate_type == "Senior Citizen" else "Regular (%)"
    show_both = rate_type == "Both"

    if not show_both:
        st.subheader(f"{rate_type} Rates — Full Tenure Heatmap")
        pivot = (
            df_all.groupby(["Bank", "Tenure", "Days Min"])[rate_col]
            .first()
            .reset_index()
            .sort_values("Days Min")
            .pivot_table(index="Tenure", columns="Bank", values=rate_col, aggfunc="max")
        )
        order = (
            df_all.sort_values("Days Min")
            .drop_duplicates("Tenure")["Tenure"]
            .tolist()
        )
        pivot = pivot.reindex([r for r in order if r in pivot.index])

        fig = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0.0, "#b71c1c"],
                [0.4, "#e65100"],
                [0.6, "#f9a825"],
                [0.75, "#388e3c"],
                [1.0, "#00c853"],
            ],
            text=[[f"{v:.2f}%" if v == v else "—" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            showscale=True,
            colorbar=dict(title="Rate %"),
        ))
        fig.update_layout(
            height=max(300, len(pivot) * 32 + 100),
            margin=dict(l=220, r=20, t=20, b=60),
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="white",
            xaxis=dict(side="top"),
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.subheader("Regular vs Senior — Full Tenure Line Charts")
        col1, col2 = st.columns(2)
        for col_ui, rtype in [(col1, "Regular (%)"), (col2, "Senior Citizen (%)")]:
            with col_ui:
                st.markdown(f"**{rtype.replace(' (%)', '')}**")
                fig = go.Figure()
                for bank in selected_banks:
                    bdf = df_all[df_all["Bank"] == bank].sort_values("Days Min")
                    fig.add_trace(go.Scatter(
                        x=bdf["Tenure"],
                        y=bdf[rtype],
                        mode="lines+markers",
                        name=bank,
                    ))
                fig.update_layout(
                    height=380,
                    xaxis_tickangle=-40,
                    yaxis_title="Rate (%)",
                    legend=dict(orientation="h", y=1.15),
                    margin=dict(l=40, r=10, t=10, b=120),
                    plot_bgcolor="#0e1117",
                    paper_bgcolor="#0e1117",
                    font_color="white",
                )
                st.plotly_chart(fig, use_container_width=True)

    # Raw data table
    with st.expander("📋 Raw data table"):
        cols_show = ["Bank", "Tenure", "Regular (%)", "Senior Citizen (%)"]
        st.dataframe(
            df_all[cols_show].sort_values(["Bank", "Days Min"]),
            use_container_width=True,
            hide_index=True,
        )
