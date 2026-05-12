"""
Section reactivation analysis.

This script ranks product sections by reactivation opportunity using monthly
sales history, decline signals, recent momentum, and 2025 profitability.

Example:
    python scripts/section_reactivation_analysis.py data/sales.xlsx
    python scripts/section_reactivation_analysis.py data/sales.csv -o reports/reactivation.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress


DATE_COL = "Date"
SECTION_COL = "Section"
QTY_COL = "bal Qty"
FIRST_INV_COL = "First_Inv_Date"
MARGIN_2025_COL = "Margin_%_2025"

MIN_AGE_MONTHS = 18
FIRST_AVG_STRONG = 1_000
FIRST_AVG_MEDIUM = 500


def load_data(input_path: Path) -> pd.DataFrame:
    """Load Excel or CSV data and normalize the important date columns."""
    if input_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(input_path)
    elif input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        raise ValueError("Input file must be .xlsx, .xls, or .csv")

    df.columns = df.columns.str.strip()
    validate_columns(df)

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[FIRST_INV_COL] = pd.to_datetime(df[FIRST_INV_COL], errors="coerce")
    df[QTY_COL] = pd.to_numeric(df[QTY_COL], errors="coerce").fillna(0)
    df[MARGIN_2025_COL] = pd.to_numeric(df[MARGIN_2025_COL], errors="coerce")

    return df.dropna(subset=[DATE_COL, SECTION_COL])


def validate_columns(df: pd.DataFrame) -> None:
    """Fail early if the source data does not contain the expected columns."""
    required_columns = {
        DATE_COL,
        SECTION_COL,
        QTY_COL,
        FIRST_INV_COL,
        MARGIN_2025_COL,
    }
    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")


def build_monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate section sales by calendar month."""
    return (
        df.groupby([SECTION_COL, pd.Grouper(key=DATE_COL, freq="MS")])[QTY_COL]
        .sum()
        .reset_index()
    )


def complete_section_timeline(
    section: str,
    section_sales: pd.DataFrame,
    source_df: pd.DataFrame,
    global_first_date: pd.Timestamp,
    global_last_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.Timestamp, str]:
    """Fill missing months with zero sales for one section."""
    first_inv = source_df.loc[source_df[SECTION_COL] == section, FIRST_INV_COL].min()
    if pd.isna(first_inv):
        first_inv = section_sales[DATE_COL].min()

    first_inv = first_inv.to_period("M").to_timestamp()
    history_flag = "Missing Early History" if first_inv < global_first_date else "Complete"

    timeline_start = max(first_inv, global_first_date)
    full_month_range = pd.date_range(timeline_start, global_last_date, freq="MS")

    completed_sales = section_sales.set_index(DATE_COL).reindex(full_month_range)
    completed_sales.index.name = DATE_COL
    completed_sales[QTY_COL] = completed_sales[QTY_COL].fillna(0)
    completed_sales[SECTION_COL] = section

    return completed_sales.reset_index(), first_inv, history_flag


def month_difference(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    """Return the number of full month steps between two month-start dates."""
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)


def percent_change(new_value: float, old_value: float) -> float:
    """Calculate percentage change and return NaN when the base is zero."""
    if old_value <= 0:
        return np.nan
    return (new_value - old_value) / old_value * 100


def score_section(
    first_avg: float,
    decline_pct: float,
    slope: float,
    profitable_2025: bool,
    recent_momentum: float,
    recent_6m_total: float,
    dead_section: bool,
    history_flag: str,
) -> int:
    """Calculate a simple business score for reactivation priority."""
    score = 0

    if first_avg >= FIRST_AVG_STRONG:
        score += 30
    elif first_avg >= FIRST_AVG_MEDIUM:
        score += 20

    if not np.isnan(decline_pct):
        if decline_pct <= -70:
            score += 30
        elif decline_pct <= -40:
            score += 20

    if slope < 0:
        score += 20
    if profitable_2025:
        score += 20
    if recent_momentum > 30:
        score += 10
    if recent_6m_total > 100:
        score += 10
    if dead_section:
        score -= 10
    if history_flag != "Complete":
        score -= 15

    return score


def classify_status(dead_section: bool, decline_pct: float, slope: float) -> str:
    """Convert the main decline indicators into a readable status."""
    if dead_section:
        return "Dead Section"
    if not np.isnan(decline_pct) and decline_pct <= -70 and slope < 0:
        return "Critical Decline"
    if not np.isnan(decline_pct) and decline_pct <= -40:
        return "Strong Decline"
    if slope < 0:
        return "Slow Decline"
    return "Healthy"


def analyze_section(
    section: str,
    monthly_sales: pd.DataFrame,
    source_df: pd.DataFrame,
    global_first_date: pd.Timestamp,
    global_last_date: pd.Timestamp,
) -> dict[str, object] | None:
    """Analyze one section and return one output row."""
    section_sales = (
        monthly_sales.loc[monthly_sales[SECTION_COL] == section]
        .copy()
        .sort_values(DATE_COL)
    )

    section_sales, first_inv, history_flag = complete_section_timeline(
        section,
        section_sales,
        source_df,
        global_first_date,
        global_last_date,
    )

    actual_start = section_sales[DATE_COL].min()
    age_months = month_difference(actual_start, global_last_date)
    if age_months < MIN_AGE_MONTHS:
        return None

    first_12m_end = actual_start + pd.DateOffset(months=12)
    first_12m = section_sales[
        (section_sales[DATE_COL] >= actual_start)
        & (section_sales[DATE_COL] < first_12m_end)
    ]
    last_12m_start = global_last_date - pd.DateOffset(months=11)

    first_avg = first_12m[QTY_COL].mean()
    last_avg = section_sales.loc[section_sales[DATE_COL] >= last_12m_start, QTY_COL].mean()
    retention_ratio = last_avg / first_avg if first_avg > 0 else np.nan
    decline_pct = percent_change(last_avg, first_avg)

    month_index = np.arange(len(section_sales))
    slope, _, r_value, _, _ = linregress(month_index, section_sales[QTY_COL].values)
    r2 = r_value**2

    recent_6m_avg = section_sales.tail(6)[QTY_COL].mean()
    prev_6m_avg = section_sales.iloc[-12:-6][QTY_COL].mean()
    recent_momentum = percent_change(recent_6m_avg, prev_6m_avg)

    recent_6m_total = section_sales.tail(6)[QTY_COL].sum()
    sales_2024 = section_sales.loc[section_sales[DATE_COL].dt.year == 2024, QTY_COL].sum()
    sales_2025 = section_sales.loc[section_sales[DATE_COL].dt.year == 2025, QTY_COL].sum()

    section_source = source_df.loc[source_df[SECTION_COL] == section]
    margin_2025 = section_source[MARGIN_2025_COL].max()
    profitable_2025 = margin_2025 > 0
    dead_section = (section_sales.tail(3)[QTY_COL] == 0).all()

    score = score_section(
        first_avg=first_avg,
        decline_pct=decline_pct,
        slope=slope,
        profitable_2025=profitable_2025,
        recent_momentum=recent_momentum,
        recent_6m_total=recent_6m_total,
        dead_section=dead_section,
        history_flag=history_flag,
    )
    status = classify_status(dead_section, decline_pct, slope)

    return {
        "Section": section,
        "First_Inv_Date": first_inv,
        "History_Flag": history_flag,
        "Age_Months": age_months,
        "First_12M_Avg": round(first_avg, 2),
        "Last_12M_Avg": round(last_avg, 2),
        "Retention_Ratio": round(retention_ratio, 2),
        "Decline_%": round(decline_pct, 2),
        "Slope_All_Years": round(slope, 2),
        "R2": round(r2, 3),
        "Recent_6M_Momentum_%": round(recent_momentum, 2),
        "Recent_6M_Total": round(recent_6m_total, 2),
        "Sales_2024": round(sales_2024, 2),
