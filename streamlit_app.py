from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analyze_resegmentation import (
    K2M,
    KORP,
    M2K,
    MSB,
    load_data,
    summarize_h1,
    summarize_h2,
    summarize_improvement,
    weak_client_mask,
)


st.set_page_config(
    page_title="Дашборд ресегментации",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


COLORS = {
    "teal": "#149FA8",
    "teal_soft": "#149FA8",
    "amber": "#D7B56D",
    "amber_soft": "#D7B56D",
    "ink": "#2B2A29",
    "muted": "#898989",
    "rose": "#898989",
    "olive": "#7688A1",
    "blue": "#193F72",
    "violet": "#2957A2",
    "sand": "#F1F2F7",
    "paper": "rgba(255,253,250,0.0)",
    "plot": "rgba(254,254,254,0.90)",
}

CREDIT_COLORS = {
    0: "#D9DADA",
    1: "#149FA8",
    2: "#7688A1",
    3: "#2957A2",
    4: "#193F72",
    5: "#2B2A29",
}

SEGMENT_CONFIG = {
    KORP: {
        "transfer_in": M2K,
        "transfer_out": K2M,
        "accent": COLORS["amber"],
    },
    MSB: {
        "transfer_in": K2M,
        "transfer_out": M2K,
        "accent": COLORS["blue"],
    },
}

ENTRY_STATUSES = {"entry", "re_entry"}
EXIT_STATUSES = {"exit_ahd", "re_exit_ahd"}


def is_segment_entry(df: pd.DataFrame, segment: str) -> pd.Series:
    entry_mask = df["status"].astype(str).isin(ENTRY_STATUSES)
    return (df["segment"] == segment) & entry_mask


def is_segment_exit(df: pd.DataFrame, segment: str) -> pd.Series:
    if segment != MSB:
        return pd.Series(False, index=df.index)
    exit_mask = df["status"].astype(str).isin(EXIT_STATUSES)
    return (df["segment"] == segment) & exit_mask


def is_segment_closed(df: pd.DataFrame, segment: str) -> pd.Series:
    if "is_closed" in df.columns:
        closed_mask = pd.to_numeric(df["is_closed"], errors="coerce").fillna(0).eq(1)
    else:
        closed_mask = pd.Series(False, index=df.index)
    return (df["segment"] == segment) & closed_mask


def format_status_label(value: object) -> str:
    status = str(value)
    if status in {"entry", "re_entry"}:
        return "Новые"
    return status

def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-soft: #f5f1e8;
            --panel: #fffdfa;
            --ink: #1e1e1b;
            --muted: #6c6a63;
            --accent: #0f766e;
            --accent-2: #b45309;
            --border: #ddd7c9;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.08), transparent 30%),
                radial-gradient(circle at left top, rgba(180, 83, 9, 0.08), transparent 28%),
                linear-gradient(180deg, #f7f4ed 0%, #f2eee5 100%);
            color: var(--ink);
        }

        .stApp *, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp span, .stApp label, .stApp div, .stApp section, .stApp article,
        .stApp a, .stApp button, .stApp input, .stApp select, .stApp textarea {
            color: var(--ink) !important;
        }

        [data-testid="stSidebar"] {
            background-color: #fffdfa !important;
            color: var(--ink) !important;
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }

        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] button,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--ink) !important;
        }

        [data-testid="stSidebar"] [role="button"] {
            background: rgba(241, 242, 247, 0.95) !important;
        }

        .js-plotly-plot .main-svg text,
        .js-plotly-plot .main-svg .xtick text,
        .js-plotly-plot .main-svg .ytick text,
        .js-plotly-plot .main-svg .gtitle text,
        .js-plotly-plot .main-svg .legend text {
            fill: var(--ink) !important;
        }

        .stApp *::placeholder {
            color: rgba(43, 42, 41, 0.65) !important;
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
        }

        .hero {
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.10), rgba(180, 83, 9, 0.10));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.1;
        }

        .hero p {
            margin: 0.45rem 0 0 0;
            color: var(--muted);
            font-size: 1rem;
        }

        .mini-note {
            color: var(--muted);
            font-size: 0.95rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 253, 250, 0.92);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.55rem 0.75rem;
        }

        .section-card {
            background: rgba(255, 253, 250, 0.9);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.9rem 1rem 0.3rem 1rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stTabs"] {
            margin-top: 0.4rem;
        }

        div[data-testid="stTabs"] > div:first-child {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid #d9dada;
            border-radius: 22px;
            padding: 0.45rem;
            box-shadow: 0 10px 26px rgba(25, 63, 114, 0.08);
            margin-bottom: 1rem;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 0.55rem;
        }

        div[data-testid="stTabs"] [role="tab"] {
            min-height: 64px;
            padding: 0.85rem 1.25rem;
            border-radius: 16px;
            border: 1px solid transparent;
            background: rgba(241, 242, 247, 0.88);
            color: #7688A1;
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            transition: all 0.18s ease;
        }

        div[data-testid="stTabs"] [role="tab"]:hover {
            border-color: #d7b56d;
            background: rgba(215, 181, 109, 0.14);
            color: #193f72;
        }

        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, rgba(118, 136, 161, 0.96), rgba(118, 136, 161, 0.96));
            color: #ffffff;
            border-color: rgba(118, 136, 161, 0.9);
            box-shadow: 0 12px 26px rgba(118, 136, 161, 0.24);
        }

        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
            color: #fefefe;
        }

        div[data-testid="stTabs"] [role="tab"] p {
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.2;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Загрузка и агрегация df_all.csv...")
def get_analysis_bundle():
    df = load_data()
    h1 = summarize_h1(df)
    h2 = summarize_h2(df)
    improvement = summarize_improvement(h1)
    outcomes = h2["outcomes"]
    return df, h1, h2, improvement, outcomes


def to_percent(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.mean()) * 100.0


def mean_credit_class_nonzero(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    values = values[values.isin([1, 2, 3, 4, 5])]
    return float(values.mean()) if not values.empty else 0.0


RU_MONTH_SHORT = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}


def month_point_label(value: pd.Timestamp | str) -> str:
    ts = pd.Timestamp(value)
    return f"{RU_MONTH_SHORT[ts.month]} {ts.year}"


def month_point_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).map(month_point_label)


def credit_class_reference_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Класс": "class (0)", "Описание": "нет кредита"},
            {"Класс": "PL (class 1)", "Описание": "до 30 дней"},
            {"Класс": "PL (class 2)", "Описание": "31-90"},
            {"Класс": "NPL (class 3)", "Описание": "91-180"},
            {"Класс": "NPL (class 4)", "Описание": "181-365"},
            {"Класс": "NPL (class 5)", "Описание": "365+"},
        ]
    )


def apply_fig_style(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"color": COLORS["ink"]}},
        template="plotly_white",
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["plot"],
        font={"family": "Segoe UI, Arial, sans-serif", "color": COLORS["ink"]},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
            "xanchor": "left",
            "x": 0,
            "title": {"text": ""},
            "font": {"color": COLORS["ink"]},
        },
        margin={"l": 24, "r": 24, "t": 88, "b": 92},
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, color=COLORS["ink"], title_font_color=COLORS["ink"], tickfont={"color": COLORS["ink"]}, gridcolor="rgba(31,41,55,0.10)")
    fig.update_yaxes(color=COLORS["ink"], title_font_color=COLORS["ink"], tickfont={"color": COLORS["ink"]}, gridcolor="rgba(31,41,55,0.10)")
    return fig


def render_plot(fig: go.Figure, key: str) -> None:
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displaylogo": False, "responsive": True},
        key=key,
    )


def build_range_slider(container, label: str, min_value: float, max_value: float, key: str) -> tuple[float, float]:
    if min_value == max_value:
        return (min_value, max_value)
    slider_value = container.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=(min_value, max_value),
        key=key,
        width="stretch",
    )
    return slider_value if isinstance(slider_value, tuple) else (slider_value, slider_value)


def build_boolean_metric_table(
    left: pd.DataFrame,
    right: pd.DataFrame,
    metrics: list[tuple[str, str]],
    left_label: str,
    right_label: str,
) -> pd.DataFrame:
    rows = []
    for label, col in metrics:
        left_val = round(to_percent(left[col]), 2)
        right_val = round(to_percent(right[col]), 2)
        rows.append(
            {
                "Показатель": label,
                left_label: left_val,
                right_label: right_val,
                "Разрыв": round(left_val - right_val, 2),
            }
        )
    return pd.DataFrame(rows)


def build_boolean_metric_count_table(
    left: pd.DataFrame,
    right: pd.DataFrame,
    metrics: list[tuple[str, str]],
    left_label: str,
    right_label: str,
) -> pd.DataFrame:
    rows = []
    for label, col in metrics:
        left_val = int(left[col].fillna(False).sum())
        right_val = int(right[col].fillna(False).sum())
        rows.append(
            {
                "Показатель": label,
                left_label: left_val,
                right_label: right_val,
                "Разрыв": left_val - right_val,
            }
        )
    return pd.DataFrame(rows)


def get_pre_segment(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    pre = df[(df["segment"] == segment) & (df["next_is_consecutive"])].copy()
    pre["risk_any"] = pre["npl_now"] | pre["npl_within_3m"]
    pre["clean_now"] = pre["credit_class"] == 0
    pre["good_upgrade_candidate"] = (
        pre["corp_rule"] & pre["clean_now"] & (~pre["has_debt_now"]) & (~pre["npl_now"])
    )
    pre["is_group_or_official"] = (pre["is_group"] == 1) | (pre["is_official"] == 1)
    return pre


def filter_transfer_view(
    df: pd.DataFrame,
    source_segment: str,
    transfer_status: str,
    selected_months: list[pd.Timestamp],
    scope: str,
    quality_only: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pre = get_pre_segment(df, source_segment)
    if selected_months:
        pre = pre[pre["next_eomonth"].isin(selected_months)]

    transfer_pre = pre[pre["next_status"] == transfer_status].copy()
    retain_pre = pre[pre["next_segment"] == source_segment].copy()

    if scope in {"Only clients that fail KORP rule", "Только клиенты, не проходящие правило КОРП"}:
        transfer_pre = transfer_pre[~transfer_pre["corp_rule"]]
        retain_pre = retain_pre[~retain_pre["corp_rule"]]
    elif scope in {"Only clients that meet KORP rule", "Только клиенты, проходящие правило КОРП"}:
        transfer_pre = transfer_pre[transfer_pre["corp_rule"]]
        retain_pre = retain_pre[retain_pre["corp_rule"]]

    if quality_only:
        transfer_pre = transfer_pre[transfer_pre["good_upgrade_candidate"]]
        retain_pre = retain_pre[retain_pre["good_upgrade_candidate"]]

    return transfer_pre, retain_pre


def build_entry_month_summary(outcomes: pd.DataFrame, horizon: int) -> pd.DataFrame:
    mature = get_mature_entry_outcomes(outcomes, horizon)
    if mature.empty:
        return pd.DataFrame(
            columns=[
                "entry_date",
                "entries",
                "left_within",
                "to_msb_within",
                "drop_within",
                "weak_share",
                "to_msb_count",
                "weak_count",
                "weak_to_msb_count",
                "weak_not_to_msb_count",
                "not_to_msb_count",
            ]
        )

    mature = mature.copy()
    mature["weak_to_msb"] = mature["weak"] & mature["to_msb_within"]
    mature["weak_not_to_msb"] = mature["weak"] & ~mature["to_msb_within"]

    summary = (
        mature.groupby("entry_date")
        .agg(
            entries=("client_code", "size"),
            left_within=("left_within", "mean"),
            to_msb_within=("to_msb_within", "mean"),
            drop_within=("drop_within", "mean"),
            weak_share=("weak", "mean"),
            to_msb_count=("to_msb_within", "sum"),
            weak_count=("weak", "sum"),
            weak_to_msb_count=("weak_to_msb", "sum"),
            weak_not_to_msb_count=("weak_not_to_msb", "sum"),
        )
        .reset_index()
    )
    summary["not_to_msb_count"] = summary["entries"] - summary["to_msb_count"]
    for col in ["left_within", "to_msb_within", "drop_within", "weak_share"]:
        summary[col] = (summary[col] * 100).round(2)
    for col in ["to_msb_count", "weak_count", "weak_to_msb_count", "weak_not_to_msb_count", "not_to_msb_count"]:
        summary[col] = summary[col].astype(int)
    return summary


def fig_entry_flow(summary: pd.DataFrame, horizon: int, weak_scope: str = "all") -> go.Figure:
    if summary.empty:
        fig = go.Figure()
        fig.update_xaxes(type="category")
        fig.update_yaxes(title="\u0412\u0445\u043e\u0434\u044b")
        return apply_fig_style(
            fig,
            f"\u0412\u0445\u043e\u0434\u044b \u0432 \u041a\u041e\u0420\u041f \u043f\u043e \u043c\u0435\u0441\u044f\u0446\u0430\u043c \u0438 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b \u0447\u0435\u0440\u0435\u0437 {horizon} \u043c\u0435\u0441."
        )

    plot_df = summary.copy()
    x = month_point_series(plot_df["entry_date"])

    if weak_scope == "to_msb":
        weak_line = np.where(
            plot_df["to_msb_count"] > 0,
            plot_df["weak_to_msb_count"] / plot_df["to_msb_count"] * 100,
            0.0,
        )
        weak_line_name = "Доля слабых"
        show_to_msb = True
        show_not_to_msb = False
    elif weak_scope == "stay_korp":
        weak_line = np.where(
            plot_df["not_to_msb_count"] > 0,
            plot_df["weak_not_to_msb_count"] / plot_df["not_to_msb_count"] * 100,
            0.0,
        )
        weak_line_name = "Доля слабых"
        show_to_msb = False
        show_not_to_msb = True
    else:
        weak_line = plot_df["weak_share"].to_numpy(dtype=float)
        weak_line_name = "Доля слабых"
        show_to_msb = True
        show_not_to_msb = True

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if show_not_to_msb:
        fig.add_trace(
            go.Bar(
                x=x,
                y=plot_df["not_to_msb_count"],
                name="Остались в КОРП",
                marker_color="#D7B56D",
                hovertemplate="%{x}<br>Остались в КОРП: %{y:,.0f}<extra></extra>",
            ),
            secondary_y=False,
        )
    if show_to_msb:
        fig.add_trace(
            go.Bar(
                x=x,
                y=plot_df["to_msb_count"],
                name=f"Переведены в МСБ за {horizon} мес.",
                marker_color="#193F72",
                hovertemplate="%{x}<br>\u041f\u0435\u0440\u0435\u0432\u0435\u0434\u0435\u043d\u044b \u0432 \u041c\u0421\u0411: %{y:,.0f}<extra></extra>",
            ),
            secondary_y=False,
        )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=weak_line,
            mode="lines+markers",
            name=weak_line_name,
            line={"color": COLORS["muted"], "width": 2.5},
            marker={"color": COLORS["muted"], "size": 7},
            hovertemplate="%{x}<br>%{fullData.name}: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(barmode="stack")
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_yaxes(title_text="\u0412\u0445\u043e\u0434\u044b", secondary_y=False)
    fig.update_yaxes(
        title_text="\u0414\u043e\u043b\u044f \u0441\u043b\u0430\u0431\u044b\u0445, %",
        secondary_y=True,
        range=[0, 100],
        showgrid=False,
    )
    return apply_fig_style(
        fig,
        f"\u0412\u0445\u043e\u0434\u044b \u0432 \u041a\u041e\u0420\u041f \u043f\u043e \u043c\u0435\u0441\u044f\u0446\u0430\u043c \u0438 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b \u0447\u0435\u0440\u0435\u0437 {horizon} \u043c\u0435\u0441."
    )


def get_mature_entry_outcomes(outcomes: pd.DataFrame, horizon: int) -> pd.DataFrame:
    mature = outcomes[outcomes["months_observable_after_entry"] >= horizon].copy()
    mature["left_within"] = mature["months_to_event"].fillna(999) <= horizon
    mature["to_msb_within"] = (mature["event_type"] == "to_msb") & mature["left_within"]
    mature["drop_within"] = (mature["event_type"] == "drop_or_closed") & mature["left_within"]
    return mature


def build_credit_mix(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    classes = [0, 1, 2, 3, 4, 5]
    left_counts = left["credit_class"].value_counts(normalize=True).reindex(classes, fill_value=0)
    right_counts = right["credit_class"].value_counts(normalize=True).reindex(classes, fill_value=0)
    return pd.DataFrame(
        {
            "credit_class": classes,
            "Когорта перевода": (left_counts.values * 100).round(2),
            "Удержанная когорта": (right_counts.values * 100).round(2),
        }
    )


def build_credit_mix_counts(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    classes = [0, 1, 2, 3, 4, 5]
    left_counts = left["credit_class"].value_counts().reindex(classes, fill_value=0)
    right_counts = right["credit_class"].value_counts().reindex(classes, fill_value=0)
    return pd.DataFrame(
        {
            "credit_class": classes,
            "КОРП→МСБ": left_counts.values,
            "Остались в КОРП": right_counts.values,
        }
    )


def build_h1_credit_class_dynamics(
    df: pd.DataFrame, transfer_pre: pd.DataFrame, retain_pre: pd.DataFrame
) -> pd.DataFrame:
    base = df[["client_code", "month_id", "credit_class"]].copy()

    def expand(anchor: pd.DataFrame, cohort_label: str) -> pd.DataFrame:
        anchors = anchor[["client_code", "next_month_id"]].copy()
        anchors = anchors.rename(columns={"next_month_id": "event_month_id"})
        if anchors.empty:
            return pd.DataFrame(columns=["cohort", "relative_month", "credit_class", "share_pct"])

        relatives = pd.DataFrame({"relative_month": list(range(-6, 7))})
        anchors["__key"] = 1
        relatives["__key"] = 1
        expanded = anchors.merge(relatives, on="__key", how="inner").drop(columns="__key")
        expanded["target_month_id"] = expanded["event_month_id"] + expanded["relative_month"]
        expanded = expanded.merge(
            base,
            left_on=["client_code", "target_month_id"],
            right_on=["client_code", "month_id"],
            how="left",
        )
        expanded["cohort"] = cohort_label
        expanded = expanded[expanded["credit_class"].notna() & expanded["credit_class"].gt(0)].copy()
        if expanded.empty:
            return pd.DataFrame(columns=["cohort", "relative_month", "credit_class", "share_pct"])

        counts = (
            expanded.groupby(["cohort", "relative_month", "credit_class"])
            .size()
            .rename("clients")
            .reset_index()
        )
        totals = (
            expanded.groupby(["cohort", "relative_month"])
            .size()
            .rename("total_clients")
            .reset_index()
        )
        counts = counts.merge(totals, on=["cohort", "relative_month"], how="left")
        counts["share_pct"] = counts["clients"] / counts["total_clients"] * 100
        return counts

    return pd.concat(
        [
            expand(transfer_pre, "КОРП→МСБ"),
            expand(retain_pre, "Остались в КОРП"),
        ],
        ignore_index=True,
    )


def build_h1_numeric_dynamics(
    df: pd.DataFrame,
    transfer_pre: pd.DataFrame,
    retain_pre: pd.DataFrame,
    value_col: str,
) -> pd.DataFrame:
    base = df[["client_code", "month_id", value_col]].copy()

    def expand(anchor: pd.DataFrame, cohort_label: str) -> pd.DataFrame:
        anchors = anchor[["client_code", "next_month_id"]].copy()
        anchors = anchors.rename(columns={"next_month_id": "event_month_id"})
        if anchors.empty:
            return pd.DataFrame(
                columns=[
                    "cohort",
                    "relative_month",
                    "median_nonzero",
                    "p25_nonzero",
                    "p75_nonzero",
                    "zero_share_pct",
                    "clients",
                ]
            )

        relatives = pd.DataFrame({"relative_month": list(range(-6, 7))})
        anchors["__key"] = 1
        relatives["__key"] = 1
        expanded = anchors.merge(relatives, on="__key", how="inner").drop(columns="__key")
        expanded["target_month_id"] = expanded["event_month_id"] + expanded["relative_month"]
        expanded = expanded.merge(
            base,
            left_on=["client_code", "target_month_id"],
            right_on=["client_code", "month_id"],
            how="left",
        )
        expanded["cohort"] = cohort_label
        expanded = expanded[expanded[value_col].notna()].copy()
        if expanded.empty:
            return pd.DataFrame(
                columns=[
                    "cohort",
                    "relative_month",
                    "median_nonzero",
                    "p25_nonzero",
                    "p75_nonzero",
                    "zero_share_pct",
                    "clients",
                ]
            )

        def summarize(group: pd.DataFrame) -> pd.Series:
            values = pd.to_numeric(group[value_col], errors="coerce").dropna()
            nonzero = values[values > 0]
            zero_share = float((values == 0).mean() * 100) if len(values) else 0.0
            if len(nonzero):
                return pd.Series(
                    {
                        "median_nonzero": float(nonzero.median()),
                        "p25_nonzero": float(nonzero.quantile(0.25)),
                        "p75_nonzero": float(nonzero.quantile(0.75)),
                        "zero_share_pct": zero_share,
                        "clients": int(len(values)),
                    }
                )
            return pd.Series(
                {
                    "median_nonzero": 0.0,
                    "p25_nonzero": 0.0,
                    "p75_nonzero": 0.0,
                    "zero_share_pct": zero_share,
                    "clients": int(len(values)),
                }
            )

        return (
            expanded.groupby(["cohort", "relative_month"], as_index=False)
            .apply(summarize)
            .reset_index(drop=True)
        )

    return pd.concat(
        [
            expand(transfer_pre, "КОРП→МСБ"),
            expand(retain_pre, "Остались в КОРП"),
        ],
        ignore_index=True,
    )


def build_zero_share_comparison(
    left: pd.DataFrame, right: pd.DataFrame, value_col: str, left_label: str, right_label: str
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Когорта": left_label,
                "Нулевой оборот, %": round((left[value_col] == 0).mean() * 100 if len(left) else 0, 2),
            },
            {
                "Когорта": right_label,
                "Нулевой оборот, %": round((right[value_col] == 0).mean() * 100 if len(right) else 0, 2),
            },
        ]
    )


def build_segment_event_summary(df: pd.DataFrame) -> pd.DataFrame:
    status_series = df["status"].astype(str)
    months = pd.Index(sorted(df["eomonth"].dropna().unique()))
    summaries = []
    for segment, cfg in SEGMENT_CONFIG.items():
        segment_rows = df["segment"] == segment
        total_clients = (
            df[segment_rows]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        direct_entries = (
            df[segment_rows & status_series.isin(ENTRY_STATUSES)]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        transfer_in = (
            df[status_series.eq(cfg["transfer_in"])]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        transfer_out = (
            df[status_series.eq(cfg["transfer_out"])]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        exits_outside = (
            df[segment_rows & status_series.isin(EXIT_STATUSES)]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        closed_rows = df[segment_rows & is_segment_closed(df, segment)].copy()
        closed_positive = (
            closed_rows[closed_rows["next_is_consecutive"]]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        closed_negative = (
            closed_rows[~closed_rows["next_is_consecutive"]]
            .groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )
        closed_total = (
            closed_rows.groupby("eomonth")["client_code"]
            .nunique()
            .reindex(months, fill_value=0)
        )

        summary = pd.DataFrame(
            {
                "eomonth": months,
                "segment": segment,
                "total_clients": total_clients.values,
                "direct_entries": direct_entries.values,
                "transfer_in": transfer_in.values,
                "transfer_out": transfer_out.values,
                "exits_outside": exits_outside.values,
                "closed_positive": closed_positive.values,
                "closed_negative": closed_negative.values,
                "closed_total": closed_total.values,
            }
        )
        summary["continuing_base"] = (
            summary["total_clients"]
            - summary["direct_entries"]
            - summary["transfer_in"]
        ).clip(lower=0)
        summary["net_client_change"] = summary["total_clients"].diff().fillna(0)
        summaries.append(summary)

    return pd.concat(summaries, ignore_index=True)


def build_turnover_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["eomonth", "segment"])
        .agg(
            total_clients=("client_code", "nunique"),
            total_turnover_bn=("turnover_bn", "sum"),
            total_turnover_y_bn=("turnover_y_bn", "sum"),
            mean_turnover_bn=("turnover_bn", "mean"),
            median_turnover_bn=("turnover_bn", "median"),
            mean_credit_class=("credit_class", mean_credit_class_nonzero),
        )
        .reset_index()
    )
    summary["turnover_per_client_bn"] = (
        summary["total_turnover_bn"] / summary["total_clients"].replace(0, pd.NA)
    ).fillna(0)
    return summary


def build_credit_trend(df: pd.DataFrame, segment: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    seg = df[df["segment"] == segment].copy()
    credit_only = seg[seg["credit_class"] > 0].copy()
    counts = (
        credit_only.groupby(["eomonth", "credit_class"])
        .size()
        .rename("clients")
        .reset_index()
    )
    totals = credit_only.groupby("eomonth").size().rename("total_clients").reset_index()
    counts = counts.merge(totals, on="eomonth", how="left")
    counts["share_pct"] = counts["clients"] / counts["total_clients"] * 100

    mean_credit = (
        credit_only.groupby("eomonth")
        .agg(
            mean_credit_class=("credit_class", mean_credit_class_nonzero),
            npl_share=("npl_now", "mean"),
            has_debt_share=("has_debt_now", "mean"),
        )
        .reset_index()
    )
    mean_credit["npl_share"] = mean_credit["npl_share"] * 100
    mean_credit["has_debt_share"] = mean_credit["has_debt_share"] * 100
    return counts, mean_credit


def build_credit_presence_trend(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    seg = df[df["segment"] == segment].copy()
    summary = (
        seg.assign(credit_presence=seg["credit_class"].eq(0).map({True: "Без кредита (class 0)", False: "С кредитом (class 1, 2, 3, 4, 5)"}))
        .groupby(["eomonth", "credit_presence"])["client_code"]
        .nunique()
        .rename("clients")
        .reset_index()
    )
    return summary


def fig_active_base(summary: pd.DataFrame, segment: str) -> go.Figure:
    seg = summary[summary["segment"] == segment].copy()
    x = month_point_series(seg["eomonth"])
    fig = go.Figure()
    positive_layers = [
        ("continuing_base", "Текущие", COLORS["sand"]),
        ("direct_entries", "Новые", COLORS["amber_soft"]),
        ("transfer_in", "Переводы в сегмент", COLORS["amber"]),
    ]
    negative_layers = [
        ("transfer_out", "Переводы из сегмента", COLORS["violet"]),
        ("exits_outside", "вне АКБ", COLORS["rose"]),
    ]
    for col, label, color in positive_layers:
        if float(seg[col].fillna(0).abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg[col],
                mode="lines",
                line={"width": 0.7, "color": color},
                stackgroup="one",
                name=label,
                showlegend=True,
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )
    for col, label, color in negative_layers:
        if float(seg[col].fillna(0).abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-seg[col],
                mode="lines",
                line={"width": 0.7, "color": color},
                stackgroup="negative",
                name=label,
                showlegend=True,
                hovertemplate="%{x}<br>" + label + ": %{customdata:,.0f}<extra></extra>",
                customdata=seg[col],
            )
        )
    new_client_text = seg["direct_entries"].where(seg["direct_entries"].gt(0), "")
    if (seg["direct_entries"] > 0).any():
        label_offset = (seg["total_clients"].max() * 0.018) if len(seg) else 0
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["total_clients"] + label_offset,
                mode="text",
                text=new_client_text,
                textposition="top center",
                textfont={"color": COLORS["amber"], "size": 11},
                showlegend=False,
                hoverinfo="skip",
                cliponaxis=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["direct_entries"],
                mode="lines+markers+text",
                text=new_client_text,
                textposition="top center",
                textfont={"color": COLORS["amber"], "size": 11},
                line={"color": COLORS["amber"], "width": 1.5, "dash": "dot"},
                marker={"color": COLORS["amber"], "size": 6},
                showlegend=False,
                hovertemplate="%{x}<br>Новые: %{y:,.0f}<extra></extra>",
            )
        )
    outside_text = seg["exits_outside"].where(seg["exits_outside"].gt(0), "")
    if (seg["exits_outside"] > 0).any():
        exit_offset = max(float(seg["exits_outside"].max()) * 0.08, 40.0)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-(seg["exits_outside"] + exit_offset),
                mode="text",
                text=outside_text,
                textposition="bottom center",
                textfont={"color": COLORS["blue"], "size": 11},
                showlegend=False,
                hoverinfo="skip",
                cliponaxis=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-seg["exits_outside"],
                mode="lines+markers+text",
                text=outside_text,
                textposition="bottom center",
                textfont={"color": COLORS["blue"], "size": 11},
                line={"color": COLORS["blue"], "width": 1.5, "dash": "dot"},
                marker={"color": COLORS["blue"], "size": 6},
                showlegend=False,
                hovertemplate="%{x}<br>вне АКБ: %{customdata:,.0f}<extra></extra>",
                customdata=seg["exits_outside"],
            )
        )
    if float(seg["closed_total"].fillna(0).abs().sum()) > 0:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["closed_total"],
                mode="lines+markers",
                name="Закрытые",
                line={"color": COLORS["muted"], "width": 2, "dash": "dash"},
                hovertemplate="%{x}<br>Закрытые: %{y:,.0f}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=seg["total_clients"],
            mode="lines+markers",
            name="Всего клиентов сегмента",
            line={"color": COLORS["ink"], "width": 2.5},
            hovertemplate="%{x}<br>Клиенты сегмента: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(xaxis={"type": "category"})
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title="Клиенты", zeroline=True, zerolinecolor="rgba(31,41,55,0.35)")
    return apply_fig_style(fig, f"{segment}: Состав базы по сегменту")


def fig_active_base(summary: pd.DataFrame, segment: str) -> go.Figure:
    seg = summary[summary["segment"] == segment].copy()
    x = month_point_series(seg["eomonth"])
    fig = go.Figure()

    positive_layers = [
        ("continuing_base", "Текущие", COLORS["sand"]),
        ("direct_entries", "Новые", COLORS["amber_soft"]),
        ("transfer_in", "Переводы в сегмент", COLORS["amber"]),
    ]
    negative_layers = [
        ("transfer_out", "Переводы из сегмента", COLORS["violet"]),
        ("exits_outside", "вне АКБ", COLORS["blue"]),
    ]

    for col, label, color in positive_layers:
        values = seg[col].fillna(0)
        if float(values.abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=values,
                mode="lines",
                stackgroup="positive",
                line={"width": 0.8, "color": color},
                fillcolor=color,
                name=label,
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )

    for col, label, color in negative_layers:
        values = seg[col].fillna(0)
        if float(values.abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-values,
                mode="lines",
                stackgroup="negative",
                line={"width": 0.8, "color": color},
                fillcolor=color,
                name=label,
                customdata=values,
                hovertemplate="%{x}<br>" + label + ": %{customdata:,.0f}<extra></extra>",
            )
        )

    if float(seg["direct_entries"].fillna(0).abs().sum()) > 0:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["direct_entries"],
                mode="lines+markers",
                line={"color": COLORS["amber"], "width": 1.6},
                marker={"color": COLORS["amber"], "size": 5},
                showlegend=False,
                hovertemplate="%{x}<br>Новые: %{y:,.0f}<extra></extra>",
            )
        )

    if float(seg["transfer_out"].fillna(0).abs().sum()) > 0:
        transfer_out_text = seg["transfer_out"].where(seg["transfer_out"].gt(0), "")
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-seg["transfer_out"],
                mode="lines+markers+text",
                text=transfer_out_text,
                textposition="bottom center",
                textfont={"color": COLORS["violet"], "size": 11},
                line={"color": COLORS["violet"], "width": 1.6},
                marker={"color": COLORS["violet"], "size": 5},
                showlegend=False,
                customdata=seg["transfer_out"],
                hovertemplate="%{x}<br>Переводы из сегмента: %{customdata:,.0f}<extra></extra>",
                cliponaxis=False,
            )
        )

    if float(seg["closed_total"].fillna(0).abs().sum()) > 0:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["closed_total"],
                mode="lines+markers",
                name="Закрытые",
                line={"color": COLORS["muted"], "width": 2, "dash": "dash"},
                hovertemplate="%{x}<br>Закрытые: %{y:,.0f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=seg["total_clients"],
            mode="lines+markers",
            name="Всего клиентов сегмента",
            line={"color": COLORS["ink"], "width": 2.5},
            hovertemplate="%{x}<br>Всего клиентов сегмента: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(xaxis={"type": "category"})
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title="Клиенты", zeroline=True, zerolinecolor="rgba(31,41,55,0.35)")
    return apply_fig_style(fig, f"{segment}: Состав базы по сегменту")


def fig_active_base(summary: pd.DataFrame, segment: str) -> go.Figure:
    seg = summary[summary["segment"] == segment].copy()
    x = month_point_series(seg["eomonth"])
    fig = go.Figure()

    positive_layers = [
        ("continuing_base", "Текущие", COLORS["sand"]),
        ("direct_entries", "Новые", "#B2B3B3"),
        ("transfer_in", "Переводы в сегмент", COLORS["amber"]),
    ]
    negative_layers = [
        ("transfer_out", "Переводы из сегмента", COLORS["violet"]),
        ("exits_outside", "вне АКБ", COLORS["blue"]),
    ]

    for col, label, color in positive_layers:
        values = seg[col].fillna(0)
        if float(values.abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=values,
                mode="lines",
                stackgroup="positive",
                line={"width": 0.8, "color": color},
                fillcolor=color,
                name=label,
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )

    for col, label, color in negative_layers:
        values = seg[col].fillna(0)
        if float(values.abs().sum()) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-values,
                mode="lines",
                stackgroup="negative",
                line={"width": 0.8, "color": color},
                fillcolor=color,
                name=label,
                customdata=values,
                hovertemplate="%{x}<br>" + label + ": %{customdata:,.0f}<extra></extra>",
            )
        )

    if float(seg["transfer_out"].fillna(0).abs().sum()) > 0:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=-seg["transfer_out"],
                mode="lines+markers",
                line={"color": COLORS["violet"], "width": 1.6},
                marker={"color": COLORS["violet"], "size": 5},
                showlegend=False,
                customdata=seg["transfer_out"],
                hovertemplate="%{x}<br>Переводы из сегмента: %{customdata:,.0f}<extra></extra>",
            )
        )

    if float(seg["closed_total"].fillna(0).abs().sum()) > 0:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg["closed_total"],
                mode="lines+markers",
                name="Закрытые",
                line={"color": COLORS["muted"], "width": 2, "dash": "dash"},
                hovertemplate="%{x}<br>Закрытые: %{y:,.0f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=seg["total_clients"],
            mode="lines+markers",
            name="Всего клиентов сегмента",
            line={"color": COLORS["ink"], "width": 2.5},
            hovertemplate="%{x}<br>Всего клиентов сегмента: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(xaxis={"type": "category"})
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title="Клиенты", zeroline=True, zerolinecolor="rgba(31,41,55,0.35)")
    return apply_fig_style(fig, f"{segment}: Состав базы по сегменту")


def fig_outflows(summary: pd.DataFrame, segment: str) -> go.Figure:
    seg = summary[summary["segment"] == segment].copy()
    x = month_point_series(seg["eomonth"])
    fig = go.Figure()
    for col, label, color in [
        ("transfer_out", "Переведены из сегмента", COLORS["violet"]),
        ("exits_inactive", "Выход или повторный выход", COLORS["rose"]),
        ("closed", "Закрытые или изначально закрытые", COLORS["muted"]),
    ]:
        fig.add_trace(
            go.Bar(
                x=x,
                y=seg[col],
                name=label,
                marker_color=color,
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=seg["net_client_change"],
            mode="lines+markers",
            name="Чистое изменение базы",
            line={"color": COLORS["ink"], "width": 2},
            yaxis="y2",
            hovertemplate="%{x}<br>Чистое изменение: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        yaxis2={"overlaying": "y", "side": "right", "title": "Чистое изменение"},
        xaxis={"type": "category"},
    )
    return apply_fig_style(fig, f"{segment}: Выбытия и чистое изменение")


def fig_turnover_lines(summary: pd.DataFrame, metric: str, title: str, y_title: str) -> go.Figure:
    labels = {
        "total_turnover_bn": "Общий месячный оборот",
        "turnover_per_client_bn": "Оборот на клиента",
        "total_turnover_y_bn": "Совокупный годовой оборот",
    }
    fig = go.Figure()
    for segment, color in [(KORP, COLORS["amber"]), (MSB, COLORS["blue"])]:
        seg = summary[summary["segment"] == segment]
        x = month_point_series(seg["eomonth"])
        fig.add_trace(
            go.Scatter(
                x=x,
                y=seg[metric],
                mode="lines+markers",
                name=segment,
                line={"color": color, "width": 3},
                hovertemplate="%{x}<br>"
                + labels[metric]
                + ": %{y:,.2f}<extra>"
                + segment
                + "</extra>",
            )
        )
    fig.update_yaxes(title=y_title)
    fig.update_xaxes(type="category")
    return apply_fig_style(fig, title)


def fig_credit_stack(df: pd.DataFrame, segment: str) -> go.Figure:
    counts, mean_credit = build_credit_trend(df, segment)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for cls in [1, 2, 3, 4, 5]:
        sub = counts[counts["credit_class"] == cls]
        fig.add_trace(
            go.Scatter(
                x=month_point_series(sub["eomonth"]),
                y=sub["share_pct"],
                mode="lines",
                stackgroup="one",
                name=f"class ({cls})",
                line={"width": 0.7, "color": CREDIT_COLORS[cls]},
                hovertemplate="%{x}<br>class ("
                + str(cls)
                + ": %{y:.2f}%<extra></extra>",
            ),
            secondary_y=False,
        )

    fig.add_trace(
        go.Scatter(
            x=month_point_series(mean_credit["eomonth"]),
            y=mean_credit["mean_credit_class"],
            mode="lines+markers",
            name="Средний class",
            line={"color": COLORS["ink"], "width": 2.8},
            hovertemplate="%{x}<br>Средний class: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=month_point_series(mean_credit["eomonth"]),
            y=mean_credit["npl_share"],
            mode="lines",
            name="Доля NPL",
            line={"color": COLORS["rose"], "width": 2, "dash": "dot"},
            hovertemplate="%{x}<br>Доля NPL: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.update_yaxes(title_text="Доля клиентов, %", secondary_y=False)
    fig.update_yaxes(title_text="Средний class", secondary_y=True)
    fig.update_xaxes(type="category")
    return apply_fig_style(fig, f"{segment}: Структура class и средний class")


def fig_credit_presence(df: pd.DataFrame, segment: str) -> go.Figure:
    summary = build_credit_presence_trend(df, segment)
    fig = go.Figure()
    color_map = {
        "С кредитом (class 1, 2, 3, 4, 5)": COLORS["blue"],
        "Без кредита (class 0)": COLORS["muted"],
    }
    for label in ["С кредитом (class 1, 2, 3, 4, 5)", "Без кредита (class 0)"]:
        sub = summary[summary["credit_presence"] == label]
        fig.add_trace(
            go.Bar(
                x=month_point_series(sub["eomonth"]),
                y=sub["clients"],
                name=label,
                marker_color=color_map[label],
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_yaxes(title="Клиенты")
    return apply_fig_style(fig, f"{segment}: С кредитом и без кредита")


def fig_metric_bars(metric_df: pd.DataFrame, left_label: str, right_label: str, title: str) -> go.Figure:
    plot_df = metric_df.melt(
        id_vars="Показатель",
        value_vars=[left_label, right_label],
        var_name="Когорта",
        value_name="Доля",
    )
    fig = px.bar(
        plot_df,
        x="Показатель",
        y="Доля",
        color="Когорта",
        barmode="group",
        color_discrete_map={left_label: COLORS["blue"], right_label: COLORS["amber"]},
    )
    fig.update_xaxes(categoryorder="array", categoryarray=metric_df["Показатель"].tolist())
    fig.update_yaxes(title="Доля, %")
    return apply_fig_style(fig, title)


def fig_metric_bars_count(metric_df: pd.DataFrame, left_label: str, right_label: str, title: str) -> go.Figure:
    plot_df = metric_df.melt(
        id_vars="Показатель",
        value_vars=[left_label, right_label],
        var_name="Серия",
        value_name="Клиенты",
    )
    fig = px.bar(
        plot_df,
        x="Показатель",
        y="Клиенты",
        color="Серия",
        barmode="group",
        color_discrete_map={left_label: COLORS["blue"], right_label: COLORS["amber"]},
    )
    fig.update_xaxes(categoryorder="array", categoryarray=metric_df["Показатель"].tolist())
    fig.update_yaxes(title="Клиенты")
    return apply_fig_style(fig, title)


def fig_metric_bars_count_horizontal(
    metric_df: pd.DataFrame, left_label: str, right_label: str, title: str
) -> go.Figure:
    plot_df = metric_df.melt(
        id_vars="Показатель",
        value_vars=[left_label, right_label],
        var_name="Серия",
        value_name="Клиенты",
    )
    fig = px.bar(
        plot_df,
        x="Клиенты",
        y="Показатель",
        color="Серия",
        orientation="h",
        barmode="group",
        color_discrete_map={left_label: COLORS["blue"], right_label: COLORS["amber"]},
    )
    return apply_fig_style(fig, title)


def fig_metric_dumbbell(
    metric_df: pd.DataFrame, left_label: str, right_label: str, title: str
) -> go.Figure:
    label_candidates = [
        col for col in metric_df.columns if col not in {left_label, right_label, "Разрыв"}
    ]
    label_col = label_candidates[0] if label_candidates else metric_df.columns[0]
    plot_df = metric_df.melt(
        id_vars=label_col,
        value_vars=[left_label, right_label],
        var_name="Серия",
        value_name="Значение",
    )
    fig = px.bar(
        plot_df,
        x="Значение",
        y=label_col,
        color="Серия",
        orientation="h",
        barmode="group",
        color_discrete_map={left_label: COLORS["blue"], right_label: COLORS["amber"]},
    )
    fig.update_xaxes(title="Доля, %")
    return apply_fig_style(fig, title)

def fig_metric_dumbbell(
    metric_df: pd.DataFrame, left_label: str, right_label: str, title: str
) -> go.Figure:
    label_candidates = [
        col for col in metric_df.columns if col not in {left_label, right_label, "??????"}
    ]
    label_col = label_candidates[0] if label_candidates else metric_df.columns[0]
    plot_df = metric_df[[label_col, left_label, right_label]].copy()

    line_x = []
    line_y = []
    for _, row in plot_df.iterrows():
        line_x.extend([row[left_label], row[right_label], None])
        line_y.extend([row[label_col], row[label_col], None])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line={"color": "#B2B3B3", "width": 1.2},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df[left_label],
            y=plot_df[label_col],
            mode="markers",
            name=left_label,
            marker={"color": COLORS["blue"], "size": 10},
            hovertemplate="%{y}<br>" + left_label + ": %{x:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df[right_label],
            y=plot_df[label_col],
            mode="markers",
            name=right_label,
            marker={"color": COLORS["amber"], "size": 10},
            hovertemplate="%{y}<br>" + right_label + ": %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_xaxes(title="????, %")
    fig.update_yaxes(categoryorder="array", categoryarray=list(plot_df[label_col])[::-1])
    return apply_fig_style(fig, title)


def fig_credit_mix(mix: pd.DataFrame, left_label: str, right_label: str, title: str) -> go.Figure:
    plot_df = mix.melt(
        id_vars="credit_class",
        value_vars=["Когорта перевода", "Удержанная когорта"],
        var_name="Когорта",
        value_name="Доля",
    )
    plot_df["Когорта"] = plot_df["Когорта"].map(
        {"Когорта перевода": left_label, "Удержанная когорта": right_label}
    )
    fig = px.bar(
        plot_df,
        x="credit_class",
        y="Доля",
        color="Когорта",
        barmode="group",
        color_discrete_map={left_label: COLORS["blue"], right_label: COLORS["amber"]},
    )
    fig.update_xaxes(title="class")
    fig.update_yaxes(title="Доля когорты, %")
    return apply_fig_style(fig, title)


def fig_credit_mix_counts_horizontal(mix: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    class_colors = {
        0: CREDIT_COLORS[0],
        1: CREDIT_COLORS[1],
        2: CREDIT_COLORS[2],
        3: CREDIT_COLORS[3],
        4: CREDIT_COLORS[4],
        5: CREDIT_COLORS[5],
    }
    for cls in [0, 1, 2, 3, 4, 5]:
        fig.add_trace(
            go.Bar(
                y=["КОРП→МСБ", "Остались в КОРП"],
                x=[int(mix.loc[mix["credit_class"] == cls, "КОРП→МСБ"].iloc[0]), int(mix.loc[mix["credit_class"] == cls, "Остались в КОРП"].iloc[0])],
                name=f"class ({cls})",
                orientation="h",
                marker_color=class_colors[cls],
                hovertemplate="%{y}<br>class (" + str(cls) + "): %{x:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Клиенты")
    fig.update_yaxes(title="")
    return apply_fig_style(fig, title)


def fig_h1_credit_class_dynamics(dynamics: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        subplot_titles=["КОРП→МСБ", "Остались в КОРП"],
        horizontal_spacing=0.08,
    )
    relative_order = list(range(-5, 6))
    tick_labels = [f"t{n}" if n < 0 else ("t" if n == 0 else f"t+{n}") for n in relative_order]
    for col_idx, cohort in enumerate(["КОРП→МСБ", "Остались в КОРП"], start=1):
        sub = dynamics[dynamics["cohort"] == cohort]
        for cls in [1, 2, 3, 4, 5]:
            cls_sub = sub[sub["credit_class"] == cls]
            x_labels = [f"t{n}" if n < 0 else ("t" if n == 0 else f"t+{n}") for n in cls_sub["relative_month"]]
            fig.add_trace(
                go.Bar(
                    x=x_labels,
                    y=cls_sub["share_pct"],
                    customdata=cls_sub[["clients"]].to_numpy(),
                    name=f"class ({cls})",
                    marker_color=CREDIT_COLORS[cls],
                    hovertemplate="%{x}<br>class ("
                    + str(cls)
                    + "): %{y:.2f}%<br>Клиенты: %{customdata[0]:,.0f}<extra></extra>",
                    showlegend=(col_idx == 1),
                ),
                row=1,
                col=col_idx,
            )
        fig.update_xaxes(categoryorder="array", categoryarray=tick_labels, row=1, col=col_idx, tickangle=-45)
    fig.update_yaxes(title_text="Доля, %", row=1, col=1)
    fig.update_layout(barmode="stack")
    return apply_fig_style(fig, "Динамика структуры class вокруг месяца перевода")


def fig_zero_share_comparison(zero_share_df: pd.DataFrame, title: str) -> go.Figure:
    cohort_col = "Когорта"
    zero_col = "Нулевой оборот, %"
    transfer_label = "КОРП→МСБ"
    retain_korp_label = "Остались в КОРП"
    retain_msb_label = "Остались в МСБ"
    legacy_transfer_label = "Когорта перевода"
    fig = px.bar(
        zero_share_df,
        x=cohort_col,
        y=zero_col,
        color=cohort_col,
        barmode="group",
        color_discrete_map={
            transfer_label: COLORS["blue"],
            retain_korp_label: COLORS["amber"],
            legacy_transfer_label: COLORS["blue"],
            retain_msb_label: COLORS["amber"],
        },
    )
    fig.update_yaxes(title=zero_col)
    fig.update_xaxes(title="")
    return apply_fig_style(fig, title)


def fig_numeric_box(left: pd.DataFrame, right: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    cohort_col = "Когорта"
    transfer_label = "Когорта перевода"
    retained_label = "Удержанная когорта"
    box = pd.concat(
        [
            left[[value_col]].assign(**{cohort_col: transfer_label}),
            right[[value_col]].assign(**{cohort_col: retained_label}),
        ],
        ignore_index=True,
    )
    fig = px.box(
        box,
        x=cohort_col,
        y=value_col,
        color=cohort_col,
        points="outliers",
        color_discrete_map={
            transfer_label: COLORS["blue"],
            retained_label: COLORS["amber"],
        },
    )
    fig.update_xaxes(title="")
    return apply_fig_style(fig, title)


def fig_numeric_box_split(
    left: pd.DataFrame, right: pd.DataFrame, value_col: str, left_label: str, right_label: str, title: str
) -> go.Figure:
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[left_label, right_label],
        shared_yaxes=False,
        horizontal_spacing=0.12,
    )
    series = [
        (left, left_label, COLORS["blue"], 1),
        (right, right_label, COLORS["amber"], 2),
    ]
    for frame, label, color, col_idx in series:
        fig.add_trace(
            go.Box(
                y=frame[value_col],
                name=label,
                marker_color=color,
                line={"color": color},
                boxpoints="outliers",
                jitter=0.25,
                pointpos=0,
                hovertemplate=label + "<br>%{y:,.2f}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=col_idx,
        )
        fig.update_xaxes(showticklabels=False, row=1, col=col_idx)
    return apply_fig_style(fig, title)


def fig_h1_numeric_dynamics(
    dynamics: pd.DataFrame,
    title: str,
    y_title: str,
    primary_range: list[float] | None = None,
    subplot_titles: tuple[str, str] | None = None,
) -> go.Figure:
    left_title = "\u041a\u041e\u0420\u041f\u2192\u041c\u0421\u0411"
    right_title = "\u041e\u0441\u0442\u0430\u043b\u0438\u0441\u044c \u0432 \u041a\u041e\u0420\u041f"

    cohort_values = dynamics["cohort"].astype(str).dropna().unique().tolist()
    left_key = cohort_values[0] if len(cohort_values) > 0 else left_title
    right_key = cohort_values[1] if len(cohort_values) > 1 else right_title

    effective_titles = [left_title, right_title] if subplot_titles is None else [subplot_titles[0], subplot_titles[1]]

    cohorts = [left_key] if len(cohort_values) == 1 else [left_key, right_key] if len(cohort_values) > 1 else []
    if not cohorts:
        fig = go.Figure()
        return apply_fig_style(fig, title)

    if len(cohorts) == 1:
        fig = make_subplots(
            rows=1,
            cols=1,
            shared_yaxes=False,
            specs=[[{"secondary_y": True}]],
        )
    else:
        fig = make_subplots(
            rows=1,
            cols=2,
            shared_yaxes=False,
            subplot_titles=effective_titles,
            horizontal_spacing=0.02,
            specs=[[{"secondary_y": True}, {"secondary_y": True}]],
        )

    tick_labels = [f"t{n}" if n < 0 else ("t" if n == 0 else f"t+{n}") for n in range(-6, 7)]
    cohort_colors = {left_key: COLORS["blue"], right_key: COLORS["amber"]}

    for col_idx, cohort in enumerate(cohorts, start=1):
        sub = dynamics[dynamics["cohort"].astype(str) == str(cohort)].copy()
        if sub.empty:
            continue
        sub = sub.sort_values("relative_month")
        sub["x_label"] = [f"t{n}" if n < 0 else ("t" if n == 0 else f"t+{n}") for n in sub["relative_month"]]
        color = cohort_colors[cohort]
        band_color = "rgba(25,63,114,0.12)" if col_idx == 1 else "rgba(215,181,109,0.20)"

        fig.add_trace(
            go.Scatter(
                x=sub["x_label"],
                y=sub["p75_nonzero"],
                mode="lines",
                line={"width": 0},
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=col_idx,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=sub["x_label"],
                y=sub["p25_nonzero"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=band_color,
                name="IQR \u0431\u0435\u0437 \u043d\u0443\u043b\u0435\u0439",
                hoverinfo="skip",
                showlegend=(col_idx == 1),
            ),
            row=1,
            col=col_idx,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=sub["x_label"],
                y=sub["median_nonzero"],
                mode="lines+markers",
                name="\u041c\u0435\u0434\u0438\u0430\u043d\u0430 \u0431\u0435\u0437 \u043d\u0443\u043b\u0435\u0439",
                line={"color": color, "width": 3},
                marker={"color": color, "size": 7},
                customdata=sub[["clients", "zero_share_pct"]],
                hovertemplate="%{x}<br>\u041c\u0435\u0434\u0438\u0430\u043d\u0430: %{y:,.2f}<br>\u041a\u043b\u0438\u0435\u043d\u0442\u044b: %{customdata[0]:,.0f}<br>\u0414\u043e\u043b\u044f \u043d\u0443\u043b\u0435\u0439: %{customdata[1]:.2f}%<extra></extra>",
                showlegend=(col_idx == 1),
            ),
            row=1,
            col=col_idx,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=sub["x_label"],
                y=sub["zero_share_pct"],
                mode="lines+markers",
                name="\u0414\u043e\u043b\u044f \u043d\u0443\u043b\u0435\u0439",
                line={"color": COLORS["muted"], "width": 2, "dash": "dot"},
                marker={"color": COLORS["muted"], "size": 6},
                hovertemplate="%{x}<br>\u0414\u043e\u043b\u044f \u043d\u0443\u043b\u0435\u0439: %{y:.2f}%<extra></extra>",
                showlegend=(col_idx == 1),
            ),
            row=1,
            col=col_idx,
            secondary_y=True,
        )
        fig.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=tick_labels,
            tickangle=-45,
            row=1,
            col=col_idx,
        )

    if primary_range is None:
        max_primary = float(
            dynamics[["p75_nonzero", "median_nonzero"]]
            .apply(pd.to_numeric, errors="coerce")
            .max()
            .max()
        ) if not dynamics.empty else 0.0
        upper = max_primary * 1.12 if max_primary > 0 else 1.0
        primary_range = [0, upper]

    fig.update_yaxes(title_text=y_title, range=primary_range, secondary_y=False, row=1, col=1)
    fig.update_yaxes(range=primary_range, secondary_y=False, row=1, col=2, title_text="")
    fig.update_yaxes(title_text="", range=[0, 100], showgrid=False, secondary_y=True, row=1, col=1, showticklabels=False)
    fig.update_yaxes(title_text="\u0414\u043e\u043b\u044f \u043d\u0443\u043b\u0435\u0439, %", range=[0, 100], showgrid=False, secondary_y=True, row=1, col=2)
    return apply_fig_style(fig, title)

def fig_korp_npl_status_monthly(df: pd.DataFrame) -> go.Figure:
    npl_label = "NPL в КОРП"
    to_pl_label = "Перешли в PL"
    transfer_label = "КОРП→МСБ"

    enriched = df.sort_values(["client_code", "eomonth"]).copy()
    group = enriched.groupby("client_code", sort=False)
    enriched["prev_month_id"] = group["month_id"].shift(1)
    enriched["prev_segment"] = group["segment"].shift(1)
    enriched["prev_credit_class"] = group["credit_class"].shift(1)

    months = pd.Index(sorted(enriched["eomonth"].dropna().unique()))
    consecutive_from_korp_npl = (
        enriched["prev_month_id"].eq(enriched["month_id"] - 1)
        & enriched["prev_segment"].eq(KORP)
        & enriched["prev_credit_class"].ge(3)
    )

    current_npl_counts = (
        enriched[(enriched["segment"] == KORP) & (enriched["credit_class"] >= 3)]
        .groupby("eomonth")["client_code"]
        .nunique()
        .reindex(months, fill_value=0)
    )
    to_pl_counts = (
        enriched[(enriched["credit_class"].isin([1, 2])) & consecutive_from_korp_npl]
        .groupby("eomonth")["client_code"]
        .nunique()
        .reindex(months, fill_value=0)
    )
    transfer_counts = (
        enriched[
            (enriched["segment"] == MSB)
            & (enriched["credit_class"] >= 3)
            & consecutive_from_korp_npl
        ]
        .groupby("eomonth")["client_code"]
        .nunique()
        .reindex(months, fill_value=0)
    )

    monthly = pd.DataFrame(
        {
            "month": months,
            npl_label: current_npl_counts.values,
            to_pl_label: to_pl_counts.values,
            transfer_label: transfer_counts.values,
        }
    )

    fig = go.Figure()
    color_map = {
        npl_label: "#898989",
        to_pl_label: "#149FA8",
        transfer_label: "#7688A1",
    }
    for label in [npl_label, to_pl_label, transfer_label]:
        fig.add_trace(
            go.Bar(
                x=month_point_series(monthly["month"]),
                y=monthly[label],
                name=label,
                marker_color=color_map[label],
                hovertemplate="%{x}<br>" + label + ": %{y:,.0f}<extra></extra>",
            )
        )

    fig.update_layout(barmode="stack")
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_yaxes(title="NPL клиенты")
    return apply_fig_style(fig, "NPL (class 3, 4, 5) в КОРП: переходы по месяцам")


def fig_client_lines(history: pd.DataFrame, cols: list[str], title: str) -> go.Figure:
    fig = go.Figure()
    color_map = {
        "turnover_bn": COLORS["blue"],
        "turnover_y_bn": COLORS["amber"],
        "credit_class": COLORS["violet"],
        "debt": COLORS["ink"],
    }
    label_map = {
        "turnover_bn": "\u041e\u0431\u043e\u0440\u043e\u0442",
        "turnover_y_bn": "\u0413\u043e\u0434\u043e\u0432\u043e\u0439 \u043e\u0431\u043e\u0440\u043e\u0442",
        "credit_class": "class",
        "debt": "\u0414\u043e\u043b\u0433",
    }
    for col in cols:
        fig.add_trace(
            go.Scatter(
                x=month_point_series(history["eomonth"]),
                y=history[col],
                mode="lines+markers",
                name=label_map.get(col, col),
                line={"color": color_map.get(col, COLORS["muted"]), "width": 3},
                hovertemplate="%{x}<br>" + label_map.get(col, col) + ": %{y:,.2f}<extra></extra>",
            )
        )
    fig.update_xaxes(type="category", tickangle=-45)
    return apply_fig_style(fig, title)


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p style="white-space: pre-line;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview(df: pd.DataFrame, h1: dict, h2: dict) -> None:
    render_hero(
        "Дашборд ресегментации",
        "Интерактивный обзор динамики базы, оборотов, кредитного качества и переводов между КОРП и МСБ.",
    )
    

    event_summary = build_segment_event_summary(df)
    turnover_summary = build_turnover_summary(df)
    latest_month = df["eomonth"].max()
    total_clients_latest = int(
        event_summary.loc[event_summary["eomonth"] == latest_month, "total_clients"].sum()
    )
    if "is_closed" in df.columns:
        initial_closed_mask = (
            pd.to_numeric(df["is_closed"], errors="coerce").fillna(0).eq(1)
            & (df["eomonth"] == df["eomonth"].min())
        )
    else:
        initial_closed_mask = pd.Series(False, index=df.index)
    initially_closed_clients = int(
        df.loc[initial_closed_mask, "client_code"].nunique()
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Изначально закрытые", f"{initially_closed_clients:,}")
    col2.metric("Клиенты сегментов", f"{total_clients_latest:,}")
    col3.metric("Переводы КОРП→МСБ", f"{int((df['status'] == K2M).sum()):,}")
    col4.metric("Переводы МСБ→КОРП", f"{int((df['status'] == M2K).sum()):,}")

    tab1, tab2, tab3 = st.tabs(["База и потоки", "Обороты", "Кредитное качество"])

    with tab1:
        st.subheader("Состав базы по сегментам")
        left, right = st.columns(2)
        with left:
            render_plot(fig_active_base(event_summary, KORP), "overview_active_korp")
        with right:
            render_plot(fig_active_base(event_summary, MSB), "overview_active_msb")


    with tab2:
        st.subheader("Обороты по сегментам")
        left, right = st.columns(2)
        with left:
            render_plot(
                fig_turnover_lines(
                    turnover_summary,
                    "total_turnover_bn",
                    "Общий месячный оборот",
                    "Оборот, млрд UZS",
                ),
                "overview_turnover_total",
            )
        with right:
            render_plot(
                fig_turnover_lines(
                    turnover_summary,
                    "total_turnover_y_bn",
                    "Годовой оборот по сегментам",
                    "Годовой оборот, млрд UZS",
                ),
                "overview_turnover_y_total",
            )

    with tab3:
        st.subheader("Структура кредитных классов")
        left, right = st.columns(2)
        with left:
            render_plot(fig_credit_stack(df, KORP), "overview_credit_korp")
        with right:
            render_plot(fig_credit_stack(df, MSB), "overview_credit_msb")
        st.subheader("Клиенты с кредитом и без кредита")
        left, right = st.columns(2)
        with left:
            render_plot(fig_credit_presence(df, KORP), "overview_credit_presence_korp")
        with right:
            render_plot(fig_credit_presence(df, MSB), "overview_credit_presence_msb")

    with st.expander("Краткая сводка по гипотезам", expanded=False):
        snapshot = pd.DataFrame(
            [
                {
                    "Наблюдение": "Гипотеза 1",
                    "Вывод": "Частично подтверждается",
                    "Почему": "Переведенные клиенты более стрессовые, чем в среднем удержанные в КОРП, но в основном уже не проходят формальное правило КОРП.",
                },
                {
                    "Наблюдение": "Гипотеза 2",
                    "Вывод": "Сильно подтверждается для слабых входов",
                    "Почему": "Слабые входы в КОРП быстро выбывают и часто передаются в МСБ.",
                },
                {
                    "Наблюдение": "Потенциал восстановления",
                    "Вывод": "Есть у части когорты перевода",
                    "Почему": "Рискованные переведенные клиенты улучшаются темпами, близкими к рискованным удержанным клиентам КОРП.",
                },
                {
                    "Наблюдение": "Гипотеза 3",
                    "Вывод": "Смотрите отдельную страницу",
                    "Почему": "Клиентов МСБ->КОРП можно сравнить с удержанными в МСБ, чтобы проверить, поднимают ли лучших клиентов системно.",
                },
            ]
        )
        st.dataframe(snapshot, width="stretch", hide_index=True)

def render_h1(df: pd.DataFrame) -> None:
    render_hero(
        "Гипотеза 1: КОРП переводит слабых клиентов в МСБ",
        "На этой странице сравнивается месяц перед переводом КОРП→МСБ с клиентами КОРП, которые оставались в КОРП в те же периоды.",
    )

    
    render_plot(fig_korp_npl_status_monthly(df), "h1_korp_npl_status")
    st.markdown(
        "<hr style='border:none;height:4px;background:#2B2A29;margin:1.25rem 0 1.5rem 0;opacity:0.9;'>",
        unsafe_allow_html=True,
    )
    available_months = sorted(
        get_pre_segment(df, KORP)
        .loc[lambda x: x["next_status"] == K2M, "next_eomonth"]
        .dropna()
        .unique()
        .tolist()
    )
    default_h1_months = [pd.Timestamp("2025-07-31")] if pd.Timestamp("2025-07-31") in available_months else available_months[:1]
    selected_months = st.multiselect(
        "Месяцы переводов",
        options=available_months,
        default=default_h1_months,
        format_func=lambda x: pd.Timestamp(x).date().isoformat(),
    )
    scope = st.radio(
        "Охват",
        options=[
            "Все клиенты",
            "Только клиенты, не проходящие правило КОРП",
            "Только клиенты, проходящие правило КОРП",
        ],
        horizontal=True,
        key="h1_scope",
    )

    transfer_pre, retain_pre = filter_transfer_view(
        df=df,
        source_segment=KORP,
        transfer_status=K2M,
        selected_months=selected_months,
        scope=scope,
        quality_only=False,
    )
    class_dynamics = build_h1_credit_class_dynamics(df, transfer_pre, retain_pre)
    metric_df = build_boolean_metric_table(
        transfer_pre,
        retain_pre,
        metrics=[
            ("Уже NPL (class 3, 4, 5)", "npl_now"),
            ("NPL в течение 3 месяцев", "npl_within_3m"),
            ("Годовой оборот ниже, чем 3 месяца назад", "turnover_y_decline_3m"),
        ],
        left_label="КОРП→МСБ",
        right_label="Остались в КОРП",
    )
    turnover_nonzero_transfer = transfer_pre[transfer_pre["turnover_y_bn"] > 0].copy()
    turnover_nonzero_retain = retain_pre[retain_pre["turnover_y_bn"] > 0].copy()
    zero_share_df = build_zero_share_comparison(
        transfer_pre, retain_pre, "turnover_y_bn", "КОРП→МСБ", "Остались в КОРП"
    )

    turnover_dynamics = build_h1_numeric_dynamics(df, transfer_pre, retain_pre, "turnover_bn")
    debt_dynamics = build_h1_numeric_dynamics(df, transfer_pre, retain_pre, "debt")

    col1, col2 = st.columns(2)
    col1.metric("КОРП→МСБ", f"{len(transfer_pre):,}")
    col2.metric("Остались в КОРП", f"{len(retain_pre):,}")
    st.caption("`Остались в КОРП` — это все записи за выбранные месяцы, где клиент в следующий eomonth остался в КОРП.")

    left, right = st.columns([1.1, 0.9])
    with left:
        st.caption("Сравнение ниже показывает, сколько клиентов имели каждый риск-признак в месяце `t-1`, то есть за месяц до события `t`.")
        render_plot(
            fig_metric_dumbbell(
                metric_df,
                "КОРП→МСБ",
                "Остались в КОРП",
                "Риск-профиль в t-1 перед переводом",
            ),
            "h1_metric_bars",
        )
    with right:
        st.caption("`До перевода` здесь означает месяц `t-1`: это запись перед месяцем `t`, в котором клиент переходит КОРП→МСБ.")
        if class_dynamics.empty:
            st.info("Для текущих фильтров недостаточно наблюдений, чтобы показать динамику class вокруг месяца перевода.")
        else:
            render_plot(fig_h1_credit_class_dynamics(class_dynamics), "h1_credit_mix")
    left, right = st.columns(2)
    with left:
        st.caption("\u0042\u006f\u0078\u0070\u006c\u006f\u0074 \u043d\u0438\u0436\u0435 \u0438\u0441\u043a\u043b\u044e\u0447\u0430\u0435\u0442 \u043d\u0443\u043b\u0435\u0432\u044b\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f `turnover_y_bn`, \u0430 \u043a\u043e\u0433\u043e\u0440\u0442\u044b \u0440\u0430\u0437\u0434\u0435\u043b\u0435\u043d\u044b \u043d\u0430 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0435 \u043e\u0441\u0438, \u0447\u0442\u043e\u0431\u044b \u0440\u0430\u0437\u0431\u0440\u043e\u0441 \u0447\u0438\u0442\u0430\u043b\u0441\u044f \u043b\u0443\u0447\u0448\u0435.")
        zero_share_transfer = (transfer_pre["turnover_bn"] == 0).mean() * 100 if len(transfer_pre) else 0
        zero_share_retain = (retain_pre["turnover_bn"] == 0).mean() * 100 if len(retain_pre) else 0
        metric_left, metric_right = st.columns(2)
        metric_left.metric("\u041d\u0443\u043b\u0435\u0432\u043e\u0439 \u0433\u043e\u0434\u043e\u0432\u043e\u0439 \u043e\u0431\u043e\u0440\u043e\u0442: \u041a\u041e\u0420\u041f\u2192\u041c\u0421\u0411", f"{zero_share_transfer:.1f}%")
        metric_right.metric("\u041d\u0443\u043b\u0435\u0432\u043e\u0439 \u0433\u043e\u0434\u043e\u0432\u043e\u0439 \u043e\u0431\u043e\u0440\u043e\u0442: \u041e\u0441\u0442\u0430\u043b\u0438\u0441\u044c \u0432 \u041a\u041e\u0420\u041f", f"{zero_share_retain:.1f}%")
        render_plot(
            fig_h1_numeric_dynamics(turnover_dynamics, "Динамика оборота вокруг месяца перевода", "Оборот, млрд. сум"),
            "h1_turnover_y_box",
        )
    with right:
        st.caption("\u0042\u006f\u0078\u0070\u006c\u006f\u0074 \u043d\u0438\u0436\u0435 \u0438\u0441\u043a\u043b\u044e\u0447\u0430\u0435\u0442 \u043d\u0443\u043b\u0435\u0432\u044b\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f `debt`, \u0430 \u0434\u043e\u043b\u044f \u043d\u0443\u043b\u0435\u0439 \u0432\u044b\u043d\u0435\u0441\u0435\u043d\u0430 \u0432 KPI \u043d\u0430\u0434 \u0433\u0440\u0430\u0444\u0438\u043a\u043e\u043c.")
        overdue_nonzero_transfer = transfer_pre[transfer_pre["debt"] > 0].copy()
        overdue_nonzero_retain = retain_pre[retain_pre["debt"] > 0].copy()
        overdue_zero_share_transfer = (transfer_pre["debt"] == 0).mean() * 100 if len(transfer_pre) else 0
        overdue_zero_share_retain = (retain_pre["debt"] == 0).mean() * 100 if len(retain_pre) else 0
        metric_left, metric_right = st.columns(2)
        metric_left.metric("\u0414\u043e\u043b\u044f \u0431\u0435\u0437 \u0434\u043e\u043b\u0433\u0430: \u041a\u041e\u0420\u041f\u2192\u041c\u0421\u0411", f"{overdue_zero_share_transfer:.1f}%")
        metric_right.metric("\u0414\u043e\u043b\u044f \u0431\u0435\u0437 \u0434\u043e\u043b\u0433\u0430: \u041e\u0441\u0442\u0430\u043b\u0438\u0441\u044c \u0432 \u041a\u041e\u0420\u041f", f"{overdue_zero_share_retain:.1f}%")
        render_plot(
            fig_h1_numeric_dynamics(debt_dynamics, "Динамика долга вокруг месяца перевода", "Долг, млрд. сум"),
            "h1_overdue_box",
        )



    st.subheader("Таблица показателей")
    st.dataframe(metric_df, width="stretch", hide_index=True)

    sample_cols = [
        "client_code",
        "eomonth",
        "next_eomonth",
        "credit_class",
        "debt",
        "turnover_bn",
        "turnover_y_bn",
        "corp_rule",
        "npl_within_3m",
    ]
    suspicious = transfer_pre.copy()
    suspicious = suspicious.sort_values(
        ["credit_class", "debt", "turnover_y_decline_3m", "turnover_y_bn"],
        ascending=[False, False, False, True],
    )

    st.subheader("Пример подозрительных переводов")
    st.caption(
        "Это записи до перевода, отсортированные в сторону худшего кредитного класса, большей просрочки и более слабого профиля оборота."
    )
    st.dataframe(suspicious[sample_cols].head(50), width="stretch", hide_index=True)



def render_h2(df: pd.DataFrame, h2: dict, outcomes: pd.DataFrame) -> None:
    render_hero(
        "Гипотеза 2: КОРП краткосрочно заводит посредственных клиентов",
        "На этой странице рассматриваются качество входов, выбытия зрелых когорт и различия между слабыми и устойчивыми входами в КОРП.",
    )

    
    st.markdown(
        """
        <div class="section-card">
            <p style="margin:0 0 0.35rem 0;font-weight:700;">Как определяются слабые клиенты</p>
            <p style="margin:0;">
                В текущей логике слабый клиент на входе в КОРП — это клиент, у которого одновременно:
                <code>turnover_y_bn &lt; 0.5</code>, <code>loan &lt; 0.5</code>, <code>is_group = 0</code> и <code>is_official = 0</code>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    entries = h2["entries"]

    quality = pd.DataFrame(h2["quality_rows"], columns=["Показатель", "Доля"])
    quality_label_map = {
        "Meets formal KORP rule": "Проходит формальное правило КОРП",
        "Group or official": "Группа или официальный клиент",
        "Turnover_y > 100": "Годовой оборот > 100",
        "Loan amount > 100": "Сумма кредита > 100",
        "Watchlist at entry (class 1-2)": "PL на входе (class 1, 2)",
        "Already NPL at entry": "Уже NPL на входе",
        "Any overdue at entry": "Есть просрочка на входе",
        "Weak at entry: zero turnover_y, zero loan, not group, not official": "Слабый на входе: turnover_y_bn < 0.5, loan < 0.5, не группа, не официальный",
    }
    quality["Показатель"] = quality["Показатель"].replace(quality_label_map)

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Входы в КОРП", f"{len(entries):,}")
    kpi2.metric("Проходят правило КОРП на входе", quality.loc[0, "Доля"])
    kpi3.metric("Группа или официал", quality.loc[1, "Доля"])

    kpi4, kpi5, kpi6 = st.columns(3)
    turnover_or_loan_over_100 = f"{to_percent((entries['turnover_y_bn'] > 100) | (entries['loan'] > 100)):.2f}%"
    kpi4.metric("Оборот или кредит >100", turnover_or_loan_over_100)
    kpi5.metric("Слабые на входе", quality.loc[7, "Доля"])
    kpi6.metric("NPL на входе", quality.loc[6, "Доля"])

    col_left, col_right = st.columns(2)
    with col_left:
        horizon = st.radio("Окно зрелости", options=[3, 6, 8], horizontal=True, key="h2_horizon")
    with col_right:
        weak_scope = st.radio(
            "Охват",
            options=[
                ("all", "Все входы"),
                ("to_msb", "Только переведенные в МСБ"),
                ("stay_korp", "Только оставшиеся в КОРП"),
            ],
            format_func=lambda x: x[1],
            horizontal=True,
            key="h2_scope",
        )[0]

    mature_summary = build_entry_month_summary(outcomes, horizon)
    mature_summary_display = mature_summary.rename(
        columns={
            "entry_date": "Месяц входа",
            "entries": "Входы",
            "left_within": "Выбыли в окне, %",
            "to_msb_within": "Переведены в МСБ в окне, %",
            "drop_within": "Выбыли или закрыты в окне, %",
            "weak_share": "Доля слабых на входе, %",
        }
    )

    render_plot(fig_entry_flow(mature_summary, horizon, weak_scope=weak_scope), "h2_entry_flow")

    mature = get_mature_entry_outcomes(outcomes, horizon)
    filtered_mature = mature.copy()
    if weak_scope == "to_msb":
        filtered_mature = mature[mature["to_msb_within"]].copy()
    elif weak_scope == "stay_korp":
        filtered_mature = mature[~mature["to_msb_within"]].copy()

    selected_client_codes = filtered_mature["client_code"].unique()

    transfer_pre = df[df["client_code"].isin(selected_client_codes) & (df["segment"] == KORP)].copy()
    retain_pre = pd.DataFrame(columns=["client_code", "next_month_id"])

    turnover_dynamics = build_h1_numeric_dynamics(df, transfer_pre, retain_pre, "turnover_bn")
    debt_dynamics = build_h1_numeric_dynamics(df, transfer_pre, retain_pre, "debt")

    scope_label = {
        "all": "Все входы",
        "to_msb": "Только переведены в МСБ",
        "stay_korp": "Только остались в КОРП",
    }[weak_scope]
    chart_suffix = f"{horizon} мес., {scope_label}"

    left, right = st.columns(2, gap="small")
    with left:
        render_plot(
            fig_h1_numeric_dynamics(
                turnover_dynamics,
                f"Динамика оборота вокруг месяца перевода ({chart_suffix})",
                "Оборот, млрд. сум",
                subplot_titles=("", ""),
            ),
            "h2_turnover_dynamics",
        )
    with right:
        render_plot(
            fig_h1_numeric_dynamics(
                debt_dynamics,
                f"Динамика долга вокруг месяца перевода ({chart_suffix})",
                "Долг, млрд. сум",
                subplot_titles=("", ""),
            ),
            "h2_debt_dynamics",
        )

    weak = filtered_mature[filtered_mature["weak"]].copy()
    non_weak = filtered_mature[~filtered_mature["weak"]].copy()

    weak_scope_label = {
        "all": "Все входы",
        "to_msb": "Только переведенные в МСБ",
        "stay_korp": "Только оставшиеся в КОРП",
    }[weak_scope]
    st.caption(f"Показаны значения для: {weak_scope_label}.")

    suspect_entries = entries[weak_client_mask(entries)].copy()
    suspect_entries = suspect_entries.sort_values(["eomonth", "client_code"])
    st.subheader("Пример слабых входов в КОРП")
    st.dataframe(
        suspect_entries[
            [
                "client_code",
                "eomonth",
                "status",
                "segment",
                "turnover_bn",
                "turnover_y_bn",
                "loan",
                "is_group",
                "is_official",
            ]
        ].head(50),
        width="stretch",
        hide_index=True,
    )


def render_h3(df: pd.DataFrame) -> None:
    render_hero(
        "Гипотеза 3: Хороших клиентов переводят из МСБ в КОРП",
        "На этой странице проверяется, выглядят ли клиенты МСБ→КОРП лучше, чем клиенты МСБ, которые оставались в МСБ в те же периоды.",
    )

    
    available_months = sorted(get_pre_segment(df, MSB)["next_eomonth"].dropna().unique().tolist())
    selected_months = st.multiselect(
        "Месяцы переводов",
        options=available_months,
        default=default_h1_months,
        format_func=lambda x: pd.Timestamp(x).date().isoformat(),
        key="h3_months",
    )
    scope = st.radio(
        "Охват",
        options=[
            "Все клиенты",
            "Только клиенты, не проходящие правило КОРП",
            "Только клиенты, проходящие правило КОРП",
        ],
        horizontal=True,
        key="h3_scope",
    )
    quality_only = st.toggle("Только чистые клиенты, готовые к апгрейду", value=False, key="h3_quality_only")

    transfer_pre, retain_pre = filter_transfer_view(
        df=df,
        source_segment=MSB,
        transfer_status=M2K,
        selected_months=selected_months,
        scope=scope,
        quality_only=quality_only,
    )

    if transfer_pre.empty or retain_pre.empty:
        st.warning("Текущие фильтры оставляют слишком мало клиентов для сравнения. Попробуйте расширить месяцы или сменить режим фильтра.")
        return

    metric_df = build_boolean_metric_table(
        transfer_pre,
        retain_pre,
        metrics=[
            ("Проходит формальное правило КОРП", "corp_rule"),
            ("Хороший кандидат на апгрейд", "good_upgrade_candidate"),
            ("Без кредита (class 0)", "clean_now"),
            ("Нет просроченной задолженности", "clean_now"),
            ("Не NPL (class 3, 4, 5)", "clean_now"),
            ("Группа или официальный клиент", "is_group_or_official"),
        ],
        left_label="Когорта перевода",
        right_label="Удержанные в МСБ",
    )
    metric_df.loc[3, "Когорта перевода"] = round(to_percent(~transfer_pre["has_debt_now"]), 2)
    metric_df.loc[3, "Удержанные в МСБ"] = round(to_percent(~retain_pre["has_debt_now"]), 2)
    metric_df.loc[3, "Разрыв"] = round(metric_df.loc[3, "Когорта перевода"] - metric_df.loc[3, "Удержанные в МСБ"], 2)
    metric_df.loc[4, "Когорта перевода"] = round(to_percent(~transfer_pre["npl_now"]), 2)
    metric_df.loc[4, "Удержанные в МСБ"] = round(to_percent(~retain_pre["npl_now"]), 2)
    metric_df.loc[4, "Разрыв"] = round(metric_df.loc[4, "Когорта перевода"] - metric_df.loc[4, "Удержанные в МСБ"], 2)

    transfer_rule_share = to_percent(transfer_pre["corp_rule"])
    retain_rule_share = to_percent(retain_pre["corp_rule"])
    transfer_good_share = to_percent(transfer_pre["good_upgrade_candidate"])
    retain_good_share = to_percent(retain_pre["good_upgrade_candidate"])
    transfer_clean_share = to_percent(transfer_pre["clean_now"])
    retain_clean_share = to_percent(retain_pre["clean_now"])
    transfer_no_overdue = to_percent(~transfer_pre["has_debt_now"])
    retain_no_overdue = to_percent(~retain_pre["has_debt_now"])
    transfer_not_npl = to_percent(~transfer_pre["npl_now"])
    retain_not_npl = to_percent(~retain_pre["npl_now"])
    turnover_y_median_transfer = float(transfer_pre["turnover_y_bn"].median())
    turnover_y_median_retain = float(retain_pre["turnover_y_bn"].median())
    turnover_y_median_gap = turnover_y_median_transfer - turnover_y_median_retain

    evidence_score = sum(
        [
            transfer_rule_share - retain_rule_share > 5,
            transfer_good_share - retain_good_share > 5,
            transfer_clean_share - retain_clean_share > 5,
            transfer_no_overdue - retain_no_overdue > 2,
            transfer_not_npl - retain_not_npl > 1,
            turnover_y_median_gap > 0,
        ]
    )
    if evidence_score >= 5:
        verdict = "Сильное подтверждение"
        verdict_text = "Отфильтрованная когорта `МСБ->КОРП` выглядит заметно лучше, чем удержанные в `МСБ`, по нескольким качественным признакам. Это поддерживает идею, что более сильных клиентов поднимают вверх."
    elif evidence_score >= 3:
        verdict = "Умеренное подтверждение"
        verdict_text = "Отфильтрованная когорта `МСБ->КОРП` выглядит лучше, чем удержанные в `МСБ`, по нескольким признакам, хотя сигнал не одинаково силен по всем метрикам."
    elif evidence_score >= 1:
        verdict = "Смешанные сигналы"
        verdict_text = "Есть признаки того, что лучшие клиенты переходят из `МСБ` в `КОРП`, но при текущих фильтрах картина недостаточно чистая, чтобы назвать это сильным эффектом отбора."
    else:
        verdict = "Слабое подтверждение"
        verdict_text = "При текущих фильтрах когорта `МСБ->КОРП` не выглядит явно лучше, чем удержанные в `МСБ`, поэтому гипотеза подтверждается слабо."

    st.subheader("Оперативный вывод")
    st.markdown(
        f"""
        **Вердикт:** {verdict}  
        {verdict_text}
        """.strip()
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Когорта МСБ→КОРП", f"{len(transfer_pre):,}")
    col2.metric("Удержанные в МСБ", f"{len(retain_pre):,}")
    col3.metric("Разрыв по правилу КОРП", f"{metric_df.loc[0, 'Разрыв']:.2f} п.п.")
    col4.metric("Разрыв по чистому кредиту", f"{metric_df.loc[2, 'Разрыв']:.2f} п.п.")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(
        "Проходят правило КОРП",
        f"{transfer_rule_share:.2f}%",
        delta=f"{transfer_rule_share - retain_rule_share:.2f} п.п. к удержанным в МСБ",
    )
    kpi2.metric(
        "Хороший кандидат на апгрейд",
        f"{transfer_good_share:.2f}%",
        delta=f"{transfer_good_share - retain_good_share:.2f} п.п. к удержанным в МСБ",
    )
    kpi3.metric(
        "Без просроченной задолженности",
        f"{transfer_no_overdue:.2f}%",
        delta=f"{transfer_no_overdue - retain_no_overdue:.2f} п.п. к удержанным в МСБ",
    )
    kpi4.metric(
        "Медиана turnover_y_bn",
        f"{turnover_y_median_transfer:.2f}",
        delta=f"{turnover_y_median_gap:.2f} к удержанным в МСБ",
    )

    with st.expander("Почему присвоен такой вердикт", expanded=False):
        evidence = pd.DataFrame(
            [
                {
                    "Сигнал": "Проходит формальное правило КОРП",
                    "МСБ→КОРП": round(transfer_rule_share, 2),
                    "Удержанные в МСБ": round(retain_rule_share, 2),
                    "Разрыв": round(transfer_rule_share - retain_rule_share, 2),
                },
                {
                    "Сигнал": "Хороший кандидат на апгрейд",
                    "МСБ→КОРП": round(transfer_good_share, 2),
                    "Удержанные в МСБ": round(retain_good_share, 2),
                    "Разрыв": round(transfer_good_share - retain_good_share, 2),
                },
                {
                    "Сигнал": "Без кредита (class 0)",
                    "МСБ→КОРП": round(transfer_clean_share, 2),
                    "Удержанные в МСБ": round(retain_clean_share, 2),
                    "Разрыв": round(transfer_clean_share - retain_clean_share, 2),
                },
                {
                    "Сигнал": "Без просроченной задолженности",
                    "МСБ→КОРП": round(transfer_no_overdue, 2),
                    "Удержанные в МСБ": round(retain_no_overdue, 2),
                    "Разрыв": round(transfer_no_overdue - retain_no_overdue, 2),
                },
                {
                    "Сигнал": "Не NPL (class 3, 4, 5)",
                    "МСБ→КОРП": round(transfer_not_npl, 2),
                    "Удержанные в МСБ": round(retain_not_npl, 2),
                    "Разрыв": round(transfer_not_npl - retain_not_npl, 2),
                },
                {
                    "Сигнал": "Медиана turnover_y_bn",
                    "МСБ→КОРП": round(turnover_y_median_transfer, 2),
                    "Удержанные в МСБ": round(turnover_y_median_retain, 2),
                    "Разрыв": round(turnover_y_median_gap, 2),
                },
            ]
        )
        st.dataframe(evidence, width="stretch", hide_index=True)

    left, right = st.columns([1.1, 0.9])
    with left:
        render_plot(
            fig_metric_bars(metric_df, "Когорта перевода", "Удержанные в МСБ", "Сравнение качества МСБ→КОРП"),
            "h3_metric_bars",
        )
    with right:
        render_plot(
            fig_credit_mix(
                build_credit_mix(transfer_pre, retain_pre),
                "МСБ→КОРП",
                "Удержанные в МСБ",
                "Структура кредитных классов до апгрейда",
            ),
            "h3_credit_mix",
        )

    left, right = st.columns(2)
    with left:
        render_plot(
            fig_numeric_box(transfer_pre, retain_pre, "turnover_y_bn", "Распределение годового оборота"),
            "h3_turnover_y_box",
        )
    with right:
        render_plot(
            fig_numeric_box(transfer_pre, retain_pre, "turnover_bn", "Распределение месячного оборота"),
            "h3_turnover_box",
        )

    st.subheader("Таблица показателей")
    st.dataframe(metric_df, width="stretch", hide_index=True)

    good_sample = transfer_pre.sort_values(
        ["good_upgrade_candidate", "corp_rule", "turnover_y_bn", "credit_class"],
        ascending=[False, False, False, True],
    )
    st.subheader("Пример сильных переводов МСБ→КОРП")
    st.dataframe(
        good_sample[
            [
                "client_code",
                "eomonth",
                "next_eomonth",
                "turnover_bn",
                "turnover_y_bn",
                "credit_class",
                "debt",
                "loan",
                "corp_rule",
                "is_group_or_official",
                "good_upgrade_candidate",
            ]
        ].head(50),
        width="stretch",
        hide_index=True,
    )


def render_h3_refactored(df: pd.DataFrame) -> None:
    render_hero(
        "Гипотеза 3: Неподходящих клиентов переводят из МСБ в КОРП",
        "Переводят ли из МСБ в КОРП клиентов:\n- которые не проходят формальное правило КОРП\n- среди которых преобладают PL-клиенты с низким долгом",
    )

    msb_pre = get_pre_segment(df, MSB).copy()
    transfer_months = sorted(
        msb_pre.loc[msb_pre["next_status"] == M2K, "next_eomonth"].dropna().unique().tolist()
    )
    july_2025 = pd.Timestamp("2025-07-31")
    default_months = [july_2025] if july_2025 in transfer_months else transfer_months[:1]

    selected_months = st.multiselect(
        "Месяцы переводов",
        options=transfer_months,
        default=default_months,
        format_func=month_point_label,
        key="h3_months_refactored",
    )

    if not selected_months:
        st.warning("Выберите хотя бы один месяц перевода.")
        return

    pre = msb_pre[msb_pre["next_eomonth"].isin(selected_months)].copy()
    pre["non_compliant_korp_rule"] = (
        (pre["turnover_y_bn"] < 100)
        & (pre["loan"] < 100)
        & (pre["is_group"] == 0)
        & (pre["is_official"] == 0)
    )
    pre["pl_now"] = pre["credit_class"].isin([1, 2])
    pre["npl_now"] = pre["credit_class"].isin([3, 4, 5])
    pre["low_debt"] = pre["debt"] < 100
    pre["both_pl_low_debt"] = pre["pl_now"] & pre["low_debt"]

    transfer_all = pre[pre["next_status"] == M2K].copy()
    retain_all = pre[pre["next_segment"] == MSB].copy()
    transfer_non_rule = transfer_all[transfer_all["non_compliant_korp_rule"]].copy()
    retain_non_rule = retain_all[retain_all["non_compliant_korp_rule"]].copy()

    if transfer_all.empty:
        st.warning("В выбранных месяцах нет переводов МСБ→КОРП.")
        return

    if transfer_non_rule.empty:
                return

    transfer_share_non_rule = to_percent(transfer_all["non_compliant_korp_rule"])
    retain_share_non_rule = to_percent(retain_all["non_compliant_korp_rule"]) if not retain_all.empty else 0.0
    pl_share_transfer = to_percent(transfer_non_rule["pl_now"])
    pl_share_retain = to_percent(retain_non_rule["pl_now"]) if not retain_non_rule.empty else 0.0
    low_debt_share_transfer = to_percent(transfer_non_rule["low_debt"])
    low_debt_share_retain = to_percent(retain_non_rule["low_debt"]) if not retain_non_rule.empty else 0.0
    both_share_transfer = to_percent(transfer_non_rule["both_pl_low_debt"])
    both_share_retain = to_percent(retain_non_rule["both_pl_low_debt"]) if not retain_non_rule.empty else 0.0
    non_npl_transfer = to_percent(~transfer_non_rule["npl_now"])
    non_npl_retain = to_percent(~retain_non_rule["npl_now"]) if not retain_non_rule.empty else 0.0
    npl_share_transfer = to_percent(transfer_non_rule["npl_now"])
    credit_share_transfer = to_percent(transfer_non_rule["credit_class"] > 0)
    median_debt_transfer = float(transfer_non_rule["debt"].median())
    median_debt_retain = float(retain_non_rule["debt"].median()) if not retain_non_rule.empty else 0.0

    if pl_share_transfer >= 50 and low_debt_share_transfer >= 50:
        conclusion = "Да: среди переводов МСБ→КОРП есть заметная доля клиентов, не проходящих правило КОРП, и в этой когорте большинство выглядит как PL-клиенты с низким долгом."
    elif pl_share_transfer >= 50 or low_debt_share_transfer >= 50:
        conclusion = "Частично: переводы МСБ→КОРП среди неподходящих клиентов есть, но большинство видно только по одному из двух сигналов: либо PL, либо низкий долг."
    else:
        conclusion = "Скорее нет: неподходящие клиенты действительно переводятся МСБ→КОРП, но среди них не видно явного большинства PL-клиентов с низким долгом."

    
    st.markdown(
        """
        <div class="section-card">
        <strong>Как считать.</strong><br>
        На месяце <code>t</code> клиент еще находится в <code>МСБ</code>. Мы смотрим, переводится ли он в
        <code>КОРП</code> в следующий месяц, и оцениваем его профиль по признакам на месяце <code>t</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Все переводы МСБ→КОРП", f"{len(transfer_all):,}")
    col2.metric("Не проходят правило КОРП", f"{len(transfer_non_rule):,}")
    col3.metric("Доля NPL", f"{npl_share_transfer:.2f}%")
    col4.metric("Доля клиентов с кредитами", f"{credit_share_transfer:.2f}%")

    st.caption(f"{transfer_share_non_rule:.2f}% от переводов не проходят правило КОРП")

    metric_df = pd.DataFrame(
        [
            {"Показатель": "Все переводы МСБ→КОРП", "Значение": len(transfer_all)},
            {"Показатель": "Не проходят правило КОРП", "Значение": len(transfer_non_rule)},
            {"Показатель": "Доля NPL", "Значение": round(npl_share_transfer, 2)},
            {"Показатель": "Доля клиентов с кредитами", "Значение": round(credit_share_transfer, 2)},
        ]
    )

    sample = transfer_non_rule.sort_values(
        ["pl_now", "low_debt", "debt", "turnover_y_bn"],
        ascending=[False, False, True, False],
    )
    st.subheader("Примеры неподходящих клиентов, переведенных МСБ→КОРП")
    st.dataframe(
        sample[
            [
                "client_code",
                "eomonth",
                "next_eomonth",
                "turnover_bn",
                "turnover_y_bn",
                "loan",
                "debt",
                "credit_class",
                "pl_now",
                "low_debt",
                "non_compliant_korp_rule",
            ]
        ].head(50),
        width="stretch",
        hide_index=True,
    )
    return


def render_client_explorer(df: pd.DataFrame) -> None:
    df = df.copy()
    df["client_code_display"] = df["client_code"].astype(str).str.zfill(8)
    df = df.sort_values(["client_code", "eomonth"]).copy()

    render_hero(
        "Карточка клиента",
        "Просмотр одного клиента по всем месячным срезам с быстрым доступом к переведенным и подозрительным когортам.",
    )

    weak_entry_codes = (
        df.loc[
            ((df["segment"] == KORP) & df["is_entry_event"] & weak_client_mask(df)),
            "client_code_display",
        ]
        .drop_duplicates()
        .tolist()
    )
    all_codes = df["client_code_display"].drop_duplicates().tolist()

    npl_after_transfer_codes = []
    for client_code, grp in df.groupby("client_code_display", sort=False):
        transfer_months = grp.loc[grp["status"] == K2M, "month_id"]
        if transfer_months.empty:
            continue
        first_transfer_month = transfer_months.min()
        if grp.loc[grp["month_id"] > first_transfer_month, "credit_class"].ge(3).any():
            npl_after_transfer_codes.append(client_code)

    cohort = st.selectbox(
        "Выбор когорты",
        options=[
            "Клиенты, ставшие NPL после КОРП->МСБ",
            "Клиенты КОРП, перешедшие в МСБ в течение x мес. после входа",
            "Слабые входы в КОРП",
            "Все клиенты",
        ],
        label_visibility="collapsed",
    )
    entry_to_msb_horizon = None
    if cohort == "Клиенты КОРП, перешедшие в МСБ в течение x мес. после входа":
        entry_to_msb_horizon = st.radio(
            "Окно после входа, мес.",
            options=[3, 6, 8, 12],
            horizontal=True,
            key="client_entry_to_msb_horizon",
        )

    if cohort == "Клиенты, ставшие NPL после КОРП->МСБ":
        pool = npl_after_transfer_codes
    elif cohort == "Клиенты КОРП, перешедшие в МСБ в течение x мес. после входа":
        pool = []
        entry_rows = df[(df["segment"] == KORP) & df["is_entry_event"]].copy()
        for client_code, grp in entry_rows.groupby("client_code_display", sort=False):
            client_history = df[df["client_code_display"] == client_code]
            matched = False
            for _, entry_row in grp.iterrows():
                month_diff = client_history["month_id"] - entry_row["month_id"]
                moved_mask = (
                    (client_history["status"] == K2M)
                    & month_diff.ge(1)
                    & month_diff.le(entry_to_msb_horizon)
                )
                if moved_mask.any():
                    matched = True
                    break
            if matched:
                pool.append(client_code)
    elif cohort == "Слабые входы в КОРП":
        pool = weak_entry_codes
    else:
        pool = all_codes

    pool_df = (
        df[df["client_code_display"].isin(pool)]
        .sort_values(["client_code", "eomonth"])
        .groupby("client_code", as_index=False)
        .tail(1)
        .copy()
    )
    if not pool_df.empty:
        pool_history_df = df[df["client_code_display"].isin(pool)].copy()
        filter_code, filter_segment, filter_status, filter_rule = st.columns(4)
        code_query = filter_code.text_input(
            "Фильтр: Код клиента",
            value="",
            key="client_pool_code_filter",
        ).strip()
        segment_options = sorted(pool_df["segment"].dropna().astype(str).unique().tolist())
        selected_segments = filter_segment.multiselect(
            "Фильтр: Сегмент",
            options=segment_options,
            default=[],
            key="client_pool_segment_filter",
        )
        status_options = sorted(pool_history_df["status"].dropna().map(format_status_label).astype(str).unique().tolist())
        selected_statuses = filter_status.multiselect(
            "Фильтр: Статус",
            options=status_options,
            default=[],
            key="client_pool_status_filter",
        )
        corp_rule_choice = filter_rule.selectbox(
            "Фильтр: Правило КОРП",
            options=["Все", "Да", "Нет"],
            index=0,
            key="client_pool_rule_filter",
        )

        filter_month, filter_class, filter_turnover, filter_debt = st.columns(4)
        month_options = sorted(pool_df["eomonth"].dropna().unique().tolist())
        selected_months = filter_month.multiselect(
            "Фильтр: Последний месяц",
            options=month_options,
            default=[],
            format_func=lambda x: pd.Timestamp(x).date().isoformat(),
            key="client_pool_month_filter",
        )
        class_options = sorted(pd.to_numeric(pool_df["credit_class"], errors="coerce").dropna().astype(int).unique().tolist())
        selected_classes = filter_class.multiselect(
            "Фильтр: class",
            options=class_options,
            default=[],
            key="client_pool_class_filter",
        )
        turnover_y_max = float(pd.to_numeric(pool_df["turnover_y_bn"], errors="coerce").fillna(0).max())
        turnover_y_range = build_range_slider(
            filter_turnover,
            "Фильтр: Годовой оборот",
            0.0,
            max(turnover_y_max, 0.0),
            key="client_pool_turnover_y_filter",
        )
        debt_max = float(pd.to_numeric(pool_df["debt"], errors="coerce").fillna(0).max())
        debt_range = build_range_slider(
            filter_debt,
            "Фильтр: Долг",
            0.0,
            max(debt_max, 0.0),
            key="client_pool_debt_filter",
        )

        filtered_pool_df = pool_history_df.copy() if code_query else pool_df.copy()
        if code_query:
            filtered_pool_df = filtered_pool_df[
                filtered_pool_df["client_code_display"].astype(str).str.contains(code_query, case=False, na=False)
            ]
        if selected_segments:
            filtered_pool_df = filtered_pool_df[filtered_pool_df["segment"].astype(str).isin(selected_segments)]
        if selected_statuses:
            matched_codes = pool_history_df.loc[
                pool_history_df["status"].map(format_status_label).astype(str).isin(selected_statuses),
                "client_code_display",
            ].drop_duplicates()
            filtered_pool_df = filtered_pool_df[
                filtered_pool_df["client_code_display"].isin(matched_codes)
            ]
        if corp_rule_choice != "Все":
            rule_value = corp_rule_choice == "Да"
            filtered_pool_df = filtered_pool_df[filtered_pool_df["corp_rule"].astype(bool) == rule_value]
        if selected_months:
            selected_months_set = {pd.Timestamp(m) for m in selected_months}
            filtered_pool_df = filtered_pool_df[
                filtered_pool_df["eomonth"].map(pd.Timestamp).isin(selected_months_set)
            ]
        if selected_classes:
            filtered_pool_df = filtered_pool_df[
                pd.to_numeric(filtered_pool_df["credit_class"], errors="coerce").fillna(-1).astype(int).isin(selected_classes)
            ]
        filtered_pool_df = filtered_pool_df[
            pd.to_numeric(filtered_pool_df["turnover_y_bn"], errors="coerce").fillna(0).between(*turnover_y_range)
        ]
        filtered_pool_df = filtered_pool_df[
            pd.to_numeric(filtered_pool_df["debt"], errors="coerce").fillna(0).between(*debt_range)
        ]

        st.caption(f"После фильтров: {filtered_pool_df['client_code_display'].nunique():,} клиентов")

        pool_df = filtered_pool_df[
            [
                "client_code_display",
                "eomonth",
                "segment",
                "status",
                "turnover_bn",
                "turnover_y_bn",
                "credit_class",
                "debt",
                "loan",
                "corp_rule",
                "is_group",
                "is_official",
            ]
        ].copy()
        pool_df["status"] = pool_df["status"].map(format_status_label)
        pool_df = pool_df.rename(
            columns={
                "client_code_display": "Код клиента",
                "eomonth": "Последний месяц",
                "segment": "Сегмент",
                "status": "Статус",
                "turnover_bn": "Оборот",
                "turnover_y_bn": "Годовой оборот",
                "credit_class": "class",
                "debt": "Долг",
                "loan": "Сумма кредита",
                "corp_rule": "Проходит правило КОРП",
                "is_group": "is_group",
                "is_official": "is_official",
            }
        )
        st.dataframe(pool_df, width="stretch", hide_index=True)

    # Aggregate graphs for filtered clients
    if not filtered_pool_df.empty:
        st.subheader("Агрегированные графики по фильтрованным клиентам")

        # Group by eomonth and compute averages
        agg_df = filtered_pool_df.groupby("eomonth").agg({
            "turnover_bn": "mean",
            "turnover_y_bn": "mean",
            "credit_class": mean_credit_class_nonzero,
            "debt": "mean"
        }).reset_index()

        left, right = st.columns(2)
        with left:
            render_plot(
                fig_client_lines(agg_df, ["turnover_bn", "turnover_y_bn"], "Средние обороты по фильтрованным клиентам"),
                "filtered_turnover",
            )
        with right:
            render_plot(
                fig_client_lines(agg_df, ["credit_class", "debt"], "Средний класс и долг по фильтрованным клиентам"),
                "filtered_credit",
            )

    default_code = "04694951"
    client_code = st.text_input("Код клиента", value=default_code).strip().zfill(8)

    history = df[df["client_code_display"] == client_code].copy()
    if history.empty:
        st.warning("Клиент с таким кодом не найден в df_all.csv.")
        return

    history = history.sort_values("eomonth")
    latest = history.iloc[-1]

    left, right = st.columns(2)
    with left:
        render_plot(
            fig_client_lines(history, ["turnover_bn", "turnover_y_bn"], "История оборотов"),
            "client_turnover",
        )
    with right:
        render_plot(
            fig_client_lines(history, ["credit_class", "debt"], "\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u043a\u0440\u0435\u0434\u0438\u0442\u0430 \u0438 \u0434\u043e\u043b\u0433\u0430"),
            "client_credit",
        )

    display = history[
        [
            "eomonth",
            "segment",
            "status",
            "turnover_bn",
            "turnover_y_bn",
            "credit_class",
            "debt",
            "loan",
            "corp_rule",
            "is_group",
            "is_official",
        ]
    ].copy()
    display["status"] = display["status"].map(format_status_label)
    st.subheader("Полная месячная история")
    st.dataframe(display, width="stretch", hide_index=True)



def render_segmentation_criteria() -> None:
    render_hero(
        "Критерии сегментации",
        "Справочная страница с правилами и порогами, которые используются при отнесении клиентов к сегментам банка.",
    )

    st.markdown(
        """
        <div class="section-card">
        <strong>Критерии отнесения к сегменту</strong>
        <ul style="margin:0.6rem 0 0 1.2rem;">
            <li>Кредитовый оборот за последний календарный год. Допускается использование выручки клиента за последний финансовый год либо неочищенных кредитовых оборотов при отсутствии очищенного кредитового оборота.</li>
            <li>Принадлежность к группе компаний корпоративного сегмента либо к международным компаниям.</li>
            <li>Наличие кредита или кредитной заявки по сумме договора.</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    criteria_df = pd.DataFrame(
        [
            {
                "Критерии": "Классификация бизнеса по годовому кредитовому обороту либо выручке компании",
                "Микро": "до 1 млрд. сум",
                "Малый": "1 - 10 млрд. сум (не включительно)",
                "Средний": "10 - 130 млрд. сум (не включительно)",
                "Корпоративный": "130 млрд. сум и более",
            },
            {
                "Критерии": "Наличие кредита либо кредитной заявки по сумме договора",
                "Микро": "до 1 млрд. сум",
                "Малый": "1 - 10 млрд. сум (не включительно)",
                "Средний": "10 - 130 млрд. сум (не включительно)",
                "Корпоративный": "130 млрд. сум и более",
            },
        ]
    )

    st.subheader("Пороговые значения по сегментам")
    st.dataframe(criteria_df, width="stretch", hide_index=True)

    st.markdown(
        """
        <div class="section-card">
        <strong>Дополнительные правила</strong>
        <ol style="margin:0.6rem 0 0 1.2rem;">
            <li>Если компания ведёт деятельность менее одного календарного года, годовой кредитовый оборот пересчитывается пропорционально фактическому периоду деятельности.</li>
            <li>Индивидуальные предприниматели относятся к сегменту «Микро».</li>
            <li>Если в группе компаний хотя бы одна компания относится к Корпоративному сегменту, вся группа сегментируется как корпоративная.</li>
            <li>Центральные аппараты министерств, посольства и организации с дипломатическим статусом относятся к Корпоративному сегменту.</li>
            <li>Компании с долей иностранного владения более 50%, привлечённые ДКСИ, относятся к Корпоративному сегменту.</li>
            <li style="color:#c0392b;font-weight:700;">Постоянные учреждения и представительства, привлечённые ДКСИ, относятся к Корпоративному сегменту.</li>
            <li style="color:#c0392b;font-weight:700;">Клиенты с качеством кредитного портфеля «неудовлетворительный», «сомнительный» или «безнадёжный» не закрепляются за клиентскими менеджерами для обслуживания.</li>
            <li>Актуализация набора критериев проводится по инициативе ДКСИ или клиентских подразделений при согласовании.</li>
            <li>Плановая пересегментация клиентов осуществляется два раза в год: на 1 июля и на 1 января.</li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

def main() -> None:
    inject_styles()
    df, h1, h2, _improvement, outcomes = get_analysis_bundle()

    with st.sidebar:
        st.markdown("## Навигация")
        page = st.radio(
            "Открыть страницу",
            options=[
                "Обзор",
                "Гипотеза 1",
                "Гипотеза 2",
                "Гипотеза 3",
                "Критерии сегментации",
                "Клиенты",
            ],
            key="main_page",
        )
        st.markdown("---")
        st.markdown("## Примечания")
        st.caption("Правило КОРП: группа или официальный клиент, либо годовой оборот > 100, либо сумма кредита > 100.")
        st.caption("PL: class (1, 2). NPL: class (3, 4, 5).")
        st.caption("Для всех основных графиков используется Plotly.")
        st.dataframe(credit_class_reference_table(), width="stretch", hide_index=True)

    if page == "Обзор":
        render_overview(df, h1, h2)
    elif page == "Гипотеза 1":
        render_h1(df)
    elif page == "Гипотеза 2":
        render_h2(df, h2, outcomes)
    elif page == "Гипотеза 3":
        render_h3_refactored(df)
    elif page == "Критерии сегментации":
        render_segmentation_criteria()
    elif page == "Клиенты":
        render_client_explorer(df)


if __name__ == "__main__":
    main()
