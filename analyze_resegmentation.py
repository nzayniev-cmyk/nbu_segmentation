from pathlib import Path

import numpy as np


# Patch deprecated NumPy aliases so the local pandas install can import.
for _old, _new in [
    ("bool", np.bool_),
    ("complex", np.complex128),
    ("object", np.object_),
    ("int", np.int_),
    ("float", np.float64),
]:
    setattr(np, _old, _new)

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "df_all.csv"
REPORT_FILE = BASE_DIR / "resegmentation_analysis_report.md"

MSB = "\u041c\u0421\u0411"
KORP = "\u041a\u041e\u0420\u041f"
K2M = f"{KORP}->{MSB}"
M2K = f"{MSB}->{KORP}"
ENTRY_STATUSES = {"entry", "re_entry"}
EXIT_STATUSES = {"exit_ahd", "re_exit_ahd"}


def infer_segment_mapping(df: pd.DataFrame) -> dict[str, str]:
    raw_segments = [str(value) for value in df["segment"].dropna().astype(str).unique()]
    if set(raw_segments) >= {KORP, MSB}:
        return {KORP: KORP, MSB: MSB}

    # Prefer explicit transfer labels like "<seg_a>-><seg_b>" when present.
    transfer_pairs = []
    for status in df["status"].dropna().astype(str).unique():
        if "->" in status:
            left, right = [part.strip() for part in status.split("->", 1)]
            transfer_pairs.append((left, right))
    for left, right in transfer_pairs:
        if left in raw_segments and right in raw_segments and left != right:
            # Infer KORP/MSB by the conventional 4-letter vs 3-letter segment names.
            if len(left) == 4 and len(right) == 3:
                return {left: KORP, right: MSB}
            if len(left) == 3 and len(right) == 4:
                return {right: KORP, left: MSB}

    if len(raw_segments) == 2:
        ordered = sorted(raw_segments, key=len, reverse=True)
        return {ordered[0]: KORP, ordered[1]: MSB}

    return {value: value for value in raw_segments}


def is_entry_event(series: pd.Series) -> pd.Series:
    return series.astype(str).isin(ENTRY_STATUSES)


def is_exit_event(series: pd.Series) -> pd.Series:
    return series.astype(str).isin(EXIT_STATUSES)


def is_transfer_k2m(series: pd.Series) -> pd.Series:
    return series.astype(str) == K2M


def is_transfer_m2k(series: pd.Series) -> pd.Series:
    return series.astype(str) == M2K


def is_segment_entry_event(df: pd.DataFrame, segment: str) -> pd.Series:
    return (df["segment"] == segment) & df["is_entry_event"]


def segment_uses_exit_statuses(segment: str) -> bool:
    return segment == MSB


def is_segment_drop_event(df: pd.DataFrame, segment: str) -> pd.Series:
    drop_mask = df["is_closed"].eq(1)
    if segment_uses_exit_statuses(segment):
        drop_mask = drop_mask | df["is_exit_event"]
    return (df["segment"] == segment) & drop_mask


def is_segment_drop_row(row: pd.Series, segment: str) -> bool:
    uses_exit = segment_uses_exit_statuses(segment)
    return bool(
        (row["segment"] == segment)
        and ((row["is_closed"] == 1) or (uses_exit and row["is_exit_event"]))
    )


def weak_client_mask(df: pd.DataFrame) -> pd.Series:
    return (
        (df["turnover_y_bn"] < 0.5)
        & (df["loan"] < 0.5)
        & (df["is_group"] == 0)
        & (df["is_official"] == 0)
    )


def is_weak_client_row(row: pd.Series) -> bool:
    return bool(
        (row["turnover_y_bn"] < 0.5)
        and (row["loan"] < 0.5)
        and (row["is_group"] == 0)
        and (row["is_official"] == 0)
    )


def pct(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.mean()) * 100.0


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def fmt_num(value: float) -> str:
    return f"{value:.2f}"


def md_table(headers, rows) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def as_bool_array(series: pd.Series) -> np.ndarray:
    return series.fillna(False).to_numpy(dtype=bool)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, parse_dates=["eomonth"])
    df = df.sort_values(["client_code", "eomonth"]).reset_index(drop=True)

    # Backward compatibility for renamed numeric fields in df_all.csv.
    if "debt" not in df.columns and "overdue_debt_bn" in df.columns:
        df["debt"] = df["overdue_debt_bn"]
    if "loan" not in df.columns and "loan_amount_bn" in df.columns:
        df["loan"] = df["loan_amount_bn"]

    numeric_cols = [
        "turnover_bn",
        "turnover_y_bn",
        "credit_class",
        "debt",
        "loan",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["is_group", "is_official"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "is_closed" in df.columns:
        df["is_closed"] = pd.to_numeric(df["is_closed"], errors="coerce").fillna(0).astype(int)
    else:
        df["is_closed"] = 0

    segment_map = infer_segment_mapping(df)
    df["segment"] = df["segment"].astype(str).map(lambda value: segment_map.get(value, value))
    status_map = {}
    for value in df["status"].dropna().astype(str).unique():
        if "->" in value:
            left, right = [part.strip() for part in value.split("->", 1)]
            left = segment_map.get(left, left)
            right = segment_map.get(right, right)
            status_map[value] = f"{left}->{right}"
        elif value in segment_map:
            status_map[value] = segment_map[value]
        else:
            status_map[value] = value
    df["status"] = df["status"].astype(str).map(lambda value: status_map.get(value, value))

    df["month_id"] = df["eomonth"].dt.year * 12 + df["eomonth"].dt.month
    df["is_entry_event"] = is_entry_event(df["status"])
    df["is_exit_event"] = is_exit_event(df["status"])
    df["is_transfer_k2m"] = is_transfer_k2m(df["status"])
    df["is_transfer_m2k"] = is_transfer_m2k(df["status"])
    df["corp_rule"] = (
        (df["is_group"] == 1)
        | (df["is_official"] == 1)
        | (df["turnover_y_bn"] > 100)
        | (df["loan"] > 100)
    )

    group = df.groupby("client_code", sort=False)
    for col in [
        "eomonth",
        "month_id",
        "status",
        "segment",
        "credit_class",
        "debt",
        "turnover_bn",
        "turnover_y_bn",
    ]:
        df[f"next_{col}"] = group[col].shift(-1)

    for i in range(1, 7):
        df[f"lead{i}_month_id"] = group["month_id"].shift(-i)
        df[f"lead{i}_credit_class"] = group["credit_class"].shift(-i)
        df[f"lead{i}_turnover_y_bn"] = group["turnover_y_bn"].shift(-i)
        df[f"lead{i}_debt"] = group["debt"].shift(-i)

    for i in range(1, 4):
        df[f"lag{i}_month_id"] = group["month_id"].shift(i)
        df[f"lag{i}_turnover_y_bn"] = group["turnover_y_bn"].shift(i)

    df["next_is_consecutive"] = df["next_month_id"] == (df["month_id"] + 1)
    df["npl_now"] = df["credit_class"] >= 3
    df["watch_now"] = df["credit_class"].isin([1, 2])
    df["has_debt_now"] = df["debt"] > 0
    df["turnover_y_decline_3m"] = (
        (df["lag3_month_id"] == (df["month_id"] - 3))
        & (df["turnover_y_bn"] < df["lag3_turnover_y_bn"])
    )

    def has_lead(i: int) -> pd.Series:
        return df[f"lead{i}_month_id"] == (df["month_id"] + i)

    lead_npl_3m = [
        has_lead(i) & (df[f"lead{i}_credit_class"] >= 3) for i in range(1, 4)
    ]
    df["npl_within_3m"] = np.column_stack(lead_npl_3m).any(axis=1)

    def any_better_credit(horizon: int) -> pd.Series:
        checks = [
            has_lead(i) & (df[f"lead{i}_credit_class"] < df["credit_class"])
            for i in range(1, horizon + 1)
        ]
        return np.column_stack(checks).any(axis=1)

    def any_lower_overdue(horizon: int) -> pd.Series:
        checks = [
            has_lead(i) & (df[f"lead{i}_debt"] < df["debt"])
            for i in range(1, horizon + 1)
        ]
        return np.column_stack(checks).any(axis=1)

    def any_higher_turnover_y(horizon: int) -> pd.Series:
        checks = [
            has_lead(i) & (df[f"lead{i}_turnover_y_bn"] > df["turnover_y_bn"])
            for i in range(1, horizon + 1)
        ]
        return np.column_stack(checks).any(axis=1)

    df["better_credit_3m"] = any_better_credit(3)
    df["better_credit_6m"] = any_better_credit(6)
    df["overdue_down_3m"] = any_lower_overdue(3)
    df["turnover_y_up_3m"] = any_higher_turnover_y(3)

    return df


def summarize_h1(df: pd.DataFrame) -> dict:
    pre_corp = df[(df["segment"] == KORP) & df["next_is_consecutive"]].copy()
    transfer_pre = pre_corp[pre_corp["next_status"] == K2M].copy()
    retain_pre = pre_corp[pre_corp["next_segment"] == KORP].copy()

    transfer_pre["risk_any"] = (
        transfer_pre["npl_now"]
        | transfer_pre["npl_within_3m"]
    )

    transfer_pre["bucket"] = np.select(
        [
            as_bool_array(transfer_pre["corp_rule"] & transfer_pre["risk_any"]),
            as_bool_array(transfer_pre["corp_rule"] & ~transfer_pre["risk_any"]),
            as_bool_array(~transfer_pre["corp_rule"] & transfer_pre["risk_any"]),
        ],
        ["rule_yes_risk_yes", "rule_yes_risk_no", "rule_no_risk_yes"],
        default="rule_no_risk_no",
    )

    transfer_months = (
        transfer_pre["next_eomonth"]
        .value_counts()
        .sort_index()
        .rename_axis("transfer_month")
        .reset_index(name="clients")
    )

    overall_rows = []
    for label, col in [
        ("Already NPL (class 3-5)", "npl_now"),
        ("NPL within 3 months", "npl_within_3m"),
        ("Has debt now", "has_debt_now"),
        ("Turnover_y down vs 3 months earlier", "turnover_y_decline_3m"),
        ("Still satisfied formal KORP rule", "corp_rule"),
    ]:
        overall_rows.append(
            [label, fmt_pct(pct(transfer_pre[col])), fmt_pct(pct(retain_pre[col]))]
        )

    non_rule_transfer = transfer_pre[~transfer_pre["corp_rule"]].copy()
    non_rule_retain = retain_pre[~retain_pre["corp_rule"]].copy()
    non_rule_rows = []
    for label, col in [
        ("Already NPL (class 3-5)", "npl_now"),
        ("NPL within 3 months", "npl_within_3m"),
        ("Has debt now", "has_debt_now"),
        ("Turnover_y down vs 3 months earlier", "turnover_y_decline_3m"),
    ]:
        non_rule_rows.append(
            [label, fmt_pct(pct(non_rule_transfer[col])), fmt_pct(pct(non_rule_retain[col]))]
        )

    overdue_transfer = non_rule_transfer.loc[
        non_rule_transfer["has_debt_now"], "debt"
    ]
    overdue_retain = non_rule_retain.loc[non_rule_retain["has_debt_now"], "debt"]

    bucket_counts = transfer_pre["bucket"].value_counts().reindex(
        ["rule_no_risk_no", "rule_no_risk_yes", "rule_yes_risk_no", "rule_yes_risk_yes"],
        fill_value=0,
    )

    return {
        "transfer_pre": transfer_pre,
        "retain_pre": retain_pre,
        "transfer_months": transfer_months,
        "overall_rows": overall_rows,
        "non_rule_rows": non_rule_rows,
        "bucket_counts": bucket_counts,
        "overdue_transfer_mean": overdue_transfer.mean() if len(overdue_transfer) else 0.0,
        "overdue_retain_mean": overdue_retain.mean() if len(overdue_retain) else 0.0,
        "overdue_transfer_median": overdue_transfer.median() if len(overdue_transfer) else 0.0,
        "overdue_retain_median": overdue_retain.median() if len(overdue_retain) else 0.0,
        "total_transfers": len(transfer_pre),
        "total_retained": len(retain_pre),
        "non_rule_transfer_n": len(non_rule_transfer),
        "non_rule_retain_n": len(non_rule_retain),
    }


def build_entry_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    entries = df[is_segment_entry_event(df, KORP)].copy()
    max_month = int(df["month_id"].max())
    rows = []

    for _, row in entries.iterrows():
        client = row["client_code"]
        entry_month_id = int(row["month_id"])
        sub = df[(df["client_code"] == client) & (df["month_id"] >= entry_month_id)].copy()
        sub = sub.sort_values("month_id")

        event_month_id = None
        event_type = None

        for i in range(1, len(sub)):
            curr = sub.iloc[i]
            prev = sub.iloc[i - 1]
            if curr["month_id"] != (prev["month_id"] + 1):
                event_month_id = int(curr["month_id"])
                event_type = "gap"
                break
            if is_segment_drop_row(curr, KORP):
                event_month_id = int(curr["month_id"])
                event_type = "drop_or_closed"
                break
            if bool(curr["is_transfer_k2m"]):
                event_month_id = int(curr["month_id"])
                event_type = "to_msb"
                break
            if curr["segment"] != KORP:
                event_month_id = int(curr["month_id"])
                event_type = "non_korp_other"
                break

        rows.append(
            {
                "client_code": client,
                "entry_date": row["eomonth"],
                "entry_month_id": entry_month_id,
                "entry_status": row["status"],
                "corp_rule": bool(row["corp_rule"]),
                "weak": is_weak_client_row(row),
                "months_observable_after_entry": max_month - entry_month_id,
                "event_type": event_type,
                "months_to_event": (
                    None if event_month_id is None else (event_month_id - entry_month_id)
                ),
            }
        )

    return pd.DataFrame(rows)


def summarize_h2(df: pd.DataFrame) -> dict:
    entries = df[is_segment_entry_event(df, KORP)].copy()
    outcomes = build_entry_outcomes(df)

    month_counts = (
        entries["eomonth"].value_counts().sort_index().rename_axis("entry_month").reset_index(name="clients")
    )

    def horizon_summary(horizon: int) -> dict:
        mature = outcomes[outcomes["months_observable_after_entry"] >= horizon].copy()
        event_within = mature["months_to_event"].fillna(999) <= horizon
        to_msb_within = (mature["event_type"] == "to_msb") & event_within
        drop_within = mature["event_type"].eq("drop_or_closed") & event_within
        leaves = mature.loc[event_within, "event_type"].value_counts()

        weak = mature[mature["weak"]].copy()
        non_weak = mature[~mature["weak"]].copy()
        weak_leave = weak["months_to_event"].fillna(999) <= horizon
        weak_to_msb = (weak["event_type"] == "to_msb") & weak_leave
        non_weak_leave = non_weak["months_to_event"].fillna(999) <= horizon
        non_weak_to_msb = (non_weak["event_type"] == "to_msb") & non_weak_leave

        return {
            "horizon": horizon,
            "mature_n": len(mature),
            "leave_within_pct": pct(event_within),
            "to_msb_within_pct": pct(to_msb_within),
            "drop_within_pct": pct(drop_within),
            "weak_share_pct": pct(mature["weak"]),
            "corp_rule_share_pct": pct(mature["corp_rule"]),
            "leave_breakdown": leaves,
            "weak_n": len(weak),
            "weak_leave_pct": pct(weak_leave),
            "weak_to_msb_pct": pct(weak_to_msb),
            "non_weak_n": len(non_weak),
            "non_weak_leave_pct": pct(non_weak_leave),
            "non_weak_to_msb_pct": pct(non_weak_to_msb),
            "non_weak_corp_rule_pct": pct(non_weak["corp_rule"]),
        }

    h3 = horizon_summary(3)
    h6 = horizon_summary(6)

    quality_rows = [
        ["Met formal KORP rule at entry", fmt_pct(pct(entries["corp_rule"]))],
        [
            "Group or official at entry",
            fmt_pct(pct((entries["is_group"] == 1) | (entries["is_official"] == 1))),
        ],
        ["Turnover_y > 100 at entry", fmt_pct(pct(entries["turnover_y_bn"] > 100))],
        ["Loan amount > 100 at entry", fmt_pct(pct(entries["loan"] > 100))],
        ["Already NPL at entry", fmt_pct(pct(entries["credit_class"] >= 3))],
        ["Watchlist (class 1-2) at entry", fmt_pct(pct(entries["credit_class"].isin([1, 2])))],
        ["Any overdue at entry", fmt_pct(pct(entries["debt"] > 0))],
        [
            "Weak at entry: zero turnover_y, zero loan, not group, not official",
            fmt_pct(pct(weak_client_mask(entries))),
        ],
    ]

    return {
        "entries": entries,
        "outcomes": outcomes,
        "month_counts": month_counts,
        "quality_rows": quality_rows,
        "h3": h3,
        "h6": h6,
    }


def summarize_improvement(h1: dict) -> dict:
    transfer_pre = h1["transfer_pre"]
    retain_pre = h1["retain_pre"]

    risky_transfer = transfer_pre[
        transfer_pre["npl_now"]
    ].copy()
    risky_retain = retain_pre[
        retain_pre["npl_now"]
    ].copy()

    npl_transfer = transfer_pre[transfer_pre["npl_now"]].copy()
    npl_retain = retain_pre[retain_pre["npl_now"]].copy()

    risky_rows = []
    for label, col in [
        ("Better credit class within 3 months", "better_credit_3m"),
        ("Better credit class within 6 months", "better_credit_6m"),
        ("Overdue debt decreased within 3 months", "overdue_down_3m"),
        ("Turnover_y increased within 3 months", "turnover_y_up_3m"),
    ]:
        risky_rows.append(
            [label, fmt_pct(pct(risky_transfer[col])), fmt_pct(pct(risky_retain[col]))]
        )

    npl_rows = []
    for label, col in [
        ("Better credit class within 3 months", "better_credit_3m"),
        ("Better credit class within 6 months", "better_credit_6m"),
        ("Overdue debt decreased within 3 months", "overdue_down_3m"),
    ]:
        npl_rows.append(
            [label, fmt_pct(pct(npl_transfer[col])), fmt_pct(pct(npl_retain[col]))]
        )

    return {
        "risky_n_transfer": len(risky_transfer),
        "risky_n_retain": len(risky_retain),
        "npl_n_transfer": len(npl_transfer),
        "npl_n_retain": len(npl_retain),
        "risky_rows": risky_rows,
        "npl_rows": npl_rows,
    }


def build_report(df: pd.DataFrame, h1: dict, h2: dict, improve: dict) -> str:
    row_count = len(df)
    client_count = df["client_code"].nunique()
    date_min = df["eomonth"].min().date().isoformat()
    date_max = df["eomonth"].max().date().isoformat()
    month_count = df["eomonth"].nunique()
    m2k_count = int((df["status"] == M2K).sum())
    k2m_count = int((df["status"] == K2M).sum())

    transfer_month_rows = [
        [row.transfer_month.date().isoformat(), int(row.clients)]
        for row in h1["transfer_months"].itertuples(index=False)
    ]

    bucket = h1["bucket_counts"]
    leave_3 = h2["h3"]["leave_breakdown"]
    leave_6 = h2["h6"]["leave_breakdown"]

    lines = [
        "# Resegmentation Analysis",
        "",
        "Labels used below: `KORP = corporate segment`, `MSB = small-business segment`.",
        "",
        "## Data Overview",
        f"- Rows: {row_count:,}",
        f"- Unique clients: {client_count:,}",
        f"- Month-end snapshots: {month_count} ({date_min} to {date_max})",
        f"- `KORP->MSB` transfers observed: {k2m_count}",
        f"- `MSB->KORP` transfers observed: {m2k_count}",
        "",
        "Most `KORP->MSB` transfers were concentrated in the expected resegmentation windows.",
        "",
        md_table(["Transfer month", "Clients"], transfer_month_rows),
        "",
        "## Hypothesis 1",
        "`KORP` is transferring bad clients to `MSB`.",
        "",
        "### Test 1A: Pre-transfer profile vs retained `KORP` clients",
        "The comparison below uses the month immediately before transfer and compares it with `KORP` clients that stayed in `KORP` in the next month.",
        "",
        md_table(["Metric", "Next month KORP->MSB", "Retained in KORP"], h1["overall_rows"]),
        "",
        "### Test 1B: Same comparison only among clients who no longer satisfied the formal `KORP` rule",
        "",
        md_table(["Metric", "Next month KORP->MSB", "Retained in KORP"], h1["non_rule_rows"]),
        "",
        "Overdue amounts among non-rule clients with overdue debt:",
        f"- `KORP->MSB`: mean {fmt_num(h1['overdue_transfer_mean'])} bn, median {fmt_num(h1['overdue_transfer_median'])} bn",
        f"- Retained `KORP`: mean {fmt_num(h1['overdue_retain_mean'])} bn, median {fmt_num(h1['overdue_retain_median'])} bn",
        "",
        "Breakdown of `KORP->MSB` transfers by rule/risk bucket (month before transfer):",
        md_table(
            ["Bucket", "Clients", "Share"],
            [
                [
                    "No formal KORP rule, no risk flag",
                    int(bucket["rule_no_risk_no"]),
                    fmt_pct(100 * bucket["rule_no_risk_no"] / h1["total_transfers"]),
                ],
                [
                    "No formal KORP rule, risk flag present",
                    int(bucket["rule_no_risk_yes"]),
                    fmt_pct(100 * bucket["rule_no_risk_yes"] / h1["total_transfers"]),
                ],
                [
                    "Still formal KORP rule, no risk flag",
                    int(bucket["rule_yes_risk_no"]),
                    fmt_pct(100 * bucket["rule_yes_risk_no"] / h1["total_transfers"]),
                ],
                [
                    "Still formal KORP rule, risk flag present",
                    int(bucket["rule_yes_risk_yes"]),
                    fmt_pct(100 * bucket["rule_yes_risk_yes"] / h1["total_transfers"]),
                ],
            ],
        ),
        "",
        "### Reading",
        "- Partial support only. The transferred cohort is more stressed than the average retained `KORP` client on watchlist status, overdue incidence, and falling `turnover_y`.",
        "- But this does not look like mass dumping of the worst current NPLs. Among clients who already failed the formal `KORP` rule, transferred clients had lower current NPL and lower overdue amounts than non-rule clients still kept in `KORP`.",
        f"- {fmt_pct(100 * (bucket['rule_no_risk_no'] + bucket['rule_no_risk_yes']) / h1['total_transfers'])} of transfers happened after the client no longer met the formal `KORP` rule. Only {fmt_pct(100 * (bucket['rule_yes_risk_no'] + bucket['rule_yes_risk_yes']) / h1['total_transfers'])} still met the rule one month before transfer.",
        "- Bottom line: the pattern is more consistent with rule-based resegmentation plus some bias toward borderline deteriorating clients, not with systematically pushing out the worst NPL book.",
        "",
        "## Hypothesis 2",
        "`KORP` introduces mediocre clients for a short time to hit client-count KPI and then drops them or passes them to `MSB`.",
        "",
        f"Total `entry` + `re_entry` rows in `KORP`: {len(h2['entries'])}",
        "",
        "### Entry quality",
        md_table(["Metric", "Share"], h2["quality_rows"]),
        "",
        "### Mature cohorts only",
        "To avoid right-censoring, the tables below use only entry cohorts that had enough follow-up time in the dataset.",
        "",
        md_table(
            ["Window", "Mature entries", "Left KORP", "Moved to MSB", "Dropped/closed", "Weak at entry"],
            [
                [
                    "Within 3 months",
                    h2["h3"]["mature_n"],
                    fmt_pct(h2["h3"]["leave_within_pct"]),
                    fmt_pct(h2["h3"]["to_msb_within_pct"]),
                    fmt_pct(h2["h3"]["drop_within_pct"]),
                    fmt_pct(h2["h3"]["weak_share_pct"]),
                ],
                [
                    "Within 6 months",
                    h2["h6"]["mature_n"],
                    fmt_pct(h2["h6"]["leave_within_pct"]),
                    fmt_pct(h2["h6"]["to_msb_within_pct"]),
                    fmt_pct(h2["h6"]["drop_within_pct"]),
                    fmt_pct(h2["h6"]["weak_share_pct"]),
                ],
            ],
        ),
        "",
        "Six-month leave breakdown for mature entry cohorts:",
        md_table(
            ["Outcome within 6 months", "Clients"],
            [[idx, int(val)] for idx, val in leave_6.items()],
        ),
        "",
        "Weak vs non-weak mature 6-month entry cohorts:",
        md_table(
            ["Entry type", "Clients", "Left within 6m", "Moved to MSB within 6m"],
            [
                [
                    "Weak at entry",
                    h2["h6"]["weak_n"],
                    fmt_pct(h2["h6"]["weak_leave_pct"]),
                    fmt_pct(h2["h6"]["weak_to_msb_pct"]),
                ],
                [
                    "Not weak at entry",
                    h2["h6"]["non_weak_n"],
                    fmt_pct(h2["h6"]["non_weak_leave_pct"]),
                    fmt_pct(h2["h6"]["non_weak_to_msb_pct"]),
                ],
            ],
        ),
        "",
        "### Reading",
        "- Strong support for this hypothesis in a specific sub-cohort: the weak `KORP` entrants.",
        f"- {fmt_pct(pct((h2['entries']['turnover_y_bn'] == 0) & (h2['entries']['loan'] == 0) & (h2['entries']['is_group'] == 0) & (h2['entries']['is_official'] == 0)))} of all `KORP` entrants were weak at entry and did not satisfy the formal `KORP` rule.",
        f"- In the mature 6-month cohort, weak entrants left `KORP` in {fmt_pct(h2['h6']['weak_leave_pct'])} of cases, with {fmt_pct(h2['h6']['weak_to_msb_pct'])} moving specifically to `MSB`.",
        f"- In the same mature 6-month cohort, non-weak entrants almost never left `KORP` early: {fmt_pct(h2['h6']['non_weak_leave_pct'])}, and none moved to `MSB` within 6 months.",
        "- This is hard to explain as normal onboarding noise. It is consistent with short-term inflation of the `KORP` client base using clients that do not look like durable `KORP` relationships.",
        "",
        "## Could transferred clients have become better if they had not been moved to MSB?",
        "This cannot be proven causally from this dataset alone, but we can compare post-event improvement rates.",
        "",
        "### Risky clients before transfer vs risky clients retained in KORP",
        md_table(
            ["Metric", "KORP->MSB risky clients", "Retained KORP risky clients"],
            improve["risky_rows"],
        ),
        f"Sample sizes: transferred risky clients = {improve['risky_n_transfer']}, retained risky clients = {improve['risky_n_retain']}",
        "",
        "### NPL clients before transfer vs NPL clients retained in KORP",
        md_table(
            ["Metric", "KORP->MSB NPL clients", "Retained KORP NPL clients"],
            improve["npl_rows"],
        ),
        f"Sample sizes: transferred NPL clients = {improve['npl_n_transfer']}, retained KORP NPL clients = {improve['npl_n_retain']}",
        "",
        "### Reading",
        "- Transferred risky clients did improve sometimes, and their credit improvement rates were very similar to risky clients retained in `KORP`.",
        "- That means the transferred cohort was not uniformly hopeless. Some clients still had recovery potential after the transfer.",
        "- At the same time, the improvement gap is not large enough to claim that keeping them in `KORP` would have clearly produced better outcomes.",
        "- The safest conclusion is: there is no strong evidence that transferred clients were beyond recovery, but this file alone cannot prove they would have improved more if they had stayed in `KORP`.",
        "",
        "## Final Takeaway",
        "- Hypothesis 1 is only partially supported. `KORP->MSB` transfers are somewhat more stressed than the average retained `KORP` client, especially on watchlist status and turnover decline, but they are mostly clients that already fail the formal `KORP` rule and they are not the worst current NPL cases.",
        "- Hypothesis 2 is strongly supported for weak `KORP` entrants. A large weak sub-cohort enters `KORP` without clear rule support and then leaves quickly, most often by moving into `MSB` rather than by genuine closure.",
        "- Recovery potential exists in part of the transferred population, so the transfer process may be moving some salvageable clients out of `KORP`, but the data is descriptive rather than causal.",
    ]

    return "\n".join(lines) + "\n"


def main() -> None:
    df = load_data()
    h1 = summarize_h1(df)
    h2 = summarize_h2(df)
    improvement = summarize_improvement(h1)
    report = build_report(df, h1, h2, improvement)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_FILE}")


if __name__ == "__main__":
    main()
