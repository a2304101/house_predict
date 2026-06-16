import pandas as pd
from datetime import datetime
import re
from .address_utils import build_clean_address
from .geocode_utils import geocode_address
from .poi_utils import GEO_SERVICE
from django.core.cache import cache
import time
import hashlib
import json
from .encoding_utils import (
    get_area_price_feature,
    get_prediction_encoded_values,
    get_area_price_match_level,
)
# 之後你可以把這兩個函式也獨立出去讀 assets






BUILDING_MAIN_RATIO = {
    "住宅大樓(11層含以上有電梯)": 0.62,
    "華廈(10層含以下有電梯)": 0.7,
    "公寓(5樓含以下無電梯)": 0.85,
    "透天厝": 0.95,
    "其他": 0.8,
    "套房(1房1廳1衛)": 0.55,
}

def extract_unique_geo(address, city, district):
    address = str(address)
    city = str(city) if city else ""
    district = str(district) if district else ""
    city_dist = city + "_" + district

    clean_addr = address

    while True:
        prev_addr = clean_addr

        if city and clean_addr.startswith(city):
            clean_addr = clean_addr[len(city):].strip()

        if district and clean_addr.startswith(district):
            clean_addr = clean_addr[len(district):].strip()

        if clean_addr == prev_addr:
            break

    clean_addr = re.sub(r"\d+鄰", "", clean_addr)
    clean_addr = clean_addr.strip()

    m = re.search(
        r"(.+?路[\d一二三四五六七八九十]+段|.+?段|.+?(?:大道|園區|縣道)|.+?[路街])",
        clean_addr,
    )
    if m:
        target = re.sub(r"^.+?[村里]", "", m.group(1))
        return city_dist + "_" + target

    m = re.search(r"(.+?(?:巷|弄))", clean_addr)
    if m:
        target = re.sub(r"^.+?[村里]", "", m.group(1))
        return city_dist + "_" + target

    m = re.search(r"(.+?[村里])", clean_addr)
    if m:
        return city_dist + "_" + m.group(1)

    m = re.search(r"^([^\d地號]+)", clean_addr)
    if m and m.group(1).strip():
        return city_dist + "_" + m.group(1).strip()

    if re.search(r"\d+", clean_addr) or "地號" in clean_addr:
        return city_dist + "_區域內地號或門牌"

    return None

MODEL_COLUMNS = [
    "縣市",
    "鄉鎮市區",
    "交易距今月數",
    "成交年",
    "成交月",
    "完整行政區",
    "屋齡",
    "建物型態",
    "坪數",
    "移轉層次",
    "總樓層數",
    "電梯",
    "is_presale",
    "age_was_missing",
    "主建物坪數",
    "time_index",
    "area_last_month_price",
    "總_編碼",
    "坪數_屋齡_交互",
    "緯度",
    "經度",
    "poi_convenience_count_300m",
    "poi_convenience_count_500m",
    "poi_bank_count_500m",
    "poi_food_count_300m",
    "poi_food_count_500m",
    "poi_medical_count_500m",
    "poi_parking_count_500m",
    "distance_to_nearest_worship_m",
    "distance_to_thsr_m",
    "distance_to_tra_m",
    "distance_to_mrt_m",
]


CATEGORY_COLUMNS = [
    "縣市",
    "鄉鎮市區",
    "完整行政區",
    "建物型態",
]


def normalize_region(df):
    df["完整行政區"] = df["完整行政區"].replace({"宜蘭縣": "宜蘭市"}, regex=True)
    df = df.replace({"臺": "台"}, regex=True)

    df.loc[df["完整行政區"] == "新竹縣_峨嵋鄉", ["鄉鎮市區", "完整行政區"]] = ["峨眉鄉", "新竹縣_峨眉鄉"]
    df.loc[df["完整行政區"] == "新竹縣_尖石鄉", ["鄉鎮市區", "完整行政區"]] = ["橫山鄉", "新竹縣_橫山鄉"]
    df.loc[df["完整行政區"] == "澎湖縣_望安鄉", ["鄉鎮市區", "完整行政區"]] = ["馬公市", "澎湖縣_馬公市"]
    df.loc[df["完整行政區"] == "金門縣_烏坵鄉", ["鄉鎮市區", "完整行政區"]] = ["金城鎮", "金門縣_金城鎮"]
    df.loc[df["完整行政區"] == "高雄市_田寮區", ["鄉鎮市區", "完整行政區"]] = ["岡山區", "高雄市_岡山區"]
    df.loc[df["完整行政區"] == "台中市_和平區", ["鄉鎮市區", "完整行政區"]] = ["東勢區", "台中市_東勢區"]
    df.loc[df["縣市"] == "新竹市", ["鄉鎮市區", "完整行政區"]] = ["新竹市", "新竹市_新竹市"]
    df.loc[df["縣市"] == "嘉義市", ["鄉鎮市區", "完整行政區"]] = ["嘉義市", "嘉義市_嘉義市"]

    return df


def build_predict_dataframe(form_data):
    now = datetime.now()
    year = now.year
    month = now.month

    city = form_data["city"]
    district = form_data["district"]
    address = form_data["address"]

    building_type = form_data.get("building_type") or "住宅大樓(11層含以上有電梯)"
    area = float(form_data.get("area") or 35)
    age = float(form_data.get("age") or 25)

    main_area = form_data.get("main_building_ping")
    if main_area:
        main_area = float(main_area)
    else:
        main_area = area * BUILDING_MAIN_RATIO.get(building_type, 0.62)
    t0 = time.time()
    clean_info = build_clean_address(address, city, district)
    print("clean:", round(time.time() - t0, 4))

    # =========================
    # Geocode cache
    # =========================
    t1 = time.time()

    geo_key_raw = json.dumps(
        {
            "city": city,
            "district": district,
            "clean_info": clean_info,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    geo_cache_key = "geo:" + hashlib.md5(
        geo_key_raw.encode("utf-8")
    ).hexdigest()

    geo_info = cache.get(geo_cache_key)

    if geo_info is None:
        geo_hit = False

        geo_info = geocode_address(
            city,
            district,
            clean_info,
        )

        cache.set(
            geo_cache_key,
            geo_info,
            60 * 60 * 24 * 30,
        )
    else:
        geo_hit = True

    print(
        "geocode:",
        round(time.time() - t1, 4),
        "hit=",
        geo_hit,
    )

    # =========================
    # POI cache
    # =========================
    if geo_info["geocode_success"]:
        t2 = time.time()

        poi_key_raw = json.dumps(
            {
                "lat": round(float(geo_info["lat"]), 6),
                "lon": round(float(geo_info["lon"]), 6),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        poi_cache_key = "poi:" + hashlib.md5(
            poi_key_raw.encode("utf-8")
        ).hexdigest()

        poi_features = cache.get(poi_cache_key)

        if poi_features is None:
            poi_hit = False

            poi_features = GEO_SERVICE.build_features(
                geo_info["lat"],
                geo_info["lon"],
            )

            cache.set(
                poi_cache_key,
                poi_features,
                60 * 60 * 24 * 30,
            )
        else:
            poi_hit = True

        print(
            "poi:",
            round(time.time() - t2, 4),
            "hit=",
            poi_hit,
        )

    else:
        poi_features = {
            "poi_convenience_count_300m": 0,
            "poi_convenience_count_500m": 0,
            "poi_bank_count_500m": 0,
            "poi_food_count_300m": 0,
            "poi_food_count_500m": 0,
            "poi_medical_count_500m": 0,
            "poi_parking_count_500m": 0,
            "distance_to_nearest_worship_m": 99999,
            "distance_to_thsr_m": 99999,
            "distance_to_tra_m": 99999,
            "distance_to_mrt_m": 5000,
        }

        print("poi: skipped geocode failed")
    unique_geo = extract_unique_geo(address, city, district)
    project_name = "一般成屋"    
    row = {
        "縣市": city,
        "鄉鎮市區": district,
        "土地位置建物門牌": address,
        "建案名稱": project_name,
        "唯一地理位置": unique_geo,         
        "交易距今月數": (year - 2011) * 12 + month,
        "成交年": float(year),
        "成交月": float(month),
        "完整行政區": f"{city}_{district}",
        "屋齡": age,
        "建物型態": building_type,
        "坪數": area,
        "移轉層次": float(form_data.get("transfer_floor") or 1),
        "總樓層數": float(form_data.get("total_floors") or 3),
        "電梯": int(form_data.get("elevator", 1)),
        "is_presale": int(form_data.get("is_presale", 0)),
        "age_was_missing": int(form_data.get("age_was_missing", 0)),
        "主建物坪數": main_area,
        "time_index": float(year * 12 + month),
        "緯度": float(geo_info["lat"]) if geo_info["lat"] is not None else 0.0,
        "經度": float(geo_info["lon"]) if geo_info["lon"] is not None else 0.0,
       
        **poi_features,
    }

    # row["area_last_month_price"] = get_area_price_feature(row)
    # row["總_編碼"] = get_prediction_encoded_values(row)
    # row["坪數_屋齡_交互"] = row["坪數"] * row["屋齡"]

    df = pd.DataFrame([row])
    df = normalize_region(df)

    # =========================
    # area_last_month_price cache
    # =========================
    t3 = time.time()

    area_cache_key = f"area_price:{city}:{district}:{year}:{month}"

    area_price = cache.get(area_cache_key)

    if area_price is None:
        area_hit = False

        area_price_series = get_area_price_feature(
            df,
            verbose=False
        )

        area_price = float(area_price_series.iloc[0])

        cache.set(
            area_cache_key,
            area_price,
            60 * 60 * 24
        )
    else:
        area_hit = True

    df["area_last_month_price"] = area_price

    print(
        "area_price:",
        round(time.time() - t3, 4),
        "hit=",
        area_hit,
    )

    # =========================
    # 總_編碼 cache
    # =========================
    t4 = time.time()

    encode_key = (
        f"encode:{city}:{district}:{building_type}:"
        f"{unique_geo}:{project_name}:{int(row['is_presale'])}"
    )

    encode_value = cache.get(encode_key)

    if encode_value is None:
        encode_hit = False

        encode_series = get_prediction_encoded_values(df)

        encode_value = float(encode_series.iloc[0])

        cache.set(
            encode_key,
            encode_value,
            60 * 60 * 24
        )
    else:
        encode_hit = True

    df["總_編碼"] = encode_value

    print(
        "encode:",
        round(time.time() - t4, 4),
        "hit=",
        encode_hit,
    )

    df["坪數_屋齡_交互"] = df["坪數"] * df["屋齡"]
    
    area_price_match_level = get_area_price_match_level(df)
    
    numeric_columns = [
        "交易距今月數",
        "成交年",
        "成交月",
        "屋齡",
        "坪數",
        "移轉層次",
        "總樓層數",
        "電梯",
        "is_presale",
        "age_was_missing",
        "主建物坪數",
        "time_index",
        "area_last_month_price",
        "總_編碼",
        "坪數_屋齡_交互",
        "緯度",
        "經度",
        "poi_convenience_count_300m",
        "poi_convenience_count_500m",
        "poi_bank_count_500m",
        "poi_food_count_300m",
        "poi_food_count_500m",
        "poi_medical_count_500m",
        "poi_parking_count_500m",
        "distance_to_nearest_worship_m",
        "distance_to_thsr_m",
        "distance_to_tra_m",
        "distance_to_mrt_m",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)

    

    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")

    return (
        df[MODEL_COLUMNS],
        clean_info,
        geo_info,
        poi_features,
        area_price_match_level,
    )
