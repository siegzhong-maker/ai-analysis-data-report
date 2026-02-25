#!/usr/bin/env python3
"""
AI Basketball / Soccer Analysis Dashboard — 用户行为与数据表现（定性+定量分析）
Data source: data/processed/*.csv (from PDF extraction or mock).
Run: streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def detect_change_segments(dates, values, min_before=2, change_ratio=1.4):
    """
    基于实际时间序列检测拐点，划分铺垫/冲突/结局区间。
    仅依据传入的 dates 与 values，不编造。若数据点不足或无显著拐点则 change_date 为 None。
    """
    if dates is None or values is None or len(dates) < 3 or len(values) < 3 or len(dates) != len(values):
        if dates is not None and len(dates) > 0:
            return (dates[0], dates[-1]), None, None
        return (None, None), None, None

    dates = list(dates)
    values = list(values)
    n = len(dates)
    change_date = None
    change_idx = None

    for i in range(min_before, n):
        mean_before = sum(values[:i]) / i
        if mean_before == 0:
            continue
        ratio = values[i] / mean_before
        if ratio >= change_ratio or ratio <= (1.0 / change_ratio):
            change_date = dates[i]
            change_idx = i
            break

    if change_date is None or change_idx is None:
        segment_before = (dates[0], dates[-1])
        segment_after = None
        return segment_before, None, segment_after

    segment_before = (dates[0], dates[change_idx - 1])
    segment_after = (dates[change_idx], dates[-1])
    return segment_before, change_date, segment_after


def add_segment_regions(fig, segment_before, change_date, segment_after):
    """在时序图上添加铺垫/冲突/结局区域（仅当存在实际分段时）。"""
    if segment_before is None or segment_before[0] is None:
        return
    x0_before, x1_before = segment_before[0], segment_before[1]
    fig.add_vrect(x0=x0_before, x1=x1_before, fillcolor="lightblue", opacity=0.1, line_width=0, annotation_text="铺垫", annotation_position="top left")
    if change_date is not None:
        fig.add_vline(x=change_date, line_dash="dash", line_color="orange")
    if segment_after is not None and segment_after[0] is not None and segment_after[1] is not None:
        fig.add_vrect(x0=segment_after[0], x1=segment_after[1], fillcolor="lightgreen", opacity=0.1, line_width=0, annotation_text="结局", annotation_position="top left")


@st.cache_data
def load_data():
    kpi = pd.read_csv(PROCESSED_DIR / "kpi.csv", encoding="utf-8")
    peak_7d = pd.read_csv(PROCESSED_DIR / "peak_7d.csv", encoding="utf-8")
    peak_48h = pd.read_csv(PROCESSED_DIR / "peak_48h.csv", encoding="utf-8")
    daily_usage = pd.read_csv(PROCESSED_DIR / "daily_usage.csv", encoding="utf-8")
    new_users = pd.read_csv(PROCESSED_DIR / "new_users.csv", encoding="utf-8")
    return kpi, peak_7d, peak_48h, daily_usage, new_users


def load_release_info():
    p = PROCESSED_DIR / "release_info.csv"
    if p.exists():
        try:
            df = pd.read_csv(p, encoding="utf-8")
            if not df.empty and "region" in df.columns and "release_date" in df.columns:
                return dict(zip(df["region"], df["release_date"].astype(str)))
        except Exception:
            pass
    return {"国内": "2026-02-09", "海外": "2026-02-11"}


def add_release_vlines(fig, release_dates):
    if not release_dates:
        return
    for date_str, _ in release_dates:
        fig.add_vline(x=date_str, line_dash="dash", line_color="gray", line_width=1)


def build_narrative(kpi_sel, peak_7d_sel, peak_48h_sel, daily_usage_sel, new_users_sel, selected_products, show_real_users_only=False):
    """基于当前筛选数据生成叙事性解读与建议。"""
    if show_real_users_only:
        if not new_users_sel.empty and "new_ai_users" in new_users_sel.columns:
            total_users = int(new_users_sel["new_ai_users"].sum())
            by_product_users = new_users_sel.groupby("product_line")["new_ai_users"].sum()
        else:
            total_users = 0
            by_product_users = pd.Series(dtype=float)
    else:
        total_users = int(kpi_sel["value"].sum())
        by_product_users = None
    observation_period = ""
    all_dates = []
    for df in [peak_7d_sel, daily_usage_sel, new_users_sel]:
        if not df.empty and "date" in df.columns:
            all_dates.extend(df["date"].astype(str).tolist())
    if all_dates:
        observation_period = f"{min(all_dates)} 至 {max(all_dates)}"
    if total_users <= 0:
        return {
            "summary": "当前筛选下暂无用户量数据。",
            "findings": [],
            "suggestions": ["请检查数据或调整产品线筛选。"],
            "observation_period": observation_period,
            "setup_sentence": "当前筛选下暂无时序数据，无法划分铺垫区间。",
            "conflict_sentence": "",
            "resolution_sentence": "",
            "change_date": None,
            "segment_before": (None, None),
            "segment_after": None,
        }

    # ----- 铺垫-冲突-结果：基于 DAU 或新增序列检测拐点（仅用实际数据）-----
    series_dates = None
    series_values = None
    series_label = ""
    if not daily_usage_sel.empty:
        agg_dau = daily_usage_sel.groupby("date")["dau"].sum()
        agg_dau = agg_dau.sort_index()
        series_dates = agg_dau.index.astype(str).tolist()
        series_values = agg_dau.tolist()
        series_label = "日活"
    elif not new_users_sel.empty:
        agg_new = new_users_sel.groupby("date")["new_ai_users"].sum()
        agg_new = agg_new.sort_index()
        series_dates = agg_new.index.astype(str).tolist()
        series_values = agg_new.tolist()
        series_label = "新增用户"

    segment_before, change_date, segment_after = (None, None), None, None
    if series_dates and series_values:
        segment_before, change_date, segment_after = detect_change_segments(series_dates, series_values)

    def _mean_in_range(dates, values, start, end):
        if start is None or end is None or not dates or not values:
            return None
        total, cnt = 0, 0
        for d, v in zip(dates, values):
            if start <= d <= end:
                total += v
                cnt += 1
        return round(total / cnt, 1) if cnt else None

    def _value_at_date(dates, values, d):
        for i, dt in enumerate(dates):
            if dt == d:
                return values[i]
        return None

    setup_sentence = ""
    conflict_sentence = ""
    resolution_sentence = ""

    if segment_before[0] is not None and segment_before[1] is not None and series_dates and series_values:
        mean_before = _mean_in_range(series_dates, series_values, segment_before[0], segment_before[1])
        if mean_before is not None:
            setup_sentence = f"**铺垫**：观察期前段（{segment_before[0]} 至 {segment_before[1]}）{series_label}相对平稳，日均约 {mean_before}。"
        else:
            setup_sentence = f"**铺垫**：观察期前段（{segment_before[0]} 至 {segment_before[1]}）为变化前区间。"

        if change_date is not None and segment_after is not None:
            val_at = _value_at_date(series_dates, series_values, change_date)
            mean_before_val = _mean_in_range(series_dates, series_values, segment_before[0], segment_before[1])
            if val_at is not None and mean_before_val is not None and mean_before_val != 0:
                pct = round((val_at - mean_before_val) / mean_before_val * 100, 1)
                direction = "上升" if pct > 0 else "下降"
                conflict_sentence = f"**冲突**：{change_date} 出现明显拐点，当日{series_label}为 {val_at}，较前段均值 {mean_before_val} {direction} {abs(pct)}%（数据表现）。"
            else:
                conflict_sentence = f"**冲突**：{change_date} 出现明显拐点，当日{series_label}为 {val_at}，与前段形成转折（数据表现）。"

            mean_after = _mean_in_range(series_dates, series_values, segment_after[0], segment_after[1])
            if mean_after is not None and mean_before_val is not None:
                resolution_sentence = f"**结局**：拐点后（{segment_after[0]} 至 {segment_after[1]}）日均{series_label}约 {mean_after}，较前段均值 {mean_before_val} 抬升。" if mean_after >= mean_before_val else f"**结局**：拐点后（{segment_after[0]} 至 {segment_after[1]}）日均{series_label}约 {mean_after}，较前段均值 {mean_before_val} 回落。"
            else:
                resolution_sentence = f"**结局**：拐点后（{segment_after[0]} 至 {segment_after[1]}）为结果区间，数据见上图。"
        else:
            conflict_sentence = "**冲突**：观测期内整体平稳，未发现明显拐点；或数据点不足，未检测到拐点。"
            resolution_sentence = "**结局**：整段观测期呈平稳态势，无拐点后区间。"
    else:
        setup_sentence = "**铺垫**：时序数据不足，无法划分铺垫区间。"
        conflict_sentence = "**冲突**：数据点不足，未检测到拐点。"
        resolution_sentence = "**结局**：暂无。"

    # ----- 统一计算关键指标（供 findings 与 suggestions 共用）-----
    lead_product, lead_count, lead_pct = None, None, None
    if len(selected_products) >= 2:
        if by_product_users is not None:
            a = float(by_product_users.get(selected_products[0], 0))
            b = float(by_product_users.get(selected_products[1], 0))
        else:
            a = kpi_sel[kpi_sel["product_line"] == selected_products[0]]["value"].sum()
            b = kpi_sel[kpi_sel["product_line"] == selected_products[1]]["value"].sum()
        if a + b > 0:
            lead_product = selected_products[0] if a >= b else selected_products[1]
            lead_count = int(a if lead_product == selected_products[0] else b)
            lead_pct = round(100 * lead_count / total_users, 1)

    dau_mean, max_dau, max_dau_date = None, None, None
    if not daily_usage_sel.empty:
        dau_mean = float(daily_usage_sel.groupby("date")["dau"].sum().mean())
        max_dau = int(daily_usage_sel["dau"].max())
        max_dau_date = daily_usage_sel.loc[daily_usage_sel["dau"].idxmax(), "date"]

    total_new, zero_days, new_peak = None, None, None
    if not new_users_sel.empty:
        new_by_date = new_users_sel.groupby("date")["new_ai_users"].sum()
        total_new = int(new_by_date.sum())
        zero_days = int((new_by_date == 0).sum())
        new_peak = int(new_users_sel["new_ai_users"].max())

    peak_date, peak_val = None, None
    if not peak_7d_sel.empty:
        agg7 = peak_7d_sel.groupby("date", as_index=False)["task_cnt"].sum()
        if not agg7.empty:
            peak_date = agg7.loc[agg7["task_cnt"].idxmax(), "date"]
            peak_val = int(agg7["task_cnt"].max())

    busy_slot = None
    if not peak_48h_sel.empty and peak_48h_sel["task_cnt"].sum() > 0:
        agg48 = peak_48h_sel.groupby("hour_slot")["task_cnt"].sum()
        busy_slot = agg48.idxmax()

    # ----- 摘要（保持不变）-----
    product_breakdown = []
    for p in selected_products:
        if by_product_users is not None:
            v = float(by_product_users.get(p, 0))
        else:
            v = kpi_sel[kpi_sel["product_line"] == p]["value"].sum()
        if v > 0:
            pct = round(100 * v / total_users, 1)
            product_breakdown.append(f"{p} {int(v)} 人（{pct}%）")
    summary_parts = [f"本周期内，所选产品线**累计用户共 {total_users} 人**"]
    if product_breakdown:
        summary_parts.append("，其中 " + "、".join(product_breakdown) + "。")
    else:
        summary_parts.append("。")
    if peak_date is not None:
        summary_parts.append(f"**近7天功能使用高峰**出现在 {peak_date}（当日任务量 {peak_val}）。")
    if max_dau is not None:
        summary_parts.append(f"**日活峰值**为 {max_dau} 人（{max_dau_date}）。")
    if total_new is not None:
        summary_parts.append(f"观测期内**新增用户合计 {total_new} 人**，单日新增最高 {new_peak} 人。")
    summary = " ".join(summary_parts)

    # ----- 主要发现：结论 + 数据 + 业务含义 -----
    findings = []
    if lead_product is not None:
        findings.append(
            f"**产品线对比**：{lead_product} 领先（共 {lead_count} 人，占 {lead_pct}%），是当前主要用户来源，资源倾斜有数据支撑；可考虑从该线向另一条线导流拉新。"
        )
    if dau_mean is not None:
        peak_part = f"，峰值 {max_dau} 人（{max_dau_date}）" if max_dau is not None else ""
        findings.append(
            f"**活跃度**：观测期内日均活跃约 {dau_mean:.1f} 人{peak_part}；整体规模仍小、波动明显，留存与习惯尚未稳定，需通过活动与触达提升。"
        )
    if zero_days is not None and zero_days > 0:
        findings.append(
            f"**新增节奏**：观测期内共 {zero_days} 天零新增、累计新增 {total_new} 人；拉新不稳定，需排查曝光与转化漏斗。"
        )
    if busy_slot is not None:
        findings.append(
            f"**48 小时高峰**：使用集中在「{busy_slot}」时段；建议在该时段保障服务容量与稳定性，并可做轻量推送以提升转化。"
        )

    # ----- 建议下一步：由数据与发现动态生成（依据 + 具体动作）-----
    suggestions = []
    if zero_days is not None and zero_days > 0:
        suggestions.append(
            f"**拉新**：基于观测期内 {zero_days} 天零新增、累计 {total_new} 人新增，建议本周内完成各渠道曝光与转化漏斗拆解，并设定下月拉新目标、落实到渠道负责人。"
        )
    if busy_slot is not None:
        suggestions.append(
            f"**资源与节奏**：使用集中在「{busy_slot}」，建议在该时段保证服务容量并安排轻量推送，以提升转化。"
        )
    if lead_product is not None:
        other = [p for p in selected_products if p != lead_product]
        other_line = other[0] if other else "另一条线"
        suggestions.append(
            f"**产品线**：{lead_product} 当前领先（{lead_count} 人，{lead_pct}%），建议优先保障该线资源与体验，并设计向{other_line}的导流实验（入口、活动或文案）。"
        )
    if dau_mean is not None:
        suggestions.append(
            f"**活跃与留存**：日均活跃约 {dau_mean:.1f} 人，建议设定留存与唤醒节奏（如每周一次触达），并跟踪次周留存以评估活动效果。"
        )
    if peak_date is not None:
        suggestions.append(
            f"**近 7 天节奏**：高峰日在 {peak_date}（任务量 {peak_val}），建议将功能与运营资源向该日前后集中，低峰日做定向召回（推送、活动）。"
        )
    if not suggestions:
        suggestions.append("当前数据下暂无强数据支撑的专项建议，可结合上方图表做人工解读并设定下期复盘指标。")

    return {
        "summary": summary,
        "findings": findings,
        "suggestions": suggestions,
        "observation_period": observation_period,
        "setup_sentence": setup_sentence,
        "conflict_sentence": conflict_sentence,
        "resolution_sentence": resolution_sentence,
        "change_date": change_date,
        "segment_before": segment_before,
        "segment_after": segment_after,
        # 供管理层视图使用的关键数值
        "total_users": total_users,
        "dau_mean": dau_mean,
        "max_dau": max_dau,
        "total_new": total_new,
        "zero_days": zero_days,
        "new_peak": new_peak,
        "busy_slot": busy_slot,
        "lead_product": lead_product,
        "lead_count": lead_count,
        "lead_pct": lead_pct,
    }


def compute_status_tags(narrative):
    """
    基于 narrative 中的关键数值，生成给管理层看的「规模 / 活跃 / 拉新」标签。
    仅做粗颗粒度归类，避免过度解读具体数值。
    """
    total_users = narrative.get("total_users")
    dau_mean = narrative.get("dau_mean")
    max_dau = narrative.get("max_dau")
    total_new = narrative.get("total_new")
    zero_days = narrative.get("zero_days")

    # 规模标签
    if not isinstance(total_users, (int, float)) or total_users is None or total_users <= 0:
        scale = "规模：暂无数据"
    elif total_users < 500:
        scale = "规模：小规模试运行"
    elif total_users < 5000:
        scale = "规模：在扩张中"
    else:
        scale = "规模：已成型"

    # 活跃标签（粗略看日均活跃与峰值）
    if dau_mean is None:
        active = "活跃：暂无数据"
    else:
        if max_dau and dau_mean and max_dau / max_dau if max_dau else 1:
            # 使用日均活跃占总用户的比例粗略判断渗透
            if total_users and total_users > 0:
                penetration = dau_mean / total_users
                if penetration >= 0.5:
                    active = "活跃：高渗透"
                elif penetration >= 0.2:
                    active = "活跃：中等"
                else:
                    active = "活跃：待提升"
            else:
                active = "活跃：待观察"
        else:
            active = "活跃：待观察"

    # 拉新标签
    if total_new is None:
        growth = "拉新：暂无数据"
    elif total_new == 0:
        growth = "拉新：暂无新增"
    elif zero_days is not None and zero_days > 0:
        growth = "拉新：节奏不稳定"
    else:
        growth = "拉新：节奏较稳定"

    return scale, active, growth


def main():
    st.set_page_config(page_title="AI 分析看板", layout="wide")
    st.title("AI 篮球 / 足球分析看板")
    st.caption("管理层视图：快速了解规模、活跃与拉新表现")
    st.markdown("本报告围绕三个问题：**现在规模与健康度如何？用户什么时候在用？下一步要做什么？** 来组织数据与结论。")

    if not (PROCESSED_DIR / "kpi.csv").exists():
        st.error("未找到数据，请先运行: python scripts/extract_pdf_data.py && python scripts/clean_and_model.py")
        return

    kpi, peak_7d, peak_48h, daily_usage, new_users = load_data()

    # Product line filter（报告来自本地 PDF 数据，无需侧栏时间选择）
    product_options = list(kpi["product_line"].unique())
    view_mode = st.sidebar.selectbox(
        "预设视图",
        ["管理层汇总视图", "自定义筛选（高级）"],
        index=0,
        help="管理层汇总视图：推荐设置；自定义筛选：按产品线与数据范围自由组合。",
    )
    selected_products = st.sidebar.multiselect("产品线", product_options, default=product_options)

    data_range = st.sidebar.radio(
        "数据范围",
        ["展示全量数据", "仅展示上线后真实用户数据"],
        index=1 if view_mode == "管理层汇总视图" else 0,
    )
    show_real_users_only = data_range == "仅展示上线后真实用户数据"

    # 预设视图下的有效筛选
    if view_mode == "管理层汇总视图":
        effective_selected_products = product_options
        effective_show_real_users_only = True
    else:
        effective_selected_products = selected_products
        effective_show_real_users_only = show_real_users_only
    release_by_region = load_release_info()
    cutoff_date = release_by_region.get("国内", "2026-02-09")

    if not effective_selected_products:
        st.warning("请至少选择一条产品线")
        return

    kpi_sel = kpi[kpi["product_line"].isin(effective_selected_products)]
    peak_7d_sel = peak_7d[peak_7d["product_line"].isin(effective_selected_products)]
    peak_48h_sel = peak_48h[peak_48h["product_line"].isin(effective_selected_products)]
    daily_usage_sel = daily_usage[daily_usage["product_line"].isin(effective_selected_products)]
    new_users_sel = new_users[new_users["product_line"].isin(effective_selected_products)]

    if effective_show_real_users_only:
        if "date" in daily_usage_sel.columns:
            daily_usage_sel = daily_usage_sel[daily_usage_sel["date"] >= cutoff_date]
        if "date" in new_users_sel.columns:
            new_users_sel = new_users_sel[new_users_sel["date"] >= cutoff_date]
        if "date" in peak_7d_sel.columns:
            peak_7d_sel = peak_7d_sel[peak_7d_sel["date"] >= cutoff_date]
        if not peak_48h_sel.empty and "hour_slot" in peak_48h_sel.columns:
            try:
                slot_dates = pd.to_datetime(peak_48h_sel["hour_slot"], errors="coerce")
                peak_48h_sel = peak_48h_sel.loc[slot_dates.dt.strftime("%Y-%m-%d") >= cutoff_date]
            except Exception:
                pass

    # ----- 核心结论（叙事摘要）-----
    narrative = build_narrative(
        kpi_sel,
        peak_7d_sel,
        peak_48h_sel,
        daily_usage_sel,
        new_users_sel,
        effective_selected_products,
        show_real_users_only=effective_show_real_users_only,
    )
    # 观察期：优先使用 PDF 报告时间范围（observation_period.csv），与 start_time/end_time 一致
    obs_file = PROCESSED_DIR / "observation_period.csv"
    if obs_file.exists():
        try:
            obs_df = pd.read_csv(obs_file, encoding="utf-8")
            if not obs_df.empty and "start_date" in obs_df.columns and "end_date" in obs_df.columns:
                obs = f"{obs_df['start_date'].iloc[0]} 至 {obs_df['end_date'].iloc[0]}"
            else:
                obs = narrative.get("observation_period", "").strip()
        except Exception:
            obs = narrative.get("observation_period", "").strip()
    else:
        obs = narrative.get("observation_period", "").strip()
    if obs:
        st.info(f"**观察期**：{obs}")
        st.caption("本功能于国内 2月9日、海外 2月11日 正式给到用户。")
        if not effective_show_real_users_only:
            st.caption("全量数据模式下，下方「每日使用次数」「每日新增用户」图中竖线为该时间点。")
    else:
        st.caption("观察期：暂无日期数据（请先运行 scripts/clean_and_model.py 生成 observation_period.csv）")
    if effective_show_real_users_only:
        st.info("当前 KPI、结论与图表均仅含上线日（国内 2月9日 / 海外 2月11日）起数据。")

    # 本期结论标签栏
    scale_tag, active_tag, growth_tag = compute_status_tags(narrative)
    tag_cols = st.columns(3)
    tag_cols[0].markdown(f"**{scale_tag}**")
    tag_cols[1].markdown(f"**{active_tag}**")
    tag_cols[2].markdown(f"**{growth_tag}**")

    # 管理层总览：左侧结论，右侧行动
    st.markdown("---")
    overview_left, overview_right = st.columns([2, 1])
    with overview_left:
        st.subheader("管理层总览")
        st.markdown(narrative["summary"])
        key_findings = narrative.get("findings", [])[:2]
        if key_findings:
            st.markdown("**关键结论**")
            for f in key_findings:
                st.markdown(f"- {f}")
    with overview_right:
        st.subheader("下一步行动")
        suggestions = narrative.get("suggestions", [])[:5]
        if suggestions:
            for s in suggestions:
                st.markdown(f"- {s}")
        else:
            st.caption("当前数据下暂无强数据支撑的专项行动建议。")

    with st.expander("📌 叙事分析（铺垫-冲突-结果）", expanded=False):
        if narrative.get("setup_sentence"):
            st.markdown(narrative["setup_sentence"])
        if narrative.get("conflict_sentence"):
            st.markdown(narrative["conflict_sentence"])
        if narrative.get("resolution_sentence"):
            st.markdown(narrative["resolution_sentence"])

    # ----- KPI -----
    if effective_show_real_users_only:
        st.subheader("上线后累计新增用户")
        st.caption("仅统计上线日（国内 2月9日 / 海外 2月11日）起新增用户，与核心结论一致。")
        real_new_by_product = new_users_sel.groupby("product_line")["new_ai_users"].sum() if not new_users_sel.empty else pd.Series(dtype=float)
        cols = st.columns(len(effective_selected_products))
        for i, prod in enumerate(effective_selected_products):
            val = int(real_new_by_product.get(prod, 0))
            cols[i].metric(prod, val)
    else:
        st.subheader("使用总用户量 (Total AI Analysis Users)")
        st.caption("各产品线累计用户数，与上方管理层总览中的「累计用户」一致，用于快速对比规模。")
        cols = st.columns(len(effective_selected_products))
        for i, prod in enumerate(effective_selected_products):
            val = kpi_sel[kpi_sel["product_line"] == prod]["value"].iloc[0]
            cols[i].metric(prod, int(val))

    # ----- Row 1: Peak 7d + Peak 48h -----
    st.markdown("---")
    st.markdown("#### 一、使用节奏：近7天与近48小时")
    st.caption("回答「用户什么时候在用？」：左图看近一周的高峰日与主力功能，右图看近 48 小时内的使用高峰时段，便于安排运营与容量。")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("近 7 天：哪天最忙，谁在贡献任务？")
        # Stack by feature_id; if multiple products selected, sum task_cnt across products per date+feature
        agg_7d = peak_7d_sel.groupby(["date", "feature_id"], as_index=False)["task_cnt"].sum()
        if not agg_7d.empty:
            fig_7d = px.bar(
                agg_7d, x="date", y="task_cnt", color="feature_id",
                title="task_cnt by date (stacked)", barmode="stack",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_7d.update_layout(xaxis_title="日期", yaxis_title="task_cnt", showlegend=True)
            st.plotly_chart(fig_7d, use_container_width=True)
        else:
            st.info("暂无近7天数据")

    with c2:
        st.subheader("近 48 小时：使用高峰在什么时候？")
        if not peak_48h_sel.empty:
            agg_48h = peak_48h_sel.groupby("hour_slot", as_index=False)["task_cnt"].sum()
            fig_48h = px.line(agg_48h, x="hour_slot", y="task_cnt", markers=True)
            fig_48h.update_layout(xaxis_title="hour_slot", yaxis_title="task_cnt")
            st.plotly_chart(fig_48h, use_container_width=True)
        else:
            st.info("暂无近48小时数据")
    st.caption("_左：按日期与功能堆叠的任务量，可看出高峰日与主力功能。右：按小时的使用量，用于识别高峰时段。_")

    # ----- Row 2: Daily usage (3 lines) + New users -----
    st.markdown("---")
    st.markdown("#### 二、活跃与增长：每日使用与新增")
    st.caption("左图同时看「平均每用户每日使用次数」「总使用次数」「日活用户数」三条线，综合判断粘性与规模；右图看每日新增用户，用于评估拉新效果与节奏是否稳定。")
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("每日使用次数 (Daily Usage Count)")
        if not daily_usage_sel.empty:
            agg_daily = daily_usage_sel.groupby("date", as_index=False).agg(
                avg_daily_usage_per_user=("avg_daily_usage_per_user", "mean"),
                total_usage_count=("total_usage_count", "sum"),
                dau=("dau", "sum"),
            )
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(x=agg_daily["date"], y=agg_daily["avg_daily_usage_per_user"], name="平均每用户每日使用次数", mode="lines+markers"))
            fig_daily.add_trace(go.Scatter(x=agg_daily["date"], y=agg_daily["total_usage_count"], name="总使用次数", mode="lines+markers"))
            fig_daily.add_trace(go.Scatter(x=agg_daily["date"], y=agg_daily["dau"], name="日活用户数", mode="lines+markers"))
            fig_daily.update_layout(xaxis_title="日期", yaxis_title="Count", legend=dict(orientation="h"))
            add_segment_regions(fig_daily, narrative["segment_before"], narrative["change_date"], narrative["segment_after"])
            if not show_real_users_only:
                add_release_vlines(fig_daily, [(release_by_region.get("国内", "2026-02-09"), "国内"), (release_by_region.get("海外", "2026-02-11"), "海外")])
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("暂无每日使用数据")

    with c4:
        st.subheader("每日新增用户 (New User By Day)")
        if not new_users_sel.empty:
            agg_new = new_users_sel.groupby("date", as_index=False)["new_ai_users"].sum()
            fig_new = px.line(agg_new, x="date", y="new_ai_users", markers=True)
            fig_new.update_layout(xaxis_title="日期", yaxis_title="new_ai_users")
            add_segment_regions(fig_new, narrative["segment_before"], narrative["change_date"], narrative["segment_after"])
            if not effective_show_real_users_only:
                add_release_vlines(fig_new, [(release_by_region.get("国内", "2026-02-09"), "国内"), (release_by_region.get("海外", "2026-02-11"), "海外")])
            st.plotly_chart(fig_new, use_container_width=True)

            # 自动生成的拉新结论，帮助管理层快速读懂新增节奏
            zero_days = narrative.get("zero_days")
            total_new = narrative.get("total_new")
            if total_new is not None:
                if zero_days is not None and zero_days > 0:
                    st.caption(f"观测期内共新增 {total_new} 人，其中有 {zero_days} 天为零新增，拉新节奏偏不稳定。")
                else:
                    st.caption(f"观测期内共新增 {total_new} 人，几乎每天都有新增，拉新节奏相对稳定。")
        else:
            st.info("暂无每日新增用户数据")
    st.caption("_左：人均使用频次 + 总使用次数 + 日活，用于综合判断粘性与规模。右：每日新增用户曲线，可与推广动作对照。_" + (" 竖线：国内 2月9日、海外 2月11日（上线日）。" if not effective_show_real_users_only else ""))

    # ----- 数据解读与建议（叙事化定性）-----
    st.markdown("---")
    st.subheader("数据解读与建议")
    st.caption("基于当前筛选数据提炼的主要发现与可执行建议，便于形成闭环决策。")
    st.caption("_以下发现与建议均基于观测期数据；建议按优先级推进，并可在下期报告中复盘。_")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**主要发现**")
        for f in narrative["findings"]:
            st.markdown(f"- {f}")
        if not narrative["findings"]:
            st.markdown("- 当前数据下暂无额外发现，可结合上方图表做人工解读。")
    with col_b:
        st.markdown("**建议下一步**")
        for s in narrative["suggestions"]:
            st.markdown(f"- {s}")

    # ----- 运营 & 购买详情 / 用户反馈等明细（来自复盘 PDF）-----
    summary_path = PROCESSED_DIR / "product_region_summary.csv"
    purchase_path = PROCESSED_DIR / "purchase_details.csv"
    cancel_path = PROCESSED_DIR / "cancel_details.csv"
    has_summary = summary_path.exists()
    has_purchase = purchase_path.exists()
    has_cancel = cancel_path.exists()

    # 管理层视图下默认收起，给运营/产品的明细按需展开
    if has_summary or has_purchase or has_cancel:
        st.markdown("---")
        with st.expander("运营 & 购买详情（给运营/产品看）", expanded=view_mode != "管理层汇总视图"):
            st.caption("用于支持拉新与转化复盘的区域汇总、购买与取消明细。")
            if has_summary:
                st.markdown("**足球/篮球 AI 分析相关数据**")
                st.caption("来源：足篮球AI分析上线2周复盘 PDF，按产品线与区域汇总。")
                try:
                    summary_df = pd.read_csv(summary_path, encoding="utf-8")
                    if not summary_df.empty and "product_line" in summary_df.columns and "region" in summary_df.columns:
                        for pl in summary_df["product_line"].unique():
                            st.markdown(f"**{pl}**")
                            sub = summary_df[summary_df["product_line"] == pl]
                            st.dataframe(sub, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.caption(f"读取汇总表失败: {e}")
            if has_purchase or has_cancel:
                st.markdown("---")
                st.markdown("**购买/取消详情（来自复盘）**")
                if has_purchase:
                    try:
                        purchase_df = pd.read_csv(purchase_path, encoding="utf-8")
                        if "region" in purchase_df.columns:
                            for r in purchase_df["region"].unique():
                                st.markdown(f"**{r}用户购买详情**")
                                st.dataframe(purchase_df[purchase_df["region"] == r], use_container_width=True, hide_index=True)
                        else:
                            st.dataframe(purchase_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.caption(f"读取购买详情失败: {e}")
                if has_cancel:
                    try:
                        cancel_df = pd.read_csv(cancel_path, encoding="utf-8")
                        st.markdown("**取消支付详情**")
                        st.dataframe(cancel_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.caption(f"读取取消详情失败: {e}")

    feedback_path = PROCESSED_DIR / "insights_feedback.txt"
    if feedback_path.exists():
        with st.expander("用户反馈与分析备注（给分析/产品看）", expanded=view_mode != "管理层汇总视图"):
            st.caption("用于还原用户主观反馈和分析备注，支撑对数据的定性判断。")
            try:
                text = feedback_path.read_text(encoding="utf-8")
                if text.strip():
                    st.markdown(text.strip())
                else:
                    st.caption("暂无内容")
            except Exception as e:
                st.caption(f"读取失败: {e}")

    # ----- Data source -----
    st.divider()
    st.caption("数据来源：根目录 AI 篮球/足球分析看板 PDF。")


if __name__ == "__main__":
    main()
