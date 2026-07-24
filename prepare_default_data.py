import pandas as pd
import os
import re
import numpy as np

# ================= 配置 =================
RAW_DATA_FOLDER = "raw_data"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAPPING_FILE = "区域映射表.xlsx"

# ================= 字段定义 =================
FIELD_SPECS = {
    "贸易伙伴名称": {"candidates": ["贸易伙伴名称","贸易伙伴名称称","贸易伙伴名","国家/地区","国家地区","目的地","partnerDesc","PartnerDesc","partner_desc","partnerName","partner","country","Country","COUNTRY","Partner","Trade Partner","destination","Destination","Country/Region","CountryName"]},
    "金额_美元": {"candidates": ["金额_美元","美元","出口金额_美元","金额（美元）","金额(美元)","fobvalue","fobValue","FOBValue","fob_value","tradeValue","TradeValue","USD","Amount_USD","Value_USD","Export Value","export_value","金额","Amount","Value","usd_value","usd_amount"]},
    "注册地名称": {"candidates": ["注册地名称","注册地","省份","出口地区","企业注册地","reporterDesc","ReporterDesc","reporter_desc","reporterName","reporter","Province","province","Region","region","Registered Region","Origin Province"]},
    "贸易类型": {"candidates": ["贸易类型","进出口类型","贸易方式","flowDesc","FlowDesc","flow_desc","flowCode","flow","Trade Type","trade_type","Type","type","Direction","direction"]},
    "数量_统一": {"candidates": ["第一法定数量","统计数量","法定数量","净重（千克）","总重量（千克）","重量","netWgt","NetWgt","net_wgt","netWeight","grossWgt","qty","Qty","Quantity","quantity","Weight","weight","Net Weight","net_weight","数量"]},
    "数据年月": {"candidates": ["数据年月","年月","统计月份","月份","报告期","period","Period","PERIOD","yearMonth","YearMonth"]},
    "统计年份": {"candidates": ["统计年份","年份","year","Year","YEAR","fiscal_year","统计年度","refYear"]},
    "产品分类": {"candidates": ["产品分类","材质","品类","category","Category","material","Material"]},
}


def match_columns(df_cols, field_specs):
    """排他性字段匹配：一个源列只映射到一个目标字段。"""
    used_cols = set()
    mapping = {}
    # 阶段1：精确匹配
    for field, spec in field_specs.items():
        for cand in spec["candidates"]:
            if cand in df_cols and cand not in used_cols:
                mapping[field] = cand
                used_cols.add(cand)
                break
    # 阶段2：忽略大小写
    df_cols_lower = {c.lower(): c for c in df_cols if c not in used_cols}
    for field, spec in field_specs.items():
        if field in mapping:
            continue
        for cand in spec["candidates"]:
            cl = cand.lower()
            if cl in df_cols_lower:
                actual = df_cols_lower[cl]
                mapping[field] = actual
                used_cols.add(actual)
                del df_cols_lower[cl]
                break
    # 阶段3：关键字兜底
    keywords_map = {
        "金额_美元": ["美元", "usd", "amount", "value", "金额"],
        "数量_统一": ["qty", "weight", "quantity", "数量", "重量", "净重"],
        "贸易伙伴名称": ["partner", "country", "destination", "国家", "地区", "目的地"],
        "注册地名称": ["province", "region", "reporter", "省份", "注册地", "企业"],
        "数据年月": ["yearmonth", "period", "年月", "报告期"],
        "统计年份": ["year", "年份", "年度"],
    }
    for field, keywords in keywords_map.items():
        if field in mapping:
            continue
        for col in df_cols:
            if col in used_cols:
                continue
            if any(kw in col.lower() for kw in keywords):
                mapping[field] = col
                used_cols.add(col)
                break
    return mapping


def extract_year(df, year_col, filename=""):
    if year_col and year_col in df.columns:
        vals = df[year_col].dropna().astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
        ext = vals.str.extract(r'(20\d{2})')[0].dropna()
        if not ext.empty:
            return str(ext.mode()[0])
    m = re.search(r'(20\d{2})', filename)
    return m.group(1) if m else None


def parse_month_series(s):
    """从『数据年月』源列解析出 1–12 的整数月份；解析不出来返回 NaN。
       支持 202601 / 2026-01 / 2026/01 / 单独的 1~12。"""
    txt = s.astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    txt = txt.str.replace(r'[/.]', '-', regex=True)
    out = pd.Series(np.nan, index=s.index, dtype="float")
    # YYYYMM (6位)
    m6 = txt.str.fullmatch(r'(20\d{2})(\d{2})')
    out[m6.fillna(False)] = pd.to_numeric(txt[m6.fillna(False)].str[-2:], errors="coerce")
    # YYYY-MM
    mdash = txt.str.fullmatch(r'20\d{2}-\d{1,2}')
    out[mdash.fillna(False)] = pd.to_numeric(
        txt[mdash.fillna(False)].str.split('-').str[1], errors="coerce")
    # 纯月份 1~12
    mraw = txt.str.fullmatch(r'\d{1,2}')
    out[mraw.fillna(False)] = pd.to_numeric(txt[mraw.fillna(False)], errors="coerce")
    out = out.where((out >= 1) & (out <= 12))
    return out


print("🚀 开始生成内置标准数据（修正版：真实月份 + 粒度标记 + 不再重复计数）...")

# 区域映射
region_dict = {}
if os.path.exists(MAPPING_FILE):
    try:
        map_df = pd.read_excel(MAPPING_FILE, sheet_name="区域映射")
        on = map_df["原始名称"].astype(str).str.strip()
        sr = map_df["子区域"].astype(str).str.strip().fillna("其他")
        region_dict = dict(zip(on, sr))
        print(f"✅ 区域映射表已加载：{len(region_dict)} 条")
    except Exception as e:
        print(f"⚠️ 映射表读取异常（区域将归为「其他」）：{e}")


# 数据集配置：名称 → (文件名匹配函数, 输出parquet名)
DATASET_MATCHERS = {
    "6910":   (lambda b: "6910" in b,                                        "6910"),
    "水龙头":  (lambda b: "faucet" in b.lower() or "水龙头" in b,                "faucet"),
    # 塑料卫浴：合并 39221000(浴缸/淋浴盘/洗涤槽/脸盆) + 39222000(坐便器盖) + 39229000(其他)
    "塑料卫浴": (lambda b: b.startswith(("39221000", "39222000", "39229000")), "plastic"),
    # 钢制浴缸：73242100(搪瓷铸铁浴缸) + 73242900(其他钢铁浴缸)
    "钢制浴缸": (lambda b: b.startswith(("73242100", "73242900")),             "steel_bath"),
    # 其他钢制卫浴：73241000(不锈钢水槽) + 73249000(其他钢铁卫生器具及零件)
    "其他钢制卫浴": (lambda b: b.startswith(("73241000", "73249000")),          "steel_other"),
}


def unified_kg(df):
    """把数量统一到『千克』：优先取计量单位为千克的那一列（第一/第二数量），
       84818090 这类第一单位是『套』的会自动改用第二数量（千克）；
       再兜底『总重量（千克）』『净重（千克）』；都没有则记 0。
       这样各 HS 码可比，单价 = 金额/千克 = 美元/千克。"""
    kg = pd.Series(np.nan, index=df.index, dtype="float")
    def c(name): return df[name] if name in df.columns else None
    for qcol, ucol in [("第一数量", "第一计量单位"), ("第二数量", "第二计量单位")]:
        q, u = c(qcol), c(ucol)
        if q is not None and u is not None:
            m = u.astype(str).str.contains("千克", na=False) & kg.isna()
            kg = kg.where(~m, pd.to_numeric(q, errors="coerce"))
    for wcol in ["总重量（千克）", "净重（千克）"]:
        w = c(wcol)
        if w is not None:
            need = kg.isna()
            kg = kg.where(~need, pd.to_numeric(w, errors="coerce"))
    return kg.fillna(0.0).clip(lower=0)


def process_files(dataset_name):
    files = []
    for root, _, fnames in os.walk(RAW_DATA_FOLDER):
        for f in fnames:
            if f.lower().endswith(('.xlsx', '.xls')):
                files.append(os.path.join(root, f))

    matcher, out_name = DATASET_MATCHERS[dataset_name]
    targets = [f for f in files if matcher(os.path.basename(f))]

    print(f"\n📦 数据集 [{dataset_name}]：匹配到 {len(targets)} 个文件")
    all_data = []
    for full in targets:
        fname = os.path.basename(full)
        try:
            df = pd.read_excel(full)
            if df.empty:
                continue
            # 先按原始列算出统一到千克的数量（在改名前，列名还是第一/第二数量）
            df["__kg__"] = unified_kg(df)
            cmap = match_columns(list(df.columns), FIELD_SPECS)

            # —— 月份 + 年份：有『数据年月』就以它为准（逐行取年/月），
            #    否则靠年份列/文件名。避免文件名里 HS 编码含"2000"等被误判为年份。——
            if "数据年月" in cmap:
                month = parse_month_series(df[cmap["数据年月"]])
                year_series = pd.to_numeric(
                    df[cmap["数据年月"]].astype(str).str.extract(r'(20\d{2})')[0], errors="coerce")
                granularity = "月度"
                year_str = str(int(year_series.dropna().mode()[0])) if year_series.notna().any() else None
            else:
                month = pd.Series(np.nan, index=df.index)
                year_series = None
                granularity = "年度"
                year_col = cmap.get("统计年份")
                year_str = extract_year(df, year_col, fname)
            if not year_str:
                print(f"  ⚠️ {fname} 无法确定年份，跳过")
                continue

            # 重命名其它字段
            rename_map = {src: key for key, src in cmap.items()
                          if key not in ["统计年份", "数据年月"]}
            df = df.rename(columns=rename_map)

            # 关键维度补齐
            df["统计年份"] = (year_series.astype("Int64").values
                            if year_series is not None else int(year_str))
            df["月份"] = month.values
            df["数据粒度"] = granularity
            df["贸易类型"] = "出口"

            # 数量统一用千克口径（__kg__ 在读文件时已按计量单位算好）
            df["数量_统一"] = pd.to_numeric(df.get("__kg__", 0.0), errors="coerce").fillna(0.0)

            df["注册地名称"] = (df["注册地名称"].astype(str).str.strip()
                              if "注册地名称" in df.columns else "未知")

            if "贸易伙伴名称" not in df.columns:
                print(f"  ⚠️ {fname} 缺少『贸易伙伴名称』，跳过")
                continue
            df["贸易伙伴名称"] = df["贸易伙伴名称"].astype(str).str.strip()
            df = df.dropna(subset=["贸易伙伴名称"])
            df = df[df["贸易伙伴名称"].str.len() > 0]

            df["金额_美元"] = (pd.to_numeric(
                df["金额_美元"].astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0.0)
                if "金额_美元" in df.columns else 0.0)
            df = df[df["金额_美元"] != 0]

            if "产品分类" not in df.columns:
                df["产品分类"] = ""
            else:
                df["产品分类"] = df["产品分类"].astype(str).str.strip()

            df["所属区域"] = df["贸易伙伴名称"].map(region_dict).fillna("其他")

            cols = ["贸易伙伴名称", "注册地名称", "贸易类型", "金额_美元", "数量_统一",
                    "统计年份", "月份", "数据粒度", "产品分类", "所属区域"]
            all_data.append(df[cols])
            mtag = "(月度)" if granularity == "月度" else "(年度)"
            print(f"  ✔ {fname} {mtag} 载入 {len(df):,} 行，年份 {year_str}")
        except Exception as e:
            print(f"  ❌ {fname} 解析失败：{e}")

    if not all_data:
        print(f"  （数据集 [{dataset_name}] 无可用数据）")
        return False

    final = pd.concat(all_data, ignore_index=True)

    # —— 防重复计数：同一年若既有月度又有年度，丢弃该年的年度行（月度更细，是同口径来源）——
    has_month_years = set(final.loc[final["数据粒度"] == "月度", "统计年份"].unique())
    before = len(final)
    drop_mask = (final["数据粒度"] == "年度") & (final["统计年份"].isin(has_month_years))
    if drop_mask.any():
        dropped_years = sorted(final.loc[drop_mask, "统计年份"].unique())
        final = final[~drop_mask].copy()
        print(f"  🧹 防重复：{dropped_years} 年同时存在月度与年度文件，已丢弃年度行 "
              f"（{before-len(final):,} 行），以月度为准")

    # —— 预聚合：应用侧只用到 年/月/区域/省份/目的地 维度，按此汇总金额与数量，
    #    丢弃商品编码/产品分类等明细行，行数大减、加载更快（尤其浏览器 WASM 部署）——
    before_agg = len(final)
    dims = ["统计年份", "月份", "数据粒度", "所属区域", "注册地名称", "贸易伙伴名称"]
    final = (final.groupby(dims, dropna=False, as_index=False)
                  .agg({"金额_美元": "sum", "数量_统一": "sum"}))
    final["贸易类型"] = "出口"

    out_path = os.path.join(OUTPUT_DIR, f"default_{out_name}.parquet")
    final.to_parquet(out_path, compression="snappy", index=False)
    span = final.groupby(["统计年份", "数据粒度"]).size().to_dict()
    print(f"  🎉 写出 {out_path}（预聚合 {before_agg:,} → {len(final):,} 行）；分布 {span}")
    return True


process_files("6910")
process_files("水龙头")
process_files("塑料卫浴")
process_files("钢制浴缸")
process_files("其他钢制卫浴")
print("\n✅ 全部完成。提醒：要做『前N月同比』，每个对比年份都需有对应的月度文件(含数据年月)。")
