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

st.set_page_config(page_title="卫浴行业数据观察智库", layout="wide")
st.title("📊 卫浴与泛家居进出口多维洞察大屏")

# ================= 侧边栏 =================
with st.sidebar:
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
    latest, months, ok_years, sp = same_period_pool(month_df)
    n = len(months)
    mlabel = "、".join(str(m) for m in months) + "月"
    plabel = f"前{n}月"
    prev_year = latest - 1
    prev_ok = prev_year in ok_years

    with st.sidebar:
        st.markdown("---")
        st.header("📅 年份筛选")
        selected_years = st.multiselect(
            f"参与{plabel}同口径对比的年份", options=ok_years, default=ok_years)
    if not selected_years:
        selected_years = ok_years
    sp = sp[sp["统计年份"].isin(selected_years)].copy()

    banner = (f"📐 **同口径口径**：{selected_dataset} 最新年份 **{latest}** 含 **{n}** 个月（{mlabel}）。"
              f"所有同比均按【各年相同月份】计算，绝不拿部分月份比往年全年。")
    if not prev_ok:
        banner += (f" ⚠️ 缺少 **{prev_year} 年的月度数据**，{latest} 年{plabel}同比暂时无法计算——"
                   f"请把 {prev_year} 年 {mlabel} 的月度数据(含『数据年月』)放进 raw_data 后重跑 prepare。")
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
        md = month_df[month_df["月份"].isin(months) & month_df["统计年份"].isin(selected_years)].copy()
        md = md.groupby(["统计年份", "月份"], as_index=False)["金额_美元"].sum()
        md["年份"] = md["统计年份"].astype(str)
        if not md.empty:
            fig = px.line(md.sort_values(["年份", "月份"]), x="月份", y="金额_美元",
                          color="年份", markers=True,
                          title=f"各年 {mlabel} 出口额对比 (USD)")
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

    # 历年全年（仅完整年份，来自年度数据；排除不完整的最新年份）
    if analysis_mode == "历年全年(完整年份)":
        st.markdown("---")
        st.subheader("🗓️ 历年全年出口额（仅完整年份）")
        if year_df.empty:
            st.caption("暂无年度（全年）数据文件。")
        else:
            yfull_src = year_df[year_df["统计年份"] < latest]
            if selected_years:
                yfull_src = yfull_src[yfull_src["统计年份"].isin(selected_years)]
            yfull = yoy_table(yfull_src, [])
            if yfull.empty:
                st.caption("暂无早于当前年份的完整年度数据。")
            else:
                yb = yfull.copy(); yb["年份"] = yb["统计年份"].astype(str)
                st.plotly_chart(px.bar(yb, x="年份", y="金额_美元", text_auto=".2s",
                                       title="历年全年出口额"), use_container_width=True)
                ys = yfull[["统计年份", "金额_美元", "上年同期", "金额同比%"]].copy()
                ys.columns = ["年份", "全年出口额", "上年", "同比%"]
                st.dataframe(ys, use_container_width=True, hide_index=True)
        st.caption(f"注意：{latest} 年尚未完整，已从全年视图中排除，避免与{plabel}数据混比。")

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

st.caption("同比口径与已验证的 6910 月度脚本一致：各年取相同月份汇总后逐年同比；"
           "缺月度数据的年份不参与同比，避免『部分年 vs 全年』的错误暴跌。")
