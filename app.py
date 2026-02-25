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


@st.cache_data
def load_data():
    kpi = pd.read_csv(PROCESSED_DIR / "kpi.csv", encoding="utf-8")
    peak_7d = pd.read_csv(PROCESSED_DIR / "peak_7d.csv", encoding="utf-8")
    peak_48h = pd.read_csv(PROCESSED_DIR / "peak_48h.csv", encoding="utf-8")
    daily_usage = pd.read_csv(PROCESSED_DIR / "daily_usage.csv", encoding="utf-8")
    new_users = pd.read_csv(PROCESSED_DIR / "new_users.csv", encoding="utf-8")
    return kpi, peak_7d, peak_48h, daily_usage, new_users


def build_narrative(kpi_sel, peak_7d_sel, peak_48h_sel, daily_usage_sel, new_users_sel, selected_products):
    """基于当前筛选数据生成叙事性解读与建议。"""
    total_users = int(kpi_sel["value"].sum())
    observation_period = ""
    all_dates = []
    for df in [peak_7d_sel, daily_usage_sel, new_users_sel]:
        if not df.empty and "date" in df.columns:
            all_dates.extend(df["date"].astype(str).tolist())
    if all_dates:
        observation_period = f"{min(all_dates)} 至 {max(all_dates)}"
    if total_users <= 0:
        return {"summary": "当前筛选下暂无用户量数据。", "findings": [], "suggestions": ["请检查数据或调整产品线筛选。"], "observation_period": observation_period}
    product_breakdown = []
    for p in selected_products:
        v = kpi_sel[kpi_sel["product_line"] == p]["value"].sum()
        if v > 0:
            pct = round(100 * v / total_users, 1)
            product_breakdown.append(f"{p} {int(v)} 人（{pct}%）")
    summary_parts = [f"本周期内，所选产品线**累计用户共 {total_users} 人**"]
    if product_breakdown:
        summary_parts.append("，其中 " + "、".join(product_breakdown) + "。")
    else:
        summary_parts.append("。")
    if not peak_7d_sel.empty:
        agg7 = peak_7d_sel.groupby("date", as_index=False)["task_cnt"].sum()
        if not agg7.empty:
            peak_date = agg7.loc[agg7["task_cnt"].idxmax(), "date"]
            peak_val = int(agg7["task_cnt"].max())
            summary_parts.append(f"**近7天功能使用高峰**出现在 {peak_date}（当日任务量 {peak_val}）。")
    if not daily_usage_sel.empty:
        max_dau = int(daily_usage_sel["dau"].max())
        max_dau_date = daily_usage_sel.loc[daily_usage_sel["dau"].idxmax(), "date"]
        summary_parts.append(f"**日活峰值**为 {max_dau} 人（{max_dau_date}）。")
    if not new_users_sel.empty:
        total_new = int(new_users_sel["new_ai_users"].sum())
        new_peak = int(new_users_sel["new_ai_users"].max())
        summary_parts.append(f"观测期内**新增用户合计 {total_new} 人**，单日新增最高 {new_peak} 人。")
    summary = " ".join(summary_parts)
    findings = []
    if len(selected_products) >= 2:
        a = kpi_sel[kpi_sel["product_line"] == selected_products[0]]["value"].sum()
        b = kpi_sel[kpi_sel["product_line"] == selected_products[1]]["value"].sum()
        if a + b > 0:
            lead = selected_products[0] if a >= b else selected_products[1]
            findings.append(f"**产品线对比**：{lead} 用户量更多，可优先给该产品线配资源，或从该线往另一条线导流拉新。")
    if not daily_usage_sel.empty:
        dau_mean = daily_usage_sel.groupby("date")["dau"].sum().mean()
        findings.append(f"**活跃度**：观测期内日均活跃约 {dau_mean:.1f} 人，日活有高有低，可通过活动、提醒提升留存。")
    if not new_users_sel.empty:
        new_by_date = new_users_sel.groupby("date")["new_ai_users"].sum()
        zero_days = (new_by_date == 0).sum()
        if zero_days > 0:
            findings.append(f"**新增节奏**：{int(zero_days)} 天没有新增用户，拉新多集中在少数几天或渠道，建议看下曝光和转化漏斗。")
    if not peak_48h_sel.empty and peak_48h_sel["task_cnt"].sum() > 0:
        agg48 = peak_48h_sel.groupby("hour_slot")["task_cnt"].sum()
        busy_slot = agg48.idxmax()
        findings.append(f"**48 小时高峰**：使用多集中在 {busy_slot} 左右，可在此时间段保证服务稳定或做轻量推送。")
    suggestions = [
        "**近 7 天功能使用**：看哪几天、哪些功能用得多，据此排功能优先级和资源；使用偏低的日期可做定向召回（推送、活动）。",
        "**每日使用与日活**：用趋势判断用户是否养成习惯；出现明显下滑时，可设计挽留动作（提醒、福利等）。",
        "**每日新增用户**：和实际推广动作对照，找出拉新效果好的渠道和时段，沉淀成可复用的拉新流程。",
    ]
    return {"summary": summary, "findings": findings, "suggestions": suggestions, "observation_period": observation_period}


def main():
    st.set_page_config(page_title="AI 分析看板", layout="wide")
    st.title("AI 篮球 / 足球分析看板")
    st.caption("用户行为与数据表现 — 定性定量分析")
    st.markdown("本报告从**用户规模、使用节奏、活跃与增长**三个维度呈现数据，并在文末给出解读与建议，便于产品决策。")

    if not (PROCESSED_DIR / "kpi.csv").exists():
        st.error("未找到数据，请先运行: python scripts/extract_pdf_data.py && python scripts/clean_and_model.py")
        return

    kpi, peak_7d, peak_48h, daily_usage, new_users = load_data()

    # Product line filter（报告来自本地 PDF 数据，无需侧栏时间选择）
    product_options = list(kpi["product_line"].unique())
    selected_products = st.sidebar.multiselect("产品线", product_options, default=product_options)

    if not selected_products:
        st.warning("请至少选择一条产品线")
        return

    kpi_sel = kpi[kpi["product_line"].isin(selected_products)]
    peak_7d_sel = peak_7d[peak_7d["product_line"].isin(selected_products)]
    peak_48h_sel = peak_48h[peak_48h["product_line"].isin(selected_products)]
    daily_usage_sel = daily_usage[daily_usage["product_line"].isin(selected_products)]
    new_users_sel = new_users[new_users["product_line"].isin(selected_products)]

    # ----- 核心结论（叙事摘要）-----
    narrative = build_narrative(kpi_sel, peak_7d_sel, peak_48h_sel, daily_usage_sel, new_users_sel, selected_products)
    # 观察期：来自本地 PDF 数据的日期范围
    obs = narrative.get("observation_period", "").strip()
    if obs:
        st.info(f"**观察期**：{obs}")
    else:
        st.caption("观察期：暂无日期数据（请确认已导入含日期的数据并选择对应产品线）")
    with st.expander("📌 核心结论（点击展开）", expanded=True):
        st.markdown(narrative["summary"])

    # ----- KPI -----
    st.subheader("使用总用户量 (Total AI Analysis Users)")
    st.caption("各产品线累计用户数，与上方核心结论中的「累计用户」一致，用于快速对比规模。")
    cols = st.columns(len(selected_products))
    for i, prod in enumerate(selected_products):
        val = kpi_sel[kpi_sel["product_line"] == prod]["value"].iloc[0]
        cols[i].metric(prod, int(val))

    # ----- Row 1: Peak 7d + Peak 48h -----
    st.markdown("---")
    st.markdown("#### 一、使用节奏：近7天与近48小时")
    st.caption("下面两张图帮助回答「用户什么时候在用」：左图看近一周各日任务量分布与功能构成，右图看 48 小时内按小时的使用集中度，便于安排运营与容量。")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("功能使用高峰 - 近7天 (AI Feature Usage Peak - Last 7 Days)")
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
        st.subheader("功能使用高峰时段 - 近48小时 (Last 48 Hours)")
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
    st.caption("左图同时看「平均每用户每日使用次数」「总使用次数」「日活用户数」三条线，用于判断粘性与规模；右图看每日新增用户，用于评估拉新效果与节奏。")
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
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("暂无每日使用数据")

    with c4:
        st.subheader("每日新增用户 (New User By Day)")
        if not new_users_sel.empty:
            agg_new = new_users_sel.groupby("date", as_index=False)["new_ai_users"].sum()
            fig_new = px.line(agg_new, x="date", y="new_ai_users", markers=True)
            fig_new.update_layout(xaxis_title="日期", yaxis_title="new_ai_users")
            st.plotly_chart(fig_new, use_container_width=True)
        else:
            st.info("暂无每日新增用户数据")
    st.caption("_左：三条线分别对应人均使用频次、总使用次数、日活，可观察趋势是否健康。右：每日新增用户曲线，可与推广动作对照。_")

    # ----- 数据解读与建议（叙事化定性）-----
    st.markdown("---")
    st.subheader("数据解读与建议")
    st.caption("基于当前筛选数据提炼的主要发现与可执行建议，便于形成闭环决策。")
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

    # ----- Data source -----
    st.divider()
    st.caption("数据来源：根目录 AI 篮球/足球分析看板 PDF。")


if __name__ == "__main__":
    main()
