import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# —— 图表统一走 Iris 深紫风：透明背景 + 青/薄荷/淡紫配色 ——
IRIS_SEQ = ["#00b1ff", "#00ffaa", "#b1a6f6", "#5350cc", "#7a86ff",
            "#3fd0ff", "#8fe9c8", "#403cd5", "#c9b8ff", "#00c2c2"]
_t = pio.templates["plotly_dark"]
_t.layout.paper_bgcolor = "rgba(0,0,0,0)"
_t.layout.plot_bgcolor = "rgba(0,0,0,0)"
_t.layout.font.color = "#c3c6e6"
_t.layout.font.family = "-apple-system, 'Segoe UI', Roboto, sans-serif"
_t.layout.xaxis.gridcolor = "rgba(177,166,246,.12)"
_t.layout.yaxis.gridcolor = "rgba(177,166,246,.12)"
_t.layout.colorway = IRIS_SEQ
pio.templates.default = "plotly_dark"
px.defaults.color_discrete_sequence = IRIS_SEQ
px.defaults.color_continuous_scale = "Purpor"

MAPPING_FILE_NAME = "区域映射表.xlsx"

# ================= 内置数据映射 =================
DATASETS = {
    "6910 (陶瓷卫浴)": "data/default_6910.parquet",
    "水龙头/龙头": "data/default_faucet.parquet",
}

st.set_page_config(page_title="卫浴行业数据观察智库", layout="wide", page_icon="📊")

# ================= 全局样式（Iris 深紫 · 参考 Impilo）=================
st.markdown("""
<style>
:root{
  --iris-bg:#16165c; --iris-surface:#232269; --iris-glow:#403cd5;
  --iris-pulse:#5350cc; --iris-border:#4846c6;
  --cyan:#00b1ff; --mint:#00ffaa; --lilac:#b1a6f6;
  --fog:#9494a9; --ink:#eef0fb; --ink-soft:#b7b9d8;
}

/* 主背景：深紫 iris，柔和径向提亮，无网格无发光 */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 700px at 15% -10%, rgba(80,76,205,.35), transparent 60%),
    radial-gradient(900px 600px at 100% 0%, rgba(0,177,255,.10), transparent 55%),
    #16165c;
  background-attachment:fixed;
}
.block-container{ position:relative; z-index:1; }

/* 侧边栏：略深的 iris 面，1px 细描边 */
[data-testid="stSidebar"]{
  background:#13134f;
  border-right:1px solid var(--iris-border);
}
[data-testid="stSidebar"] .stMarkdown hr{ border-color:rgba(72,70,198,.5); }
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
  color:var(--ink) !important; font-size:.95rem !important; letter-spacing:.2px; font-weight:600;
}

/* 顶部品牌栏：iris-surface 卡，24px 圆角，1px 细描边，无阴影 */
.top-banner{
  background:var(--iris-surface);
  border:1px solid var(--iris-border);
  border-radius:24px; padding:30px 36px 26px; margin-bottom:24px;
}
.top-banner h1{
  color:var(--ink); font-size:2rem; font-weight:600; margin:0;
  letter-spacing:-.02em;
}
.top-banner .subtitle{
  color:var(--lilac); font-size:.8rem; margin:10px 0 0; letter-spacing:.28em;
  text-transform:uppercase; font-weight:500;
}
.top-banner .tag{
  display:inline-block; margin-top:14px; padding:5px 14px; font-size:.72rem;
  color:var(--cyan); border:1px solid rgba(0,177,255,.4); border-radius:9999px;
  background:rgba(0,177,255,.08); letter-spacing:.04em;
}

/* 指标卡片：iris-surface 面 + 顶部 cyan 细条，扁平层次（无发光） */
[data-testid="stMetric"],[data-testid="metric-container"]{
  position:relative; overflow:hidden;
  background:var(--iris-surface);
  border:1px solid var(--iris-border);
  border-radius:20px; padding:18px 22px;
  transition:background .2s, transform .2s;
}
[data-testid="stMetric"]::before{
  content:""; position:absolute; left:0; top:0; right:0; height:3px;
  background:linear-gradient(90deg,var(--cyan),var(--mint));
}
[data-testid="stMetric"]:hover{ background:var(--iris-glow); transform:translateY(-2px); }
[data-testid="stMetric"] label,[data-testid="metric-container"] label{
  color:var(--ink-soft) !important; font-size:.8rem !important; letter-spacing:.02em;
}
[data-testid="stMetricValue"]{ color:var(--ink) !important; font-weight:600; letter-spacing:-.01em; }

/* 标题 */
h2,h3{ color:var(--ink); font-weight:600; letter-spacing:-.01em; }

/* 分割线 */
hr{ border-color:rgba(72,70,198,.45); }

/* 信息条：iris-surface + cyan 左条 */
[data-testid="stAlert"]{
  background:var(--iris-surface) !important;
  border:1px solid var(--iris-border) !important;
  border-left:3px solid var(--cyan) !important; border-radius:16px;
}

/* dataframe */
[data-testid="stDataFrame"]{
  border-radius:16px; overflow:hidden; border:1px solid var(--iris-border);
}

/* 胶囊标签（多选筛选项） */
[data-baseweb="tag"]{
  background:var(--iris-pulse) !important; border-radius:9999px !important; border:none !important;
}

/* 页脚：iris-surface 卡 + 顶部 cyan→mint 细条 */
.footer{
  position:relative; overflow:hidden;
  background:var(--iris-surface); border:1px solid var(--iris-border);
  border-radius:24px; padding:24px 32px; margin-top:48px;
  color:var(--ink-soft); font-size:.85rem;
  display:flex; justify-content:space-between; align-items:center; gap:20px;
}
.footer::before{
  content:""; position:absolute; left:0; right:0; top:0; height:3px;
  background:linear-gradient(90deg,var(--cyan),var(--mint),transparent);
}
.footer a{ color:var(--cyan); text-decoration:none; }

/* 品牌 LOGO 区 */
.brand{ text-align:center; padding:16px 0 8px; }
.brand .logo{
  display:inline-flex; align-items:center; justify-content:center;
  width:54px; height:54px; border-radius:18px; margin-bottom:10px;
  background:var(--iris-glow); border:1px solid var(--iris-border); font-size:1.6rem;
}
.brand .name{
  font-weight:600; font-size:1.05rem; color:var(--ink); letter-spacing:.14em;
}
.brand .name b{ color:var(--cyan); font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ================= 顶部标题栏 =================
st.markdown("""
<div class="top-banner">
  <h1>📊 卫浴与泛家居进出口多维洞察大屏</h1>
  <div class="subtitle">Sanitaryware &amp; Home Export Intelligence</div>
  <div class="tag">◆ 数据来源：海关出口月度统计</div>
</div>
""", unsafe_allow_html=True)

# ================= 侧边栏 =================
with st.sidebar:
    st.markdown("""
    <div class="brand">
      <div class="logo">📊</div>
      <div class="name">SANITARY<b>WARE</b></div>
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


def render_about():
    """作者/联系卡片——渲染在侧边栏最底部（在所有筛选控件之后）。"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("""
        <div style="padding:16px 16px;border:1px solid #4846c6;border-radius:20px;
                    background:#232269;">
          <div style="font-size:.72rem;color:#00b1ff;letter-spacing:.2em;margin-bottom:10px;">◆ ABOUT</div>
          <div style="color:#eef0fb;font-size:.9rem;font-weight:600;">👤 作者 · sze</div>
          <div style="color:#b7b9d8;font-size:.84rem;margin-top:6px;">
            📱 交流 · <a href="tel:13760765317" style="color:#00b1ff;text-decoration:none;">137-6076-5317</a>
          </div>
          <div style="color:#9494a9;font-size:.72rem;margin-top:12px;line-height:1.5;">
            数据仅供研究参考<br>不构成商业建议
          </div>
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

    banner = f"📐 口径：{selected_dataset} · 最新年份 **{latest}** · 对比月份 **{mlabel}**（各年取相同月份汇总同比）"
    if not prev_ok:
        banner += f" · ⚠️ 缺 {prev_year} 年月度数据，同比暂无法计算"
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

        # 剔除小基数区域：仅保留今年或去年份额≥1%的区域，且排除「其他」
        tot_cur_r  = region_sp.loc[region_sp["统计年份"] == latest,    "金额_美元"].sum()
        tot_prev_r = region_sp.loc[region_sp["统计年份"] == prev_year, "金额_美元"].sum()
        _rc = region_sp[region_sp["统计年份"] == latest ].set_index("所属区域")["金额_美元"]
        _rp = region_sp[region_sp["统计年份"] == prev_year].set_index("所属区域")["金额_美元"]
        _regs = set(_rc.index) | set(_rp.index)
        keep_regions = {r for r in _regs if r != "其他" and
                        (_rc.get(r, 0) / tot_cur_r if tot_cur_r else 0) >= 0.01
                        or (_rp.get(r, 0) / tot_prev_r if tot_prev_r else 0) >= 0.01}

        # ── 1. 增长贡献分解 ──────────────────────────────────────────
        st.subheader(f"📉 增长贡献分解：{prev_year}→{latest} 各区域拉动/拖累")
        st.caption("已剔除份额不足 1% 的小基数区域及「其他」")
        r_cur  = region_sp[region_sp["统计年份"] == latest ][["所属区域","金额_美元"]].rename(columns={"金额_美元":"今年"})
        r_prev = region_sp[region_sp["统计年份"] == prev_year][["所属区域","金额_美元"]].rename(columns={"金额_美元":"去年"})
        contrib = r_cur.merge(r_prev, on="所属区域", how="outer").fillna(0)
        contrib = contrib[contrib["所属区域"].isin(keep_regions)]
        contrib["贡献额"] = contrib["今年"] - contrib["去年"]
        contrib["方向"]   = contrib["贡献额"].apply(lambda x: "拉动" if x >= 0 else "拖累")
        contrib["贡献率%"] = (contrib["贡献额"] / abs(contrib["贡献额"]).sum() * 100).round(1)
        contrib = contrib.sort_values("贡献额")
        fig_c = px.bar(contrib, x="贡献额", y="所属区域", orientation="h",
                       color="方向", color_discrete_map={"拉动":"#00ffaa","拖累":"#ff6b8a"},
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
        share = share[share["所属区域"].isin(keep_regions)]
        share["份额变化ppt"] = (share["今年份额%"] - share["去年份额%"]).round(2)
        share["方向"] = share["份额变化ppt"].apply(lambda x: "提升" if x >= 0 else "下降")
        share = share.sort_values("份额变化ppt")
        fig_s = px.bar(share, x="份额变化ppt", y="所属区域", orientation="h",
                       color="方向", color_discrete_map={"提升":"#00b1ff","下降":"#ff9e6b"},
                       text=share["份额变化ppt"].apply(lambda v: f"{'+'if v>=0 else ''}{v:.1f}ppt"),
                       title=f"各区域出口份额变化（百分点）")
        fig_s.update_traces(textposition="outside")
        fig_s.update_layout(xaxis_title="份额变化（ppt）")
        st.plotly_chart(fig_s, use_container_width=True)

        st.markdown("---")

        # ── 3. 新兴市场 vs 萎缩市场（国家粒度，仅统计有真实体量的市场） ────
        # 基数门槛：今年、去年出口额均需达到当期总额的约0.3%（下限100万美元），
        # 只保留有真实体量的市场，剔除小基数市场。
        base_floor = max(1e6, 0.003 * cur_total)
        st.subheader(f"🌱 高增长 & 深回调市场（{prev_year}→{latest}，国家粒度）")
        st.caption(f"仅统计两年出口额均 ≥ ${base_floor/1e6:.1f}M 的市场（剔除小基数市场）")

        p_cur  = partner_sp[partner_sp["统计年份"] == latest ][["贸易伙伴名称","所属区域","金额_美元","金额同比%"]].rename(columns={"金额_美元":"今年"})
        p_prev = partner_sp[partner_sp["统计年份"] == prev_year][["贸易伙伴名称","金额_美元"]].rename(columns={"金额_美元":"去年"})
        p_join = p_cur.merge(p_prev, on="贸易伙伴名称", how="left").fillna({"去年": 0})
        cand = p_join[(p_join["今年"] >= base_floor) & (p_join["去年"] >= base_floor)].dropna(subset=["金额同比%"]).copy()

        risers  = cand.sort_values("金额同比%", ascending=False).head(10)
        fallers = cand.sort_values("金额同比%", ascending=True ).head(10)

        c3a, c3b = st.columns(2)
        with c3a:
            st.markdown("**🚀 增速领先 TOP10（同比%）**")
            if not risers.empty:
                fig_r = px.bar(risers.sort_values("金额同比%"), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f",
                               hover_data={"今年":":,.0f","去年":":,.0f"})
                fig_r.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_r, use_container_width=True)
                st.dataframe(risers[["贸易伙伴名称","所属区域","今年","去年","金额同比%"]].rename(
                    columns={"今年":"今年出口额","去年":"去年出口额","金额同比%":"同比%"}),
                    use_container_width=True, hide_index=True)
        with c3b:
            st.markdown("**📉 跌幅最深 TOP10（同比%）**")
            if not fallers.empty:
                fig_f = px.bar(fallers.sort_values("金额同比%", ascending=False), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f",
                               hover_data={"今年":":,.0f","去年":":,.0f"})
                fig_f.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_f, use_container_width=True)
                st.dataframe(fallers[["贸易伙伴名称","所属区域","今年","去年","金额同比%"]].rename(
                    columns={"今年":"今年出口额","去年":"去年出口额","金额同比%":"同比%"}),
                    use_container_width=True, hide_index=True)

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
            st.caption(f"注：{incomplete_years_from_month} 年数据不满12个月，未纳入全年视图。")

# ---------- 没有月度数据：只能快照（如水龙头只有单一年份）----------
else:
    st.info(f"{selected_dataset} 无月度数据，以下为最新年度快照。")
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

# 作者卡片渲染在侧边栏最底部（此时所有筛选控件已加入侧边栏）
render_about()

st.markdown("""
<div class="footer">
  <div>
    <span style="font-size:1rem;font-weight:600;color:#eef0fb;">📊 卫浴与泛家居进出口多维洞察大屏</span><br>
    <span style="font-size:.78rem;">同比口径：各年取相同月份汇总后逐年同比。</span>
  </div>
  <div style="text-align:right;line-height:1.8;">
    <span style="color:#00b1ff;font-weight:600;">作者 · sze</span><br>
    <span>📱 交流 · <a href="tel:13760765317">137-6076-5317</a></span><br>
    <span style="font-size:.75rem;color:#9494a9;">数据来源：海关出口统计 · 仅供研究参考</span>
  </div>
</div>
""", unsafe_allow_html=True)
