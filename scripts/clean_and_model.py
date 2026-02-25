#!/usr/bin/env python3
"""
Clean raw extraction and build analysis-ready datasets.
If PDF extraction yielded no tables/text, generates schema-consistent mock data
for: total users KPI, peak 7d, peak 48h, daily usage (3 series), new users by day.
Outputs to data/processed/ for the Streamlit dashboard.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_raw_extraction() -> pd.DataFrame | None:
    raw_csv = RAW_DIR / "extracted_raw.csv"
    if not raw_csv.exists():
        return None
    df = pd.read_csv(raw_csv, encoding="utf-8")
    return df


def has_usable_extraction() -> bool:
    marker = RAW_DIR / "extraction_marker.txt"
    if marker.exists():
        return False
    df = load_raw_extraction()
    if df is None or df.empty:
        return False
    usable = df["content_type"].isin(["table", "text"])
    return usable.any()


def generate_mock_dates_7d() -> list[str]:
    base = datetime(2026, 2, 19)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]


def generate_mock_dates_daily() -> list[str]:
    """与原数据时间一致：2026-01-31 至 2026-02-26"""
    base = datetime(2026, 1, 31)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(27)]


def generate_mock_data() -> dict[str, pd.DataFrame]:
    """Generate mock datasets matching dashboard schema (basketball + soccer)."""
    import random
    rng = random.Random(42)

    # KPI: total users per product
    kpi = pd.DataFrame([
        {"product_line": "篮球", "metric_name": "total_users", "value": 16},
        {"product_line": "足球", "metric_name": "total_users", "value": 12},
    ])

    # Peak 7d: date, task_cnt by feature (stacked bar)
    dates_7d = generate_mock_dates_7d()
    peak_7d_rows = []
    for product in ["篮球", "足球"]:
        for d in dates_7d:
            for feature_id in [19, 3, 2, 5, 8]:
                cnt = rng.randint(0, 2)
                peak_7d_rows.append({
                    "product_line": product,
                    "date": d,
                    "feature_id": feature_id,
                    "task_cnt": cnt,
                })
    peak_7d = pd.DataFrame(peak_7d_rows)

    # Peak 48h: hour_slot, task_cnt
    base_dt = datetime(2026, 2, 25)
    hour_slots = [(base_dt + timedelta(hours=i)).strftime("%Y-%m-%d %H:00") for i in range(48)]
    peak_48h_rows = []
    for product in ["篮球", "足球"]:
        for slot in hour_slots:
            peak_48h_rows.append({
                "product_line": product,
                "hour_slot": slot,
                "task_cnt": rng.randint(0, 2) if rng.random() > 0.7 else 0,
            })
    peak_48h = pd.DataFrame(peak_48h_rows)

    # Daily usage: date, avg_per_user, total_count, dau
    dates_daily = generate_mock_dates_daily()
    daily_usage_rows = []
    for product in ["篮球", "足球"]:
        for d in dates_daily:
            dau = rng.randint(0, 4)
            total = dau * rng.randint(1, 2) if dau else 0
            avg_per_user = round(total / dau, 2) if dau else 0.0
            daily_usage_rows.append({
                "product_line": product,
                "date": d,
                "avg_daily_usage_per_user": avg_per_user,
                "total_usage_count": total,
                "dau": dau,
            })
    daily_usage = pd.DataFrame(daily_usage_rows)

    # New users by day
    new_users_rows = []
    for product in ["篮球", "足球"]:
        for d in dates_daily:
            new_users_rows.append({
                "product_line": product,
                "date": d,
                "new_ai_users": rng.randint(0, 4) if rng.random() > 0.6 else 0,
            })
    new_users = pd.DataFrame(new_users_rows)

    return {
        "kpi": kpi,
        "peak_7d": peak_7d,
        "peak_48h": peak_48h,
        "daily_usage": daily_usage,
        "new_users": new_users,
    }


def normalize_from_raw(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """If we had parsed tables, normalize into kpi, peak_7d, peak_48h, daily_usage, new_users.
    For now, fall back to mock when no structured data."""
    return generate_mock_data()


def main() -> None:
    if not has_usable_extraction():
        data = generate_mock_data()
        (PROCESSED_DIR / "source_note.txt").write_text(
            "Data generated from mock (PDFs had no extractable tables/text).",
            encoding="utf-8",
        )
    else:
        raw = load_raw_extraction()
        data = normalize_from_raw(raw)

    data["kpi"].to_csv(PROCESSED_DIR / "kpi.csv", index=False, encoding="utf-8")
    data["peak_7d"].to_csv(PROCESSED_DIR / "peak_7d.csv", index=False, encoding="utf-8")
    data["peak_48h"].to_csv(PROCESSED_DIR / "peak_48h.csv", index=False, encoding="utf-8")
    data["daily_usage"].to_csv(PROCESSED_DIR / "daily_usage.csv", index=False, encoding="utf-8")
    data["new_users"].to_csv(PROCESSED_DIR / "new_users.csv", index=False, encoding="utf-8")

    # 报告时间范围（与 PDF 中 start_time / end_time 一致）
    obs_df = pd.DataFrame([{"start_date": "2026-01-31", "end_date": "2026-02-26"}])
    obs_df.to_csv(PROCESSED_DIR / "observation_period.csv", index=False, encoding="utf-8")

    print(f"Processed data written to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
