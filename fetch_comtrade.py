# -*- coding: utf-8 -*-
"""
UN Comtrade 全球出口数据拉取脚本（用于"全球份额"分析）。

用法：
  1. pip install comtradeapicall pandas pyarrow
  2. 去 https://comtradedeveloper.un.org 注册，订阅免费套餐，拿 subscription key
  3. 把 key 填到下面 SUBSCRIPTION_KEY（或设环境变量 COMTRADE_KEY）
  4. 按需改 CATEGORIES / YEARS，然后 python fetch_comtrade.py

口径：flow=X(出口)、partner=World(0)、reporter=全部国家、freq=A(年度)、HS 6位。
输出：raw_data/comtrade/{品类}_global.parquet （列：品类,年份,报告方,ISO,HS,出口额USD,净重kg）
"""
import os
import time
import pandas as pd

def _load_key():
    # 优先环境变量，其次本地 .comtrade_key 文件（都不进 git），最后占位符
    k = os.environ.get("COMTRADE_KEY", "").strip()
    if not k and os.path.exists(".comtrade_key"):
        k = open(".comtrade_key", encoding="utf-8").read().strip()
    return k or "在这里填你的key"


SUBSCRIPTION_KEY = _load_key()

OUT_DIR = "raw_data/comtrade"
os.makedirs(OUT_DIR, exist_ok=True)

# 各品类 → HS 6位码（Comtrade 只到6位；中国8位码在此合并对应）
CATEGORIES = {
    "陶瓷卫浴":   ["691010", "691090"],                       # 缺口：整段
    "钢制卫浴":   ["732410", "732421", "732429", "732490"],   # 缺口：整段
    "塑料卫浴":   ["392210", "392220", "392290"],             # 补 2024/25 或统一到6位
    "水龙头":     ["741820", "761520", "848180", "848190"],   # 补 2024/25、重拉2013/1999
}

# 要拉的年份（先补最缺的近年；确认没问题再往前补）
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

SLEEP = 1.5          # 每次调用间隔（避免触发限流）
RETRY = 3


def fetch_one(call, key, cats, cmd, year):
    """拉某品类某年的全球数据；失败重试。"""
    for attempt in range(1, RETRY + 1):
        try:
            df = call.getFinalData(
                key, typeCode="C", freqCode="A", clCode="HS",
                period=str(year),
                reporterCode=None,       # 全部报告国
                cmdCode=",".join(cmd),
                flowCode="X",            # 出口
                partnerCode="0",         # 对世界（World）
                partner2Code="0", customsCode="C00", motCode="0",  # 聚合口径
                maxRecords=250000, format_output="JSON", includeDesc=True,
            )
            if df is None or len(df) == 0:
                print(f"    {cats} {year}: 无数据")
                return None
            return df
        except Exception as e:
            print(f"    {cats} {year}: 第{attempt}次失败 {e}")
            time.sleep(SLEEP * attempt)
    return None


def main():
    try:
        import comtradeapicall as call
    except ImportError:
        print("缺少依赖：pip install comtradeapicall")
        return
    if "填你的key" in SUBSCRIPTION_KEY:
        print("请先填 SUBSCRIPTION_KEY（或设环境变量 COMTRADE_KEY）")
        return

    for cat, cmds in CATEGORIES.items():
        print(f"\n📦 {cat}  HS={cmds}")
        parts = []
        for yr in YEARS:
            df = fetch_one(call, SUBSCRIPTION_KEY, cat, cmds, yr)
            if df is not None:
                parts.append(df)
                print(f"    {yr}: {len(df):,} 行")
            time.sleep(SLEEP)
        if not parts:
            print(f"  （{cat} 无数据，跳过）")
            continue
        raw = pd.concat(parts, ignore_index=True)
        # 统一精简列（不同版本字段名大小写可能不同，做兼容）
        def pick(*names):
            for n in names:
                if n in raw.columns:
                    return n
            return None
        out = pd.DataFrame({
            "品类": cat,
            "年份": pd.to_numeric(raw[pick("refYear", "RefYear")], errors="coerce"),
            "报告方": raw[pick("reporterDesc", "ReporterDesc")],
            "ISO": raw[pick("reporterISO", "ReporterISO")],
            "HS": raw[pick("cmdCode", "CmdCode")].astype(str),
            "出口额USD": pd.to_numeric(raw[pick("primaryValue", "PrimaryValue", "fobvalue", "Fobvalue")], errors="coerce"),
            "净重kg": pd.to_numeric(raw[pick("netWgt", "NetWgt")], errors="coerce"),
        })
        out = out[out["出口额USD"].fillna(0) > 0]
        raw_path = os.path.join(OUT_DIR, f"{cat}_global_raw.csv")
        pq_path = os.path.join(OUT_DIR, f"{cat}_global.parquet")
        raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
        out.to_parquet(pq_path, index=False)
        print(f"  🎉 {cat}: {len(out):,} 行 → {pq_path}")

    print("\n✅ 完成。提示：2024/25 若返回空，是各国还没上报（Comtrade 有滞后），过段时间再拉。")


if __name__ == "__main__":
    main()
