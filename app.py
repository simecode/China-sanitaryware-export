import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import os
import base64
import warnings
warnings.filterwarnings('ignore')

# —— 品牌 Logo：优先用裁好透明底的 logo_mark.png ——
def _load_logo_b64():
    for p in ("assets/logo_mark.png", "assets/logo.png"):
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("ascii")
            except Exception:
                pass
    return None

LOGO_B64 = _load_logo_b64()
# favicon / 分享缩略图：优先用方形白底图标（透明/竖版在微信里会变灰、显得过大）
LOGO_PATH = next((p for p in ("assets/logo_icon.png", "assets/logo_mark.png", "assets/logo.png")
                  if os.path.exists(p)), None)

# —— 图表统一走 Ventriloc 编辑风：白底 + 墨黑/暖灰 + 橙/黄铜点睛 ——
# 近乎单色（graphite/steel/slate 灰阶）+ Ember 橙 + Brass 黄铜为暖色点缀
EDIT_SEQ = ["#ff682c", "#816729", "#202020", "#4d4d4d", "#828282",
            "#b5651d", "#c9a227", "#a6a6a6", "#5c4a1f", "#d98a5c"]
_t = pio.templates["plotly_white"]
_t.layout.paper_bgcolor = "rgba(0,0,0,0)"
_t.layout.plot_bgcolor = "rgba(0,0,0,0)"
_t.layout.font.color = "#202020"
_t.layout.font.family = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
_t.layout.xaxis.gridcolor = "#e8e8e8"
_t.layout.yaxis.gridcolor = "#e8e8e8"
_t.layout.xaxis.linecolor = "#e8e8e8"
_t.layout.yaxis.linecolor = "#e8e8e8"
_t.layout.colorway = EDIT_SEQ
pio.templates.default = "plotly_white"
px.defaults.color_discrete_sequence = EDIT_SEQ
px.defaults.color_continuous_scale = "Oranges"

MAPPING_FILE_NAME = "区域映射表.xlsx"

# —— 主要贸易伙伴经纬度（用于出口流向地图；覆盖约九成出口额）——
CN_ORIGIN = (34.0, 108.9)  # 中国大致中心，作为流向起点
COUNTRY_COORDS = {
    "美国": (39.8, -98.6), "越南": (16.0, 107.8), "泰国": (15.0, 101.0), "新加坡": (1.35, 103.8),
    "韩国": (36.5, 127.8), "马来西亚": (4.2, 101.9), "英国": (54.0, -2.0), "澳大利亚": (-25.3, 133.8),
    "加拿大": (56.1, -106.3), "俄罗斯": (61.5, 105.3), "菲律宾": (12.9, 121.8), "西班牙": (40.0, -3.7),
    "巴西": (-14.2, -51.9), "墨西哥": (23.6, -102.5), "沙特阿拉伯": (23.9, 45.1), "印度尼西亚": (-2.5, 118.0),
    "法国": (46.6, 2.2), "波兰": (51.9, 19.1), "印度": (22.0, 79.0), "阿联酋": (24.0, 54.0),
    "德国": (51.2, 10.4), "意大利": (42.8, 12.8), "荷兰": (52.1, 5.3), "中国台湾": (23.7, 121.0),
    "秘鲁": (-9.2, -75.0), "哈萨克斯坦": (48.0, 66.9), "智利": (-35.7, -71.5), "哥伦比亚": (4.6, -74.3),
    "希腊": (39.1, 21.8), "吉尔吉斯斯坦": (41.2, 74.8), "吉布提": (11.8, 42.6), "柬埔寨": (12.6, 104.9),
    "以色列": (31.0, 34.8), "摩洛哥": (31.8, -7.1), "斯里兰卡": (7.9, 80.8), "阿根廷": (-38.4, -63.6),
    "肯尼亚": (-0.02, 37.9), "中国香港": (22.3, 114.2), "新西兰": (-41.8, 172.0), "加纳": (7.9, -1.0),
    "南非": (-30.6, 22.9), "多米尼加": (18.7, -70.2), "罗马尼亚": (45.9, 24.9), "孟加拉国": (23.7, 90.4),
    "坦桑尼亚": (-6.4, 34.9), "日本": (36.2, 138.3), "土耳其": (39.0, 35.2), "埃及": (26.8, 30.8),
    "尼日利亚": (9.1, 8.7), "科威特": (29.3, 47.5), "卡塔尔": (25.3, 51.2), "伊拉克": (33.2, 43.7),
}


def render_flow_map(dfp, latest_year):
    """出口流向世界地图：从中国到各主要目的地的弧线，线宽/点大小随出口额。"""
    flow = (dfp[dfp["统计年份"] == latest_year]
            .groupby("贸易伙伴名称")["金额_美元"].sum())
    flow = flow[flow.index.isin(COUNTRY_COORDS) & (flow > 0)]
    if flow.empty:
        return
    maxv = float(flow.max())
    fig = go.Figure()
    for name, val in flow.items():
        lat, lon = COUNTRY_COORDS[name]
        r = val / maxv
        fig.add_trace(go.Scattergeo(
            lat=[CN_ORIGIN[0], lat], lon=[CN_ORIGIN[1], lon], mode="lines",
            line=dict(width=0.6 + 4.5 * r, color="#ff682c"),
            opacity=0.25 + 0.45 * r, hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scattergeo(
        lat=[COUNTRY_COORDS[n][0] for n in flow.index],
        lon=[COUNTRY_COORDS[n][1] for n in flow.index],
        text=[f"{n}：{v/1e8:.2f}亿美元" for n, v in flow.items()],
        marker=dict(size=[5 + 16 * (v / maxv) for v in flow.values],
                    color="#ff682c", opacity=0.75, line=dict(width=0)),
        mode="markers", hoverinfo="text", showlegend=False))
    fig.add_trace(go.Scattergeo(
        lat=[CN_ORIGIN[0]], lon=[CN_ORIGIN[1]], mode="markers",
        marker=dict(size=11, color="#202020"), text=["中国"], hoverinfo="text", showlegend=False))
    fig.update_geos(showcountries=True, countrycolor="#e2ded6",
                    showland=True, landcolor="#efeae1", showocean=True, oceancolor="#ffffff",
                    showcoastlines=False, projection_type="natural earth",
                    bgcolor="rgba(0,0,0,0)", showframe=False)
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=440,
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width='stretch')


def _hex_rgba(h, a):
    h = h.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def render_sankey(dfp, latest_year, top_prov=8, top_ctry=12):
    """三级流向桑基：产地省份 → 目的地区域 → 目的地国家，宽度随出口额（亿美元）。"""
    d = dfp[dfp["统计年份"] == latest_year][["注册地名称", "所属区域", "贸易伙伴名称", "金额_美元"]].copy()
    d = d[d["金额_美元"] > 0]
    if d.empty:
        return
    topp = set(d.groupby("注册地名称")["金额_美元"].sum().nlargest(top_prov).index)
    d["省"] = d["注册地名称"].where(d["注册地名称"].isin(topp), "其他省份")
    topc = set(d.groupby("贸易伙伴名称")["金额_美元"].sum().nlargest(top_ctry).index)
    d["国"] = d["贸易伙伴名称"].where(d["贸易伙伴名称"].isin(topc), "其他国家")
    d["区"] = d["所属区域"].replace("", "其他").fillna("其他")

    def _order(sr, tail):
        vals = sr.sort_values(ascending=False).index.tolist()
        return [v for v in vals if v != tail] + ([tail] if tail in vals else [])

    provs = _order(d.groupby("省")["金额_美元"].sum(), "其他省份")
    regs = d.groupby("区")["金额_美元"].sum().sort_values(ascending=False).index.tolist()
    ctrys = _order(d.groupby("国")["金额_美元"].sum(), "其他国家")
    nodes = provs + regs + ctrys
    idx = {n: i for i, n in enumerate(nodes)}

    reg_colors = {r: EDIT_SEQ[i % len(EDIT_SEQ)] for i, r in enumerate(regs)}
    node_colors = (["#3b3b3b"] * len(provs)
                   + [reg_colors[r] for r in regs]
                   + ["#b9b2a6"] * len(ctrys))

    pr = d.groupby(["省", "区"], as_index=False)["金额_美元"].sum()
    rc = d.groupby(["区", "国"], as_index=False)["金额_美元"].sum()
    s, t, val, lc = [], [], [], []
    for _, row in pr.iterrows():
        s.append(idx[row["省"]]); t.append(idx[row["区"]]); val.append(row["金额_美元"] / 1e8)
        lc.append(_hex_rgba(reg_colors[row["区"]], 0.30))
    for _, row in rc.iterrows():
        s.append(idx[row["区"]]); t.append(idx[row["国"]]); val.append(row["金额_美元"] / 1e8)
        lc.append(_hex_rgba(reg_colors[row["区"]], 0.30))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=nodes, color=node_colors, pad=14, thickness=14, line=dict(width=0),
                  hovertemplate="%{label}：%{value:.2f}亿美元<extra></extra>"),
        link=dict(source=s, target=t, value=val, color=lc,
                  hovertemplate="%{source.label} → %{target.label}：%{value:.2f}亿美元<extra></extra>")))
    fig.update_layout(margin=dict(t=6, l=6, r=6, b=6), height=560,
                      font=dict(color="#202020", family="Inter, system-ui, sans-serif"),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width='stretch')

# ================= 内置数据映射 =================
DATASETS = {
    "卫生陶瓷": "data/default_6910.parquet",
    "龙头": "data/default_faucet.parquet",
}

st.set_page_config(page_title="贸易可视化地图", layout="wide",
                   page_icon=(LOGO_PATH or "📊"))

# ================= 全局样式（Ventriloc 编辑风 · 暖白纸底 + 橙色点睛）=================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
:root{
  --graphite:#202020; --canvas:#ffffff; --ash:#efefef; --fog:#f5f5f5;
  --ivory:#ebe6dd; --steel:#4d4d4d; --slate:#828282; --mist:#e8e8e8;
  --ember:#ff682c; --brass:#816729;
  --font:'Inter', "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", system-ui, -apple-system, sans-serif;
}

html, body, [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] * { font-family:var(--font); }
/* 例外：Material 图标必须用图标字体，否则会显示成文字（如 keyboard_double_arrow_left） */
[data-testid="stIconMaterial"], span[class*="material-symbols"], span[class*="material-icons"],
.material-symbols-rounded, .material-symbols-outlined, .material-icons {
  font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
}

/* 主背景：纯白画布，充足留白 */
[data-testid="stAppViewContainer"]{ background:var(--canvas); }
.block-container{ padding-top:3rem; max-width:1240px; }
[data-testid="stMain"] [data-testid="stVerticalBlock"]{ gap:1.1rem; }

/* 侧边栏：Ash 暖灰面 */
[data-testid="stSidebar"]{ background:var(--ash); border-right:1px solid var(--mist); }
[data-testid="stSidebar"] .stMarkdown hr{ border-color:var(--mist); }
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
  color:var(--slate) !important; font-size:.72rem !important; font-weight:600;
  letter-spacing:.14em; text-transform:uppercase;
}

/* 顶部页头：极简大字，充足留白，细体墨黑 */
.top-banner{ padding:8px 0 30px; margin-bottom:10px; }
.top-banner h1{
  color:var(--graphite); font-size:3rem; font-weight:300; margin:0;
  line-height:1.06; letter-spacing:-.03em;
}
.top-banner .subtitle{
  color:var(--slate); font-size:.72rem; margin:16px 0 0; letter-spacing:.34em;
  text-transform:uppercase; font-weight:500;
}

/* 分区小标题：干净细体，无符号无竖条，充足上间距 */
[data-testid="stMain"] h2, [data-testid="stMain"] h3{
  color:var(--graphite); font-weight:400; letter-spacing:-.02em; margin-top:1.4em;
}
[data-testid="stMain"] h3{ font-size:1.45rem; }

/* 指标卡片：干净白面 + Mist 细边，去彩色边，8px 圆角，无阴影 */
[data-testid="stMetric"],[data-testid="metric-container"]{
  background:var(--canvas); border:1px solid var(--mist);
  border-radius:8px; padding:22px 24px;
  min-height:132px; box-sizing:border-box;
  display:flex; flex-direction:column; justify-content:center;
}
[data-testid="stMetric"] label,[data-testid="metric-container"] label{
  color:var(--slate) !important; font-size:.78rem !important; letter-spacing:.01em;
}
[data-testid="stMetricValue"]{
  color:var(--graphite) !important; font-weight:300; letter-spacing:-.02em; font-size:2rem;
}

hr{ border-color:var(--mist); }

/* 表格 */
[data-testid="stDataFrame"]{
  border-radius:8px; overflow:hidden; border:1px solid var(--mist); max-width:100%; overflow-x:auto;
}
[data-testid="stMain"] .stCaption, [data-testid="stCaptionContainer"]{ color:var(--slate); }

/* 多选筛选标签：Ash 胶囊、墨字 */
[data-baseweb="tag"]{
  background:var(--canvas) !important; color:var(--graphite) !important;
  border-radius:20px !important; border:1px solid var(--mist) !important;
}
[data-baseweb="tag"] span{ color:var(--graphite) !important; }

/* 页脚：极简，无边框无背景，仅右侧作者信息，位置靠下 */
.footer{
  margin-top:140px; padding:0 2px 8px;
  display:flex; justify-content:flex-end; color:var(--slate); font-size:.78rem;
}
.footer .col{ text-align:right; line-height:1.9; }
.footer a{ color:var(--slate); text-decoration:none; }
.footer a:hover{ color:var(--ember); }

/* 品牌 LOGO（侧边栏，居中） */
.brand{ padding:16px 2px 12px; text-align:center; }
.brand img.logo{ display:block; height:40px; width:auto; margin:0 auto; }
.brand .name{ font-weight:500; font-size:1.4rem; color:var(--graphite); letter-spacing:.04em; }

/* ===== 移动端适配 ===== */
@media (max-width: 640px){
  .block-container{ padding-left:.8rem !important; padding-right:.8rem !important; padding-top:2.4rem !important; }
  .top-banner h1{ font-size:1.9rem; }
  .top-banner .subtitle{ font-size:.62rem; letter-spacing:.2em; }
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; gap:.6rem !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{ min-width:100% !important; flex:1 1 100% !important; }
  [data-testid="stMetricValue"]{ font-size:1.5rem !important; }
  .footer{ flex-direction:column; align-items:flex-start; gap:14px; padding:20px 18px; }
  .footer > div:last-child{ text-align:left !important; }
}
</style>
""", unsafe_allow_html=True)

# ================= 顶部页头 =================
st.markdown("""
<div class="top-banner">
  <h1>贸易可视化地图</h1>
  <div class="subtitle">Trade Visualization · 卫浴与泛家居出口 · 中国海关数据</div>
</div>
""", unsafe_allow_html=True)

# ================= 侧边栏 =================
with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f'<div class="brand"><img class="logo" src="data:image/png;base64,{LOGO_B64}" alt="logo"/></div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<div class="brand"><div class="name">S</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.header("引擎配置")
    analysis_mode = st.radio("选择分析维度",
                             ["同口径(前N月)对比", "月度动态演变", "年度动态演变"])

    st.markdown("---")
    st.header("AI 接入")
    openrouter_key = st.text_input("OpenRouter API Key", type="password")
    ai_model = st.selectbox("推理模型", ["openai/gpt-oss-120b:free", "deepseek/deepseek-chat:free"])

    st.markdown("---")
    st.header("数据来源")
    use_builtin = True
    selected_dataset = st.selectbox("选择数据集", options=list(DATASETS.keys()), index=0)


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


# ================= 金额格式化（亿/万美元） =================
def fmt_money(v):
    """金额 → 中文单位字符串：≥1亿用『亿』，≥1万用『万』，否则原值。"""
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if abs(v) >= 1e8:
        return f"{v/1e8:,.2f}亿美元"
    if abs(v) >= 1e4:
        return f"{v/1e4:,.1f}万美元"
    return f"${v:,.0f}"


def disp_money(df, cols):
    """返回展示用副本：把金额列换算成『亿美元』(2位小数)并重命名列头。"""
    d = df.copy()
    ren = {}
    for c in cols:
        if c in d.columns:
            d[c] = (pd.to_numeric(d[c], errors="coerce") / 1e8).round(3)
            ren[c] = f"{c}（亿美元）"
    return d.rename(columns=ren)


def add_yi(df, src="金额_美元", dst="金额_亿"):
    """在副本上新增『亿美元』列，供图表按亿为单位绘制。"""
    d = df.copy()
    d[dst] = pd.to_numeric(d[src], errors="coerce") / 1e8
    return d


def render_period_analysis(sp, partner_sp, province_sp, region_sp, latest, prev_year, prev_ok, plabel, cur_total):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"{latest}年{plabel}前十大出口目的地")
        top = partner_sp[partner_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False).head(10)
        if not top.empty:
            topb = add_yi(top)
            fig1 = px.bar(topb, x="贸易伙伴名称", y="金额_亿", color="所属区域", text_auto=".2f")
            fig1.update_layout(xaxis_tickangle=-30); fig1.update_yaxes(title_text="金额（亿美元）")
            st.plotly_chart(fig1, width='stretch')
    with col2:
        st.subheader(f"{latest}年{plabel}出口省份TOP10")
        ptop = province_sp[province_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False).head(10)
        if not ptop.empty:
            ptb = add_yi(ptop).sort_values("金额_亿")
            fig2 = px.bar(ptb, x="金额_亿", y="注册地名称", orientation="h", text_auto=".2f")
            fig2.update_traces(marker_color="#816729",
                               hovertemplate="%{y}<br>%{x:.2f}亿美元<extra></extra>")
            fig2.update_layout(xaxis_title="金额（亿美元）", yaxis_title="")
            st.plotly_chart(fig2, width='stretch')

    # 前十大目的地明细（全宽，与上下表格一致）
    if not top.empty:
        tshow = disp_money(top[["贸易伙伴名称", "所属区域", "金额_美元", "上年同期", "金额同比%"]],
                           ["金额_美元", "上年同期"])
        st.dataframe(tshow, width='stretch', hide_index=True)

    # 区域
    st.subheader(f"{latest}年{plabel}区域分布")
    rnow = region_sp[region_sp["统计年份"] == latest].sort_values("金额_美元", ascending=False)
    if (rnow["所属区域"] == "其他").all():
        st.warning("区域全部为「其他」：请把『区域映射表.xlsx』放到根目录后重跑 prepare，以启用区域映射。")
    if not rnow.empty:
        rnb = add_yi(rnow)
        fig3 = px.bar(rnb, x="所属区域", y="金额_亿", text_auto=".2f")
        fig3.update_traces(marker_color="#4d4d4d")
        fig3.update_yaxes(title_text="金额（亿美元）")
        st.plotly_chart(fig3, width='stretch')
        st.dataframe(disp_money(rnow[["所属区域", "金额_美元", "上年同期", "金额同比%"]],
                                ["金额_美元", "上年同期"]),
                     width='stretch', hide_index=True)

    # 出口结构（区域 › 国家）
    st.subheader(f"{latest}年{plabel}出口结构")
    tm = sp[sp["统计年份"] == latest].groupby(["所属区域", "贸易伙伴名称"], as_index=False)["金额_美元"].sum()
    tm = tm[tm["金额_美元"] > 0]
    if not tm.empty:
        tm["金额_亿"] = (tm["金额_美元"] / 1e8).round(2)
        fig_tm = px.treemap(tm, path=[px.Constant("全部"), "所属区域", "贸易伙伴名称"],
                            values="金额_美元", color="金额_美元",
                            color_continuous_scale=["#f4efe8", "#e6d3bd", "#cf9b6a", "#ff682c"],
                            custom_data=["金额_亿"])
        fig_tm.update_traces(
            texttemplate="%{label}  %{percentParent}",
            hovertemplate="%{label}<br>%{customdata[0]:.2f}亿美元<extra></extra>",
            tiling=dict(pad=2), root_color="#ffffff",
            marker_line_color="#ffffff", marker_line_width=2, textfont=dict(color="#202020"))
        fig_tm.update_layout(margin=dict(t=6, l=0, r=0, b=0), height=460,
                             coloraxis_showscale=False)
        st.plotly_chart(fig_tm, width='stretch')

    # 出口流向路径（产地省份 → 目的地区域 → 目的地国家）
    st.subheader(f"{latest}年{plabel}出口流向路径")
    st.caption("产地省份 → 目的地区域 → 目的地国家；带状宽度随出口额（单位：亿美元）")
    render_sankey(sp, latest)

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
        st.subheader("增长贡献分解")
        st.caption("已剔除份额不足 1% 的小基数区域及「其他」；单位：亿美元")
        r_cur  = region_sp[region_sp["统计年份"] == latest ][["所属区域","金额_美元"]].rename(columns={"金额_美元":"今年"})
        r_prev = region_sp[region_sp["统计年份"] == prev_year][["所属区域","金额_美元"]].rename(columns={"金额_美元":"去年"})
        contrib = r_cur.merge(r_prev, on="所属区域", how="outer").fillna(0)
        contrib = contrib[contrib["所属区域"].isin(keep_regions)]
        contrib["贡献额"] = contrib["今年"] - contrib["去年"]
        contrib["方向"]   = contrib["贡献额"].apply(lambda x: "拉动" if x >= 0 else "拖累")
        contrib["贡献率%"] = (contrib["贡献额"] / abs(contrib["贡献额"]).sum() * 100).round(1)
        contrib = contrib.sort_values("贡献额")
        contrib["贡献_亿"] = contrib["贡献额"] / 1e8
        fig_c = px.bar(contrib, x="贡献_亿", y="所属区域", orientation="h",
                       color="方向", color_discrete_map={"拉动":"#816729","拖累":"#ff682c"},
                       text=contrib["贡献额"].apply(lambda v: f"{'+'if v>=0 else ''}{v/1e8:.2f}亿"))
        fig_c.update_traces(textposition="outside")
        fig_c.update_layout(showlegend=True, xaxis_title="贡献额（亿美元）")
        st.plotly_chart(fig_c, width='stretch')
        cshow = disp_money(
            contrib[["所属区域","去年","今年","贡献额","贡献率%"]].sort_values("贡献额", ascending=False),
            ["去年","今年","贡献额"])
        cshow.columns = ["区域","去年同期（亿美元）","今年（亿美元）","贡献额（亿美元）","贡献占比%"]
        st.dataframe(cshow, width='stretch', hide_index=True)

        st.markdown("---")

        # ── 2. 份额结构演变（各区域占比逐年，100% 堆叠柱）──────────────
        st.subheader("出口份额结构演变")
        st.caption(f"每根柱为当年 100%，堆叠展示各区域份额；取 {latest}年前六大区域，其余归「其他」。")
        rev = region_sp[["统计年份", "所属区域", "金额份额%"]].copy()
        topregs = region_sp[region_sp["统计年份"] == latest].nlargest(6, "金额_美元")["所属区域"].tolist()
        rev["区域"] = rev["所属区域"].where(rev["所属区域"].isin(topregs), "其他")
        revg = rev.groupby(["统计年份", "区域"], as_index=False)["金额份额%"].sum()
        revg["年份"] = revg["统计年份"].astype(str)
        order = topregs + ["其他"]
        cmap = {r: EDIT_SEQ[i % len(EDIT_SEQ)] for i, r in enumerate(topregs)}
        cmap["其他"] = "#cfcabf"
        fig_s = px.bar(revg, x="年份", y="金额份额%", color="区域",
                       category_orders={"区域": order}, color_discrete_map=cmap)
        fig_s.update_layout(barmode="stack", yaxis_title="份额（%）", xaxis_title="",
                            legend_title_text="", bargap=0.25)
        fig_s.update_yaxes(range=[0, 100], ticksuffix="%")
        fig_s.update_traces(hovertemplate="%{x}｜%{fullData.name}：%{y:.1f}%<extra></extra>")
        st.plotly_chart(fig_s, width='stretch')

        st.markdown("---")

        # ── 3. 新兴市场 vs 萎缩市场（国家粒度，仅统计有真实体量的市场） ────
        # 基数门槛：今年、去年出口额均需达到当期总额的约0.3%（下限100万美元），
        # 只保留有真实体量的市场，剔除小基数市场。
        base_floor = max(1e6, 0.003 * cur_total)
        st.subheader("高增长 & 深回调市场")
        st.caption(f"仅统计两年出口额均 ≥ ${base_floor/1e6:.1f}M 的市场（剔除小基数市场）")

        p_cur  = partner_sp[partner_sp["统计年份"] == latest ][["贸易伙伴名称","所属区域","金额_美元","金额同比%"]].rename(columns={"金额_美元":"今年"})
        p_prev = partner_sp[partner_sp["统计年份"] == prev_year][["贸易伙伴名称","金额_美元"]].rename(columns={"金额_美元":"去年"})
        p_join = p_cur.merge(p_prev, on="贸易伙伴名称", how="left").fillna({"去年": 0})
        cand = p_join[(p_join["今年"] >= base_floor) & (p_join["去年"] >= base_floor)].dropna(subset=["金额同比%"]).copy()

        risers  = cand.sort_values("金额同比%", ascending=False).head(10)
        fallers = cand.sort_values("金额同比%", ascending=True ).head(10)

        c3a, c3b = st.columns(2)
        with c3a:
            st.markdown("**增速领先 TOP10**")
            if not risers.empty:
                fig_r = px.bar(risers.sort_values("金额同比%"), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f",
                               hover_data={"今年":":,.0f","去年":":,.0f"})
                fig_r.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_r, width='stretch')
                rt = disp_money(risers[["贸易伙伴名称","所属区域","今年","去年","金额同比%"]], ["今年","去年"])
                rt.columns = ["贸易伙伴名称","所属区域","今年出口额（亿美元）","去年出口额（亿美元）","同比%"]
                st.dataframe(rt, width='stretch', hide_index=True)
        with c3b:
            st.markdown("**跌幅最深 TOP10**")
            if not fallers.empty:
                fig_f = px.bar(fallers.sort_values("金额同比%", ascending=False), x="金额同比%", y="贸易伙伴名称",
                               orientation="h", color="所属区域", text_auto=".1f",
                               hover_data={"今年":":,.0f","去年":":,.0f"})
                fig_f.update_layout(xaxis_title="同比增长%", yaxis_title="")
                st.plotly_chart(fig_f, width='stretch')
                ft = disp_money(fallers[["贸易伙伴名称","所属区域","今年","去年","金额同比%"]], ["今年","去年"])
                ft.columns = ["贸易伙伴名称","所属区域","今年出口额（亿美元）","去年出口额（亿美元）","同比%"]
                st.dataframe(ft, width='stretch', hide_index=True)


# ================= 主体 =================
if not month_df.empty:
    all_years = sorted(int(y) for y in month_df["统计年份"].dropna().unique())
    with st.sidebar:
        st.markdown("---")
        st.header("年份筛选")
        selected_years = st.multiselect(
            "年份", options=all_years, default=all_years, label_visibility="collapsed")
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
        st.header("月份筛选")
        show_months = st.multiselect(
            "月份", options=months, default=months, label_visibility="collapsed")
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

    if not prev_ok:
        st.caption(f"缺 {prev_year}年月度数据，同比暂无法计算。")

    annual_sp = yoy_table(sp, [])
    partner_sp = yoy_table(sp, ["贸易伙伴名称", "所属区域"])
    province_sp = yoy_table(sp, ["注册地名称"])
    region_sp = yoy_table(sp, ["所属区域"])

    cur_total = float(annual_sp.loc[annual_sp["统计年份"] == latest, "金额_美元"].sum()) if not annual_sp.empty else 0.0
    cur_yoy = annual_sp.loc[annual_sp["统计年份"] == latest, "金额同比%"]
    cur_yoy = cur_yoy.iloc[0] if len(cur_yoy) and pd.notna(cur_yoy.iloc[0]) else None
    prev_total = float(annual_sp.loc[annual_sp["统计年份"] == prev_year, "金额_美元"].sum()) if prev_ok else None

    # 最新月环比（本月对上月；1月对上年12月）
    _ly = month_df[month_df["统计年份"] == latest].groupby("月份")["金额_美元"].sum()
    _lm = max(show_months) if show_months else (int(_ly.index.max()) if len(_ly) else None)
    mom_label, mom_val, mom_delta = "最新月环比", "—", None
    if _lm is not None and _lm in _ly.index:
        if _lm == 1:
            _pv = float(month_df[(month_df["统计年份"] == latest - 1) & (month_df["月份"] == 12)]["金额_美元"].sum())
        else:
            _pv = float(_ly.get(_lm - 1, 0))
        _cv = float(_ly[_lm])
        if _pv > 0:
            mom_label = f"{int(_lm)}月环比"
            mom_val = fmt_money(_cv)
            mom_delta = f"{(_cv - _pv) / _pv * 100:+.1f}%"

    st.markdown(f"### {latest}年{plabel}全球市场贸易格局透视")
    ca, cb, cc = st.columns(3)
    ca.metric(f"{latest}年{plabel}出口总额", fmt_money(cur_total),
              delta=(f"{cur_yoy:+.2f}%" if cur_yoy is not None else None))
    cb.metric(f"{prev_year}年同期", fmt_money(prev_total) if prev_total is not None else "无月度数据")
    cc.metric(mom_label, mom_val, delta=mom_delta)

    # 出口流向世界地图（销往哪里）
    st.subheader("出口流向（销往哪里）")
    st.caption("线条由中国指向各目的地，粗细/圆点大小随出口额；仅显示主要贸易伙伴")
    render_flow_map(sp, latest)

    st.markdown("---")

    if analysis_mode == "月度动态演变":
        ly = (month_df[month_df["统计年份"] == latest]
              .groupby("月份", as_index=False)["金额_美元"].sum().sort_values("月份"))
        if not ly.empty:
            ly["金额_亿"] = ly["金额_美元"] / 1e8
            ly["月标签"] = ly["月份"].astype(int).astype(str) + "月"
            # 环比：本月对上月（1月对上年12月）
            prev_dec = float(month_df[(month_df["统计年份"] == latest - 1) &
                                      (month_df["月份"] == 12)]["金额_美元"].sum())
            base = [prev_dec] + ly["金额_美元"].tolist()[:-1]
            ly["环比%"] = np.where(np.array(base) > 0,
                                  (ly["金额_美元"].values - np.array(base)) / np.array(base) * 100, np.nan).round(1)
            if prev_dec <= 0:
                ly.loc[ly.index[0], "环比%"] = np.nan
            # 同比：本月对上年同月
            py = month_df[month_df["统计年份"] == latest - 1].groupby("月份")["金额_美元"].sum()
            ly["同比%"] = [round((v - py.get(m, np.nan)) / py.get(m, np.nan) * 100, 1)
                          if py.get(m, 0) > 0 else np.nan
                          for m, v in zip(ly["月份"], ly["金额_美元"])]

            def _bar_line(metric, color, dash=None):
                f = px.bar(ly, x="月标签", y="金额_亿", text_auto=".2f")
                f.update_traces(marker_color="#4d4d4d", name="金额", showlegend=True)
                f.update_yaxes(title_text="金额（亿美元）"); f.update_xaxes(title_text="")
                f.add_scatter(x=ly["月标签"], y=ly[metric], name=metric, yaxis="y2",
                              mode="lines+markers+text", line=dict(color=color, width=2, dash=dash),
                              text=[f"{v:+.1f}%" if pd.notna(v) else "" for v in ly[metric]],
                              textposition="top center", textfont=dict(color=color))
                f.update_layout(yaxis2=dict(title=metric, overlaying="y", side="right",
                                            showgrid=False, zeroline=True, zerolinecolor="#e8e8e8"),
                                legend=dict(orientation="h", y=1.14))
                return f

            st.subheader(f"{latest}年月度出口额与同比")
            st.plotly_chart(_bar_line("同比%", "#ff682c"), width='stretch')

            st.subheader(f"{latest}年月度出口额与环比")
            st.plotly_chart(_bar_line("环比%", "#816729"), width='stretch')

            tshow = ly[["月标签", "金额_美元", "同比%", "环比%"]].copy()
            st.dataframe(disp_money(tshow, ["金额_美元"]).rename(columns={"月标签": "月份"}),
                         width='stretch', hide_index=True)
            # 季度环比（数据满足时）
            mv = dict(zip(ly["月份"].astype(int), ly["金额_美元"]))
            if all(q in mv for q in [1, 2, 3]) and all(q in mv for q in [4, 5, 6]):
                q1 = mv[1] + mv[2] + mv[3]; q2 = mv[4] + mv[5] + mv[6]
                st.markdown(f"**季度环比**：二季度 {q2/1e8:.2f}亿美元 vs 一季度 {q1/1e8:.2f}亿美元，"
                            f"环比 **{(q2-q1)/q1*100:+.1f}%**")

    else:
        st.subheader(f"历年{plabel}出口额")
        st.caption("单位：亿美元")
        if not annual_sp.empty:
            bar = annual_sp.copy()
            bar["年份"] = bar["统计年份"].astype(str)
            bar["金额_亿"] = bar["金额_美元"] / 1e8
            fig0 = px.area(bar.sort_values("统计年份"), x="年份", y="金额_亿", markers=True)
            fig0.update_traces(line_color="#ff682c", line_width=2,
                               fillcolor="rgba(255,104,44,0.10)",
                               marker=dict(size=6, color="#ff682c"),
                               hovertemplate="%{x}<br>%{y:.2f}亿美元<extra></extra>")
            fig0.update_yaxes(title_text="金额（亿美元）"); fig0.update_xaxes(title_text="")
            st.plotly_chart(fig0, width='stretch')
            show = disp_money(annual_sp[["统计年份", "金额_美元", "上年同期", "金额同比%"]],
                              ["金额_美元", "上年同期"])
            show.columns = ["年份", f"{plabel}出口额（亿美元）", "上年同期（亿美元）", "同比%"]
            st.dataframe(show, width='stretch', hide_index=True)

    render_period_analysis(sp, partner_sp, province_sp, region_sp, latest, prev_year, prev_ok, plabel, cur_total)

    st.markdown("---")

    # 历年全年：优先用月度数据里『满12个月』的年份汇总出真实全年总额，
    # 没有月度数据来源的年份再用年度（全年快照）文件补充；不满12个月的年份一律排除。
    if analysis_mode == "年度动态演变":
        st.markdown("---")
        st.subheader("历年全年出口额")
        st.caption("单位：亿美元")

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
            yb = yfull.copy(); yb["年份"] = yb["统计年份"].astype(str); yb["金额_亿"] = yb["金额_美元"] / 1e8
            fig_y = px.bar(yb, x="年份", y="金额_亿", text_auto=".2f")
            fig_y.update_yaxes(title_text="金额（亿美元）")
            st.plotly_chart(fig_y, width='stretch')
            ys = disp_money(yfull[["统计年份", "金额_美元", "上年同期", "金额同比%"]], ["金额_美元", "上年同期"])
            ys.columns = ["年份", "全年出口额（亿美元）", "上年（亿美元）", "同比%"]
            st.dataframe(ys, width='stretch', hide_index=True)

        if incomplete_years_from_month:
            st.caption(f"注：{incomplete_years_from_month}年数据不满12个月，未纳入全年视图。")

# ---------- 没有月度数据：只能快照（如水龙头只有单一年份）----------
else:
    # 年度数据（无月度，如龙头/浴缸等）：走完整年度大屏
    all_years = sorted(int(y) for y in year_df["统计年份"].dropna().unique())
    if not all_years:
        st.info("该数据集无有效年份数据。")
        st.stop()
    with st.sidebar:
        st.markdown("---")
        st.header("年份筛选")
        selected_years = st.multiselect("年份", options=all_years, default=all_years,
                                        label_visibility="collapsed")
    if not selected_years:
        selected_years = all_years

    sp = year_df[year_df["统计年份"].isin(selected_years)].copy()
    latest = int(sp["统计年份"].max())
    prev_year = latest - 1
    prev_ok = prev_year in selected_years
    plabel = "全年"

    annual_a = yoy_table(sp, [])
    partner_sp = yoy_table(sp, ["贸易伙伴名称", "所属区域"])
    province_sp = yoy_table(sp, ["注册地名称"])
    region_sp = yoy_table(sp, ["所属区域"])

    cur_total = float(annual_a.loc[annual_a["统计年份"] == latest, "金额_美元"].sum()) if not annual_a.empty else 0.0
    cur_yoy = annual_a.loc[annual_a["统计年份"] == latest, "金额同比%"]
    cur_yoy = cur_yoy.iloc[0] if len(cur_yoy) and pd.notna(cur_yoy.iloc[0]) else None
    prev_total = float(annual_a.loc[annual_a["统计年份"] == prev_year, "金额_美元"].sum()) if prev_ok else None

    st.markdown(f"### {latest}年全年全球市场贸易格局透视")
    ca, cb, cc = st.columns(3)
    ca.metric(f"{latest}年出口总额", fmt_money(cur_total),
              delta=(f"{cur_yoy:+.2f}%" if cur_yoy is not None else None))
    cb.metric(f"{prev_year}年同期", fmt_money(prev_total) if prev_total is not None else "无数据")
    cc.metric("活跃目的地数量", int(sp.loc[sp["统计年份"] == latest, "贸易伙伴名称"].nunique()))

    st.subheader("出口流向（销往哪里）")
    st.caption("线条由中国指向各目的地，粗细/圆点大小随出口额；仅显示主要贸易伙伴")
    render_flow_map(sp, latest)

    st.markdown("---")

    st.subheader("历年全年出口额")
    st.caption("单位：亿美元")
    if not annual_a.empty:
        bar = annual_a.copy(); bar["年份"] = bar["统计年份"].astype(str); bar["金额_亿"] = bar["金额_美元"] / 1e8
        fig0 = px.area(bar.sort_values("统计年份"), x="年份", y="金额_亿", markers=True)
        fig0.update_traces(line_color="#ff682c", line_width=2, fillcolor="rgba(255,104,44,0.10)",
                           marker=dict(size=6, color="#ff682c"),
                           hovertemplate="%{x}<br>%{y:.2f}亿美元<extra></extra>")
        fig0.update_yaxes(title_text="金额（亿美元）"); fig0.update_xaxes(title_text="")
        st.plotly_chart(fig0, width='stretch')
        show = disp_money(annual_a[["统计年份", "金额_美元", "上年同期", "金额同比%"]], ["金额_美元", "上年同期"])
        show.columns = ["年份", "全年出口额（亿美元）", "上年同期（亿美元）", "同比%"]
        st.dataframe(show, width='stretch', hide_index=True)

    render_period_analysis(sp, partner_sp, province_sp, region_sp,
                           latest, prev_year, prev_ok, plabel, cur_total)

st.markdown("""
<div class="footer">
  <div class="col">
    作者 · sze　交流 · <a href="tel:13760765317">137-6076-5317</a><br>
    数据来源：中国海关数据 · 仅供研究参考
  </div>
</div>
""", unsafe_allow_html=True)
