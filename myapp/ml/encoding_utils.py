import pickle
import numpy as np
import pandas as pd
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
#ASSETS_PATH = r"F:/桃竹苗/final/m/encoding_assets.pkl"
ASSETS_PATH = BASE_DIR / "m" / "encoding_assets.pkl"


with open(ASSETS_PATH, "rb") as f:
    ASSETS = pickle.load(f)


def get_prediction_encoded_values(df_subset, assets=None):
    if assets is None:
        assets = ASSETS
    #print("DEBUG 完整行政區:", df_subset["完整行政區"].iloc[0])
    #print("DEBUG dist_map value:", df_subset["完整行政區"].map(assets["dist_map"]).iloc[0])
    #print("DEBUG city_map value:", df_subset["縣市"].map(assets["city_map"]).iloc[0])
    #print("DEBUG global_final_mean:", assets["global_final_mean"])
    idx = df_subset.index

    p_val = df_subset["建案名稱"].map(assets["proj_map"])
    g_val = df_subset["唯一地理位置"].map(assets["geo_map"])
    d_val = df_subset["完整行政區"].map(assets["dist_map"])
    c_val = df_subset["縣市"].map(assets["city_map"])

    p_cnt = df_subset["建案名稱"].map(assets["proj_counts"]).fillna(0)
    g_cnt = df_subset["唯一地理位置"].map(assets["geo_counts"]).fillna(0)

    g_val_fixed = pd.Series(
        np.where(g_cnt <= 15, d_val, g_val),
        index=idx
    )

    presale_logic = d_val.fillna(c_val)
    house_logic = (
        g_val_fixed
        .fillna(d_val)
        .fillna(c_val)
        .fillna(assets["global_final_mean"])
    )

    encoded = np.where(
        df_subset["is_presale"].values == 1,
        presale_logic,
        house_logic
    )

    return np.log1p(pd.Series(encoded, index=idx))


def get_area_price_feature(df_to_predict, assets=None, verbose=False):
    if assets is None:
        assets = ASSETS

    df_to_predict = df_to_predict.copy()
    df_to_predict["time_index"] = df_to_predict["time_index"].astype(float)

    df_pred = df_to_predict.copy()
    original_index = df_pred.index

    hist = assets["historical_area_market"].copy()
    hist = hist[["完整行政區", "time_index", "area_last_month_price"]].dropna()

    df_pred = df_pred.reset_index(names="original_index")

    df_pred["完整行政區"] = df_pred["完整行政區"].astype(str)
    hist["完整行政區"] = hist["完整行政區"].astype(str)

    df_pred["time_index"] = pd.to_numeric(df_pred["time_index"], errors="coerce")
    hist["time_index"] = pd.to_numeric(hist["time_index"], errors="coerce")

    hist = hist.dropna(subset=["完整行政區", "time_index"])
    df_pred = df_pred.dropna(subset=["完整行政區", "time_index"])

    parts = []

    for dist, left_g in df_pred.groupby("完整行政區", sort=False):
        right_g = hist[hist["完整行政區"] == dist].copy()
        left_g = left_g.sort_values("time_index")

        if len(right_g) == 0:
            left_g["area_last_month_price"] = np.nan
            left_g["match_level"] = "no_dist_history"
            parts.append(left_g)
            continue

        right_g = right_g.sort_values("time_index")

        merged_g = pd.merge_asof(
            left_g,
            right_g[["time_index", "area_last_month_price"]],
            on="time_index",
            direction="backward",
            allow_exact_matches=False,
        )

        merged_g["match_level"] = np.where(
            merged_g["area_last_month_price"].notna(),
            "完整行政區歷史",
            "完整行政區無可用過去月份",
        )

        parts.append(merged_g)

    res = pd.concat(parts, axis=0)

    before_fallback_na = res["area_last_month_price"].isna()

    dist_fallback = res["完整行政區"].map(
        {str(k): v for k, v in assets["dist_map"].items()}
    )

    city_fallback = res["縣市"].map(assets["city_map"])

    use_dist_fallback = before_fallback_na & dist_fallback.notna()
    res.loc[use_dist_fallback, "match_level"] = "完整行政區均價補值"

    res["area_last_month_price"] = res["area_last_month_price"].fillna(dist_fallback)

    after_dist_na = res["area_last_month_price"].isna()
    use_city_fallback = after_dist_na & city_fallback.notna()
    res.loc[use_city_fallback, "match_level"] = "縣市均價補值"

    res["area_last_month_price"] = res["area_last_month_price"].fillna(city_fallback)

    after_city_na = res["area_last_month_price"].isna()
    res.loc[after_city_na, "match_level"] = "全域均價補值"

    res["area_last_month_price"] = res["area_last_month_price"].fillna(
        assets["global_final_mean"]
    )

    if verbose:
        print("area_last_month_price 匹配統計：")
        print(res["match_level"].value_counts(dropna=False))

    result = res.set_index("original_index")["area_last_month_price"]

    return result.reindex(original_index)


def get_area_price_match_level(df_to_predict, assets=None):
    """
    給前端顯示用：回傳 area_last_month_price 是怎麼補到的。
    單筆預測時很好用。
    """
    if assets is None:
        assets = ASSETS

    df_to_predict = df_to_predict.copy()
    hist = assets["historical_area_market"].copy()
    hist = hist[["完整行政區", "time_index", "area_last_month_price"]].dropna()

    dist = str(df_to_predict.iloc[0]["完整行政區"])
    time_index = float(df_to_predict.iloc[0]["time_index"])

    hist["完整行政區"] = hist["完整行政區"].astype(str)
    hist["time_index"] = pd.to_numeric(hist["time_index"], errors="coerce")

    right_g = hist[hist["完整行政區"] == dist].sort_values("time_index")

    if len(right_g) > 0:
        past = right_g[right_g["time_index"] < time_index]
        if len(past) > 0:
            return "完整行政區歷史"

    if dist in {str(k): v for k, v in assets["dist_map"].items()}:
        return "完整行政區均價補值"

    city = df_to_predict.iloc[0]["縣市"]

    if city in assets["city_map"]:
        return "縣市均價補值"

    return "全域均價補值"
