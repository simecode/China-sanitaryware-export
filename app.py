import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

MAPPING_FILE_NAME = "区域映射表.xlsx"

# ================= 内置数据映射 =================
DATASETS = {
    "6910 (陶瓷卫浴)": "data/default_6910.parquet",
    "水龙头/龙头": "data/default_faucet.parquet",
}

st.set_page_config(page_title="卫浴行业数据观察智库", layout="wide", page_icon="📊")

# ================= 全局样式 =================
st.markdown("""
<style>
/* 主背景 */
[data-testid="stAppViewContainer"] { background: #f0f4f8; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1a2740 0%,#243352 100%); }
[data-testid="stSidebar"] * { color: #e8edf5 !important; }
[data-testid="stSidebar"] .stMarkdown hr { border-color: #3a4d6e; }

/* 顶部大标题栏 */
.top-banner {
    background: linear-gradient(135deg,#1a2740 0%,#1e4d8c 60%,#2563b0 100%);
    border-radius: 12px; padding: 28px 36px 20px 36px;
    margin-bottom: 20px; box-shadow: 0 4px 18px rgba(30,77,140,.25);
}
.top-banner h1 { color:#ffffff; font-size:2rem; font-weight:700; margin:0; letter-spacing:.5px; }
.top-banner p  { color:#b8d0f0; font-size:.92rem; margin:6px 0 0 0; }

/* 指标卡片 */
[data-testid="metric-container"] {
    background:#ffffff; border-radius:10px;
    padding:16px 20px; border-left:4px solid #1e4d8c;
    box-shadow:0 2px 8px rgba(0,0,0,.07);
}
[data-testid="metric-container"] label { color:#6b7a99 !important; font-size:.82rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color:#1a2740 !important; font-weight:700; }

/* 分割线 */
hr { border-color:#d5dce8; }

/* dataframe */
[data-testid="stDataFrame"] { border-radius:8px; overflow:hidden; }

/* 页脚 */
.footer {
    background:linear-gradient(90deg,#1a2740,#1e4d8c);
    border-radius:10px; padding:18px 28px;
    margin-top:36px; color:#b8d0f0; font-size:.85rem;
    display:flex; justify-content:space-between; align-items:center;
}
.footer a { color:#7ec8f0; text-decoration:none; }
</style>
""", unsafe_allow_html=True)

# ================= 顶部标题栏 =================
st.markdown("""
<div class="top-banner">
  <h1>📊 卫浴与泛家居进出口多维洞察大屏</h1>
  <p>China Sanitaryware &amp; Home Export Intelligence · 数据来源：海关出口月度统计</p>
</div>
""", unsafe_allow_html=True)

# ================= 侧边栏 =================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 8px 0;">
      <div style="font-size:2rem;">📊</div>
      <div style="font-weight:700;font-size:1rem;color:#e8edf5;letter-spacing:.5px;">卫浴出口智库</div>
      <div style="font-size:.75rem;color:#7a9cc4;margin-top:2px;">China Sanitaryware Export</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.header("⚙️ 引擎配置")
    analysis_mode = st.radio("选择分析维度", ["同口径(前N月)对比", "月度动态演变", "历年全年(完整年份)"])

    st.markdown("---")
    st.header("🔑 AI 智库接入")
    openrouter_key = st.text_input("OpenRouter API Key", type="password")
    ai_model = st.selectbox("推理模型", ["openai/gpt-oss-120b:free", "deepseek/deepseek-chat:free"])

    st.markdown("---")
    st.header("📂 数据来源")
    use_builtin = st.checkbox("📊 使用内置默认数据（无需上传）", value=True)
    selected_dataset = (st.selectbox("选择内置数据集", options=list(DATASETS.keys()), index=0)
                        if use_builtin else None)

    st.markdown("---")
    st.markdown("""
    <div style="padding:12px 4px 4px 4px;">
      <div style="font-size:.78rem;color:#7a9cc4;margin-bottom:6px;letter-spacing:.5px;">ABOUT</div>
      <div style="color:#e8edf5;font-size:.88rem;font-weight:600;">👤 作者：sze</div>
      <div style="color:#b8d0f0;font-size:.82rem;margin-top:4px;">📱 交流：137-6076-5317</div>
      <div style="color:#7a9cc4;font-size:.75rem;margin-top:8px;">数据仅供研究参考，不构成商业建议</div>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data(use_builtin_flag, selected_ds):
    if not (use_builtin_flag and selected_ds):
        return None
    path = DATASETS.get(selected_ds)
    if not (path and os.path.exists(path)):
        return None
    try:
        df = pd.read_parquet(path)
    except Exception as e:
        st.error(f"内置数据读取失败: {e}")
        return None

    # —— 统一/兼容处理（即使是旧 parquet 也尽量纠正）——
    df["统计年份"] = pd.to_numeric(df["统计年份"].astype(str).str[:4], errors="coerce").astype("Int64")

    # 月份：优先用已有『月份』列；否则从『数据年月』推导（YYYY-MM / YYYYMM）
    if "月份" in df.columns:
        df["月份"] = pd.to_numeric(df["月份"], errors="coerce")
    elif "数据年月" in df.columns:
        s = df["数据年月"].astype(str).str.replace(r'[/.]', '-', regex=True)
        mm = s.str.extract(r'^20\d{2}-?(\d{1,2})$')[0]
        df["月份"] = pd.to_numeric(mm, errors="coerce")
    else:
        df["月份"] = np.nan
    df["月份"] = df["月份"].where((df["月份"] >= 1) & (df["月份"] <= 12))

    # 数据粒度：优先用已有列；否则按是否有有效月份推断
    if "数据粒度" not in df.columns:
        df["数据粒度"] = np.where(df["月份"].notna(), "月度", "年度")

    for c in ["所属区域", "注册地名称", "贸易伙伴名称"]:
        if c not in df.columns:
            df[c] = "未知"
    if "数量_统一" not in df.columns:
        df["数量_统一"] = 0.0
    return df


export_df = load_data(use_builtin, selected_dataset)
if export_df is None:
    st.info("👈 请确认 `data/` 目录下存在 Parquet 数据文件，且侧边栏已勾选内置数据。")
    st.stop()

month_df = export_df[export_df["数据粒度"] == "月度"].copy()
year_df = export_df[export_df["数据粒度"] == "年度"].copy()

# ================= 通用：同口径计算 =================
def same_period_pool(mp):
    """返回 (最新年份, 月份集合, 可对比年份列表, 同口径明细df)"""
    if mp.empty:
        return None, [], [], pd.DataFrame()
    latest = int(mp["统计年份"].max())
    latest_months = sorted(int(m) for m in mp.loc[mp["统计年份"] == latest, "月份"].dropna().unique())
    ok_years = []
    for yr, sub in mp.groupby("统计年份"):
        if set(latest_months).issubset(set(sub["月份"].dropna().astype(int).unique())):
            ok_years.append(int(yr))
    sp = mp[mp["统计年份"].isin(ok_years) & mp["月份"].isin(latest_months)].copy()
    return latest, latest_months, sorted(ok_years), sp


def yoy_table(df, group_cols):
    """同口径下：按年(+维度)汇总，逐年同比。"""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(group_cols + ["统计年份"], as_index=False).agg(
        {"金额_美元": "sum", "数量_统一": "sum"})
    g = g.sort_values(group_cols + ["统计年份"])
    g["出口单价（美元/单位）"] = np.where(g["数量_统一"] > 0,
                                   (g["金额_美元"] / g["数量_统一"]).round(4), np.nan)
    if group_cols:
        g["上年同期"] = g.groupby(group_cols)["金额_美元"].shift(1)
    else:
        g["上年同期"] = g["金额_美元"].shift(1)
    g["金额同比%"] = ((g["金额_美元"] - g["上年同期"]) / g["上年同期"].replace(0, np.nan) * 100).round(2)
    yt = g.groupby("统计年份")["金额_美元"].transform("sum")
    g["金额份额%"] = (g["金额_美元"] / yt * 100).round(2)
    return g


# ================= 主体 =================
if not month_df.empty:
    all_years = sorted(int(y) for y in month_df["统计年份"].dropna().unique())
    with st.sidebar:
        st.markdown("---")
        st.header("📅 年份筛选")
        selected_years = st.multiselect(
            "参与对比的年份", options=all_years, default=all_years)
    if not selected_years:
        selected_years = all_years

    # —— 基准年份/月份均由当前选中的年份动态决定 ——
    month_df_sel = month_df[month_df["统计年份"].isin(selected_years)]
    latest, months, ok_years, sp = same_period_pool(month_df_sel)
    prev_year = latest - 1
    prev_ok = prev_year in ok_years

    # 月份筛选：放侧边栏，影响全页所有指标/图表
    with st.sidebar:
        st.markdown("---")
        st.header("📅 月份筛选")
        show_months = st.multiselect(
            "参与对比的月份", options=months, default=months)
    if not show_months:
        show_months = months

    # 用 show_months 重新过滤 sp，让 KPI / TOP10 / 区域等全部联动
    sp = sp[sp["月份"].isin(show_months)].copy()
    n = len(show_months)
    show_months_sorted = sorted(show_months)
    mlabel = "、".join(str(m) for m in show_months_sorted) + "月"
    # 连续的前N月用"前N月"，否则直接列出月份
    is_prefix = show_months_sorted == list(range(1, n + 1))
    plabel = f"前{n}月" if is_prefix else mlabel

    banner = (f"📐 **同口径口径**：{selected_dataset} 当前筛选下最新年份 **{latest}**，"
              f"展示月份 **{mlabel}**。所有同比均按【各年相同月份】计算，绝不拿部分月份比往年全年。")
    if not prev_ok:
        banner += (f" ⚠️ 缺少 **{prev_year} 年的月度数据**，{latest} 年同比暂时无法计算。")
    st.info(banner)

    annual_sp = yoy_table(sp, [])
    partner_sp = yoy_table(sp, ["贸易伙伴名称", "所属区域"])
    province_sp = yoy_table(sp, ["注册地名称"])
    region_sp = yoy_table(sp, ["所属区域"])

    cur_total = float(annual_sp.loc[annual_sp["统计年份"] == latest, "金额_美元"].sum()) if not annual_sp.empty else 0.0
    cur_yoy = annual_sp.loc[annual_sp["统计年份"] == latest, "金额同比%"]
    cur_yoy = cur_yoy.iloc[0] if len(cur_yoy) and pd.notna(cur_yoy.iloc[0]) else None
    prev_total = float(annual_sp.loc[annual_sp["统计年份"] == prev_year, "金额_美元"].sum()) if prev_ok else None

    st.markdown(f"### 🌐 {latest} 年{plabel} 全球市场贸易格局透视")
    ca, cb, cc = st.columns(3)
    ca.metric(f"{latest} 年{plabel}出口总额", f"${cur_total:,.0f}",
              delta=(f"{cur_yoy:+.2f}%" if cur_yoy is not None else None))
    cb.metric(f"{prev_year} 年同期", f"${prev_total:,.0f}" if prev_total is not None else "无月度数据")
    cc.metric("活跃目的地数量", int(sp.loc[sp["统计年份"] == latest, "贸易伙伴名称"].nunique()))

    st.markdown("---")

    if analysis_mode == "月度动态演变":
        st.subheader("📈 月度出口趋势（同口径月份，多年份叠加对比）")
        md = month_df_sel[month_df_sel["月份"].isin(show_months)].copy()
        md = md.groupby(["统计年份", "月份"], as_index=False)["金额_美元"].sum()
        md["年份"] = md["统计年份"].astype(str)
        if not md.empty:
            if len(show_months) == 1:
                mb = md.sort_values("统计年份")
                fig = px.bar(mb, x="年份", y="金额_美元", text_auto=".2s",
                             title=f"{show_months[0]} 月出口额：各年对比 (USD)")
            else:
                fig = px.line(md.sort_values(["年份", "月份"]), x="月份", y="金额_美元",
                              color="年份", markers=True,
                              title=f"各年 {'、'.join(str(m) for m in show_months)}月 出口额对比 (USD)")
                fig.update_layout(xaxis_type="category", xaxis_tickangle=0)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.subheader(f"📊 历年{plabel}出口额（同口径）")
        if not annual_sp.empty:
            bar = annual_sp.copy()
            bar["年份"] = bar["统计年份"].astype(str)
            fig0 = px.bar(bar, x="年份", y="金额_美元", text_auto=".2s",
                          title=f"历年{plabel}出口额")
            st.plotly_chart(fig0, use_container_width=True)
            show = annual_sp[["统计年份", "金额_美元", "上年同期", "金额同比%"]].copy()
            show.columns = ["年份", f"{plabel}出口额", "上年同期", "同比%"]
            st.dataframe(show, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"🏆 {latest} 年{plabel} 前十大出口目的地")
        top = partner_sp[partner_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False).head(10)
        if not top.empty:
            fig1 = px.bar(top, x="贸易伙伴名称", y="金额_美元", color="所属区域", text_auto=".2s")
            fig1.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig1, use_container_width=True)
            tshow = top[["贸易伙伴名称", "所属区域", "金额_美元", "上年同期", "金额同比%"]]
            st.dataframe(tshow, use_container_width=True, hide_index=True)
    with col2:
        st.subheader(f"🏭 {latest} 年{plabel} 出口省份 TOP10")
        ptop = province_sp[province_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False).head(10)
        if not ptop.empty:
            fig2 = px.pie(ptop, names="注册地名称", values="金额_美元", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

    # 区域
    st.subheader(f"🗺️ {latest} 年{plabel} 区域分布")
    rnow = region_sp[region_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False)
    if (rnow["所属区域"] == "其他").all():
        st.warning("区域全部为「其他」：请把『区域映射表.xlsx』放到根目录后重跑 prepare，以启用区域映射。")
    if not rnow.empty:
        fig3 = px.bar(rnow, x="所属区域", y="金额_美元", color="所属区域", text_auto=".2s")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(rnow[["所属区域", "金额_美元", "上年同期", "金额同比%"]],
                     use_container_width=True, hide_index=True)

    # ===== 新增分析维度 =====
    if prev_ok:
        st.markdown("---")

        # ── 1. 增长贡献分解 ──────────────────────────────────────────
        st.subheader(f"📉 增长贡献分解：{prev_year}→{latest} 各区域拉动/拖累")
        r_cur  = region_sp[region_sp["统计年份"] == latest ][["所属区域","金额_美元"]].rename(columns={"金额_美元":"今年"})
        r_prev = region_sp[region_sp["统计年份"] == prev_year][["所属区域","金额_美元"]].rename(columns={"金额_美元":"去年"})
        contrib = r_cur.merge(r_prev, on="所属区域", how="outer").fillna(0)
        contrib["贡献额"] = contrib["今年"] - contrib["去年"]
        contrib["方向"]   = contrib["贡献额"].apply(lambda x: "拉动" if x >= 0 else "拖累")
        contrib["贡献率%"] = (contrib["贡献额"] / abs(contrib["贡献额"]).sum() * 100).round(1)
        contrib = contrib.sort_values("贡献额")
        fig_c = px.bar(contrib, x="贡献额", y="所属区域", orientation="h",
                       color="方向", color_discrete_map={"拉动":"#2ecc71","拖累":"#e74c3c"},
                       text=contrib["贡献额"].apply(lambda v: f"{'+'if v>=0 else ''}{v/1e6:.1f}M"),
                       title=f"{prev_year}→{latest} 各区域对总出口变化的贡献（USD）")
        fig_c.update_traces(textposition="outside")
        fig_c.update_layout(showlegend=True, xaxis_title="贡献额（USD）")
        st.plotly_chart(fig_c, use_container_width=True)
        cshow = contrib[["所属区域","去年","今年","贡献额","贡献率%"]].sort_values("贡献额", ascending=False)
        cshow.columns = ["区域","去年同期","今年","贡献额","贡献占比%"]
        st.dataframe(cshow, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── 2. 市场份额变化 ──────────────────────────────────────────
        st.subheader(f"🔄 市场份额迁移：{prev_year}→{latest} 各区域占比变化（百分点）")
        share_cur  = region_sp[region_sp["统计年份"] == latest ][["所属区域","金额份额%"]].rename(columns={"金额份额%":"今年份额%"})
        share_prev = region_sp[region_sp["统计年份"] == prev_year][["所属区域","金额份额%"]].rename(columns={"金额份额%":"去年份额%"})
        share = share_cur.merge(share_prev, on="所属区域", how="outer").fillna(0)
        share["份额变化ppt"] = (share["今年份额%"] - share["去年份额%"]).round(2)
        share["方向"] = share["份额变化ppt"].apply(lambda x: "提升" if x >= 0 else "下降")
        share = share.sort_values("份额变化ppt")
        fig_s = px.bar(share, x="份额变化ppt", y="所属区域", orientation="h",
                       color="方向", color_discrete_map={"提升":"#3498db","下降":"#e67e22"},
                       text=share["份额变化ppt"].apply(lambda v: f"{'+'if v>=0 else ''}{v:.1f}ppt"),
                       title=f"各区域出口份额变化（百分点）")
        fig_s.update_traces(textposition="outside")
        fig_s.update_layout(xaxis_title="份额变化（ppt）")
        st.plotly_chart(fig_s, use_container_width=True)

        st.markdown("---")

        # ── 3. 新兴市场 vs 萎缩市场（国家粒度） ────────────────────
        st.subheader(f"🌱 新兴市场 & 萎缩市场（{prev_year}→{latest}，国家粒度）")
        p_cur  = partner_sp[partner_sp["统计年份"] == latest ][["贸易伙伴名称","所属区域","金额_美元","金额同比%"]]
        p_prev = partner_sp[partner_sp["统计年份"] == prev_year][["贸易伙伴名称","金额_美元"]].rename(columns={"金额_美元":"去年金额"})
        p_join = p_cur.merge(p_prev, on="贸易伙伴名称", how="left")

        new_markets = p_cur[~p_cur["贸易伙伴名称"].isin(p_prev["贸易伙伴名称"])].sort_values("金额_美元", ascending=False).head(10)
        lost_markets_prev = partner_sp[partner_sp["统计年份"] == prev_year][["贸易伙伴名称","金额_美元"]]
        lost_markets = lost_markets_prev[~lost_markets_prev["贸易伙伴名称"].isin(
            partner_sp[partner_sp["统计年份"] == latest]["贸易伙伴名称"])].sort_values("金额_美元", ascending=False).head(10)

        with_both = p_join.dropna(subset=["金额同比%"]).copy()
        risers  = with_both.sort_values("金额同比%", ascending=False).head(10)
        fallers = with_both.sort_values("金额同比%", ascending=True ).head(10)

        c3a, c3b = st.columns(2)
        with c3a:
            st.markdown(f"**🚀 增速最快 TOP10（同比增长%）**")
            if not risers.empty:
                fig_r = px.bar(risers.sort_values("金额同比%"), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f")
                fig_r.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_r, use_container_width=True)
        with c3b:
            st.markdown(f"**📉 跌幅最大 TOP10（同比下滑%）**")
            if not fallers.empty:
                fig_f = px.bar(fallers.sort_values("金额同比%", ascending=False), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f",
                               color_discrete_sequence=px.colors.qualitative.Set2)
                fig_f.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_f, use_container_width=True)

        c3c, c3d = st.columns(2)
        with c3c:
            st.markdown(f"**🌱 新进入市场（{latest}年新增，{prev_year}年无记录）**")
            if not new_markets.empty:
                st.dataframe(new_markets[["贸易伙伴名称","所属区域","金额_美元"]].rename(
                    columns={"金额_美元":"出口额"}), use_container_width=True, hide_index=True)
            else:
                st.caption("无新进入市场")
        with c3d:
            st.markdown(f"**⚠️ 退出市场（{prev_year}年有，{latest}年无记录）**")
            if not lost_markets.empty:
                st.dataframe(lost_markets[["贸易伙伴名称","金额_美元"]].rename(
                    columns={"金额_美元":"去年出口额"}), use_container_width=True, hide_index=True)
            else:
                st.caption("无退出市场")

    st.markdown("---")

    # 历年全年：优先用月度数据里『满12个月』的年份汇总出真实全年总额，
    # 没有月度数据来源的年份再用年度（全年快照）文件补充；不满12个月的年份一律排除。
    if analysis_mode == "历年全年(完整年份)":
        st.markdown("---")
        st.subheader("🗓️ 历年全年出口额（仅完整年份）")

        month_counts = month_df_sel.groupby("统计年份")["月份"].nunique()
        full_years_from_month = sorted(int(y) for y in month_counts[month_counts >= 12].index)
        incomplete_years_from_month = sorted(int(y) for y in month_counts[month_counts < 12].index)

        year_df_sel = year_df[year_df["统计年份"].isin(selected_years)] if selected_years else year_df
        # 月度已覆盖的年份不重复使用年度快照（避免双计）
        year_only_years = sorted(set(int(y) for y in year_df_sel["统计年份"].unique())
                                  - set(month_df_sel["统计年份"].unique()))

        full_parts = []
        if full_years_from_month:
            full_parts.append(month_df_sel[month_df_sel["统计年份"].isin(full_years_from_month)])
        if year_only_years:
            full_parts.append(year_df_sel[year_df_sel["统计年份"].isin(year_only_years)])

        if not full_parts:
            st.caption("暂无满12个月的完整年度数据：当前筛选的年份均不足12个月。")
        else:
            yfull = yoy_table(pd.concat(full_parts, ignore_index=True), [])
            yb = yfull.copy(); yb["年份"] = yb["统计年份"].astype(str)
            st.plotly_chart(px.bar(yb, x="年份", y="金额_美元", text_auto=".2s",
                                   title="历年全年出口额"), use_container_width=True)
            ys = yfull[["统计年份", "金额_美元", "上年同期", "金额同比%"]].copy()
            ys.columns = ["年份", "全年出口额", "上年", "同比%"]
            st.dataframe(ys, use_container_width=True, hide_index=True)

        if incomplete_years_from_month:
            st.caption(f"注意：{incomplete_years_from_month} 年月度数据不满12个月，已从全年视图中排除，避免与全年数据混比。")

# ---------- 没有月度数据：只能快照（如水龙头只有单一年份）----------
else:
    st.warning(f"{selected_dataset} **没有月度数据（无有效月份）**，无法做前N月同比，"
               "以下仅作单期快照。若该数据集只有 1 个年份，则无法计算任何同比。")
    years = sorted(int(y) for y in year_df["统计年份"].dropna().unique())
    st.caption(f"可用年份：{years}")
    latest = years[-1] if years else None
    if latest is not None:
        snap = year_df[year_df["统计年份"] == latest]
        st.markdown(f"### 🌐 {latest} 年市场快照")
        ca, cb = st.columns(2)
        ca.metric(f"{latest} 年出口总额", f"${snap['金额_美元'].sum():,.0f}")
        cb.metric("活跃目的地数量", int(snap["贸易伙伴名称"].nunique()))
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏆 前十大出口目的地")
            t = snap.groupby(["贸易伙伴名称", "所属区域"], as_index=False)["金额_美元"].sum() \
                    .sort_values("金额_美元", ascending=False).head(10)
            st.plotly_chart(px.bar(t, x="贸易伙伴名称", y="金额_美元", color="所属区域",
                                   text_auto=".2s"), use_container_width=True)
        with c2:
            st.subheader("🏭 出口省份 TOP10")
            p = snap.groupby("注册地名称", as_index=False)["金额_美元"].sum() \
                    .sort_values("金额_美元", ascending=False).head(10)
            st.plotly_chart(px.pie(p, names="注册地名称", values="金额_美元", hole=0.4),
                            use_container_width=True)
        # 单价（若有重量）
        if (snap["数量_统一"] > 0).any():
            st.subheader("💰 高附加值市场 TOP10（按出口单价）")
            u = snap.groupby(["贸易伙伴名称", "所属区域"], as_index=False).agg(
                {"金额_美元": "sum", "数量_统一": "sum"})
            u["出口单价（美元/单位）"] = np.where(u["数量_统一"] > 0,
                                           (u["金额_美元"] / u["数量_统一"]).round(4), np.nan)
            u = u[u["金额_美元"] > 0].sort_values("出口单价（美元/单位）", ascending=False).head(10)
            st.dataframe(u, use_container_width=True, hide_index=True)

st.markdown("""
<div class="footer">
  <div>
    <span style="font-size:1rem;font-weight:600;color:#e8edf5;">📊 卫浴与泛家居进出口多维洞察大屏</span><br>
    <span style="font-size:.78rem;">同比口径说明：各年取相同月份汇总后逐年同比，缺月度数据的年份不参与同比，避免「部分年 vs 全年」的错误对比。</span>
  </div>
  <div style="text-align:right;line-height:1.8;">
    <span style="color:#e8edf5;font-weight:600;">作者：sze</span><br>
    <span>📱 交流：<a href="tel:13760765317">137-6076-5317</a></span><br>
    <span style="font-size:.75rem;color:#7a9cc4;">数据来源：中国海关出口统计 · 仅供研究参考</span>
  </div>
</div>
""", unsafe_allow_html=True)
