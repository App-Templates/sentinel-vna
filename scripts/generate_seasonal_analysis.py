#!/usr/bin/env python3
"""
Generate seasonal eCPM analysis from real parquet data.

This script computes weekly eCPM averages across ALL publishers for 2025,
defines seasonal periods based on calendar knowledge, and outputs JSON
for the backend to use in seasonal analysis endpoints.

Output: data/seasonal/ecpm-seasonal-analysis.json
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def compute_week_date_ranges(year: int) -> dict[int, dict[str, str]]:
    """
    Compute ISO week date ranges for the given year.
    Returns dict: {week_number: {start: YYYY-MM-DD, end: YYYY-MM-DD}}
    """
    week_ranges = {}

    # Start from the first Monday of the ISO year
    jan_4 = datetime(year, 1, 4)  # ISO year always contains Jan 4
    first_monday = jan_4 - timedelta(days=jan_4.weekday())

    for week in range(1, 54):  # ISO weeks can go up to 53
        week_start = first_monday + timedelta(weeks=week - 1)
        week_end = week_start + timedelta(days=6)

        # Check if this week belongs to the target year
        # (A week belongs to a year if Thursday of that week is in that year)
        thursday = week_start + timedelta(days=3)
        if thursday.year == year:
            week_ranges[week] = {
                "start": week_start.strftime("%Y-%m-%d"),
                "end": week_end.strftime("%Y-%m-%d"),
            }

    return week_ranges


def main():
    BASE_DIR = Path(__file__).parent.parent
    PARQUET_PATH = BASE_DIR / "data" / "baseline" / "daily_adrequests_aggregated.parquet"
    OUTPUT_PATH = BASE_DIR / "data" / "seasonal" / "ecpm-seasonal-analysis.json"

    print(f"Loading data from: {PARQUET_PATH}")

    # Load parquet
    df = pd.read_parquet(PARQUET_PATH)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to 2025
    df_2025 = df[df["date"].dt.year == 2025].copy()

    if df_2025.empty:
        print("ERROR: No data found for 2025")
        return

    print(f"Loaded {len(df_2025)} rows for 2025")
    print(f"Date range: {df_2025['date'].min()} to {df_2025['date'].max()}")

    # Compute ISO week
    iso_cal = df_2025["date"].dt.isocalendar()
    df_2025["iso_week"] = iso_cal.week.astype(int)
    df_2025["iso_year"] = iso_cal.year.astype(int)

    # Filter out rows where ISO year != 2025 (edge case: last days of Dec might belong to next year)
    df_2025 = df_2025[df_2025["iso_year"] == 2025]

    # Weekly aggregates across ALL publishers
    weekly = df_2025.groupby("iso_week").agg(
        revenue=("revenue", "sum"),
        impressions=("impressions", "sum"),
    ).reset_index()

    # Compute weekly eCPM
    weekly["ecpm"] = (weekly["revenue"] / weekly["impressions"] * 1000).fillna(0)

    # Yearly average eCPM
    total_revenue = weekly["revenue"].sum()
    total_impressions = weekly["impressions"].sum()
    yearly_avg_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0

    print(f"Yearly avg eCPM: {yearly_avg_ecpm:.2f}")
    print(f"Weekly data: {len(weekly)} weeks")

    # Define seasonal periods (calendar-based)
    # Format: (id, label, weeks_list)
    period_definitions = [
        ("post_holiday", "Post-New Year", list(range(1, 5))),           # W1-W4
        ("valentine", "Valentine's Day", list(range(6, 8))),            # W6-W7
        ("pre_easter", "Pre-Easter", list(range(10, 13))),              # W10-W12
        ("easter", "Easter", list(range(13, 17))),                       # W13-W16
        ("spring", "Spring", list(range(17, 22))),                       # W17-W21
        ("pre_summer", "Pre-Summer", list(range(22, 26))),               # W22-W25
        ("summer", "Summer", list(range(26, 35))),                       # W26-W34
        ("back_to_school", "Back to School", list(range(35, 38))),       # W35-W37
        ("autumn", "Autumn", list(range(38, 44))),                       # W38-W43
        ("singles_day", "Singles Day", list(range(44, 46))),             # W44-W45
        ("pre_blackfriday", "Pre-Black Friday", [46]),                   # W46
        ("black_friday", "Black Friday / Cyber Monday", list(range(47, 49))),  # W47-W48
        ("xmas", "Christmas / New Year", list(range(49, 53))),           # W49-W52
    ]

    seasonal_periods = []

    for period_id, label, weeks in period_definitions:
        # Filter weekly data for this period
        period_weeks = weekly[weekly["iso_week"].isin(weeks)]

        if period_weeks.empty:
            print(f"WARNING: No data for period '{label}' (weeks {weeks})")
            continue

        # Compute avg eCPM for the period
        period_revenue = period_weeks["revenue"].sum()
        period_impressions = period_weeks["impressions"].sum()
        avg_ecpm = (period_revenue / period_impressions * 1000) if period_impressions > 0 else 0

        # Delta vs yearly avg
        delta_pct = ((avg_ecpm - yearly_avg_ecpm) / yearly_avg_ecpm * 100) if yearly_avg_ecpm > 0 else 0

        # Signal classification
        if delta_pct > 5:
            signal = "RAISE"
        elif delta_pct < -5:
            signal = "LOWER"
        else:
            signal = "NEUTRAL"

        seasonal_periods.append({
            "id": period_id,
            "label": label,
            "signal": signal,
            "weeks": weeks,
            "avg_ecpm": round(avg_ecpm, 2),
            "delta_pct": round(delta_pct, 1),
        })

        print(f"  {label} (W{min(weeks)}-W{max(weeks)}): eCPM={avg_ecpm:.2f}, delta={delta_pct:+.1f}%, signal={signal}")

    # Compute week date ranges
    week_ranges = compute_week_date_ranges(2025)

    # Build week_date_ranges with period mapping
    week_date_ranges = {}
    for period in seasonal_periods:
        for week in period["weeks"]:
            if week in week_ranges:
                week_date_ranges[str(week)] = {
                    **week_ranges[week],
                    "period": period["id"],
                }

    # Output JSON
    output_data = {
        "year": 2025,
        "seasonal_periods": seasonal_periods,
        "week_date_ranges": week_date_ranges,
    }

    # Create output directory
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Seasonal analysis written to: {OUTPUT_PATH}")
    print(f"  - {len(seasonal_periods)} seasonal periods")
    print(f"  - {len(week_date_ranges)} weeks mapped")


if __name__ == "__main__":
    main()
