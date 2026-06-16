import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from tqdm import tqdm
import numpy as np
import time
import random

code_df=pd.read_csv("段名代碼表.csv")
code_df["縣市名稱"] = code_df["縣市名稱"].str.replace("臺", "台")
code_df["鄉鎮名稱"] = code_df["鄉鎮名稱"].str.replace("臺", "台")
code_df["段"] = code_df["段"].str.replace("臺", "台")
code_df["小段"] = code_df["小段"].str.replace("臺", "台")
# 使用 Regex 抓取純英文字母部分 (例如 AD01 -> AD)
code_df["office"] = code_df["所區碼"].str.extract(r"([A-Za-z]+)")
# 1-3. 將「代碼」欄位重新命名為 sect
code_df = code_df.rename(columns={"代碼": "sect"})
code_df["小段"] = code_df["小段"].fillna(np.nan)

data = {
    "地號": ["769"],
    "縣市": ["台北市"],
    "鄉鎮市區": ["大同區"],
    "段": ["市府"],
    "小段": ["二"],
}
df = pd.DataFrame(data)
df_no_subsect = df[df["小段"].isna()].copy()
df_has_subsect = df[df["小段"].notna()].copy()
res_no_subsect = pd.merge(
    df_no_subsect,
    code_df[["縣市名稱", "鄉鎮名稱", "段", "office", "sect"]].drop_duplicates(subset=["縣市名稱", "鄉鎮名稱", "段"]),
    left_on=["縣市", "鄉鎮市區", "段"],
    right_on=["縣市名稱", "鄉鎮名稱", "段"],
    how="left"
)
res_has_subsect = pd.merge(
    df_has_subsect,
    code_df[["縣市名稱", "鄉鎮名稱", "小段", "段", "office", "sect"]],
    left_on=["縣市", "鄉鎮市區", "小段", "段"],
    right_on=["縣市名稱", "鄉鎮名稱", "小段", "段"],
    how="left"
)
final_df = pd.concat([res_no_subsect, res_has_subsect], ignore_index=True)
final_df = final_df.drop(columns=["縣市名稱", "鄉鎮名稱","小段", "段"])
def format_land_no(land_no_str):
    """自動將地號轉換成官方 8 碼格式"""
    if pd.isna(land_no_str):
        return None
    land_no_str = str(land_no_str).strip()
    # 處理含有 '-' 或 '、' 或 '等' 的狀況，只抓取第一筆主子地號
    # 範例："570-118" -> main=570, sub=118; "282地號" -> main=282, sub=0
    match = re.search(r"(\d+)(?:[-](\d+))?", land_no_str)
    if match:
        main_no = match.group(1)
        sub_no = match.group(2) if match.group(2) else "0"
        return f"{int(main_no):04d}{int(sub_no):04d}"
    return None
# =========================================================
# 🧠 Session（重用連線，避免每次新 TCP）
session = requests.Session()
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0",
]
session.headers.update({
    "User-Agent": random.choice(USER_AGENTS),
    "Referer": "https://maps.nlsc.gov.tw/",
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
})
# =========================================================
# 🧠 全域 cache（超重要）
cache = {}

# =========================================================
# 🧠 單筆查詢（防封版）
def fetch_single_coordinate(index, office, sect, landno, retry=3):
    """
    負責單一執行緒執行的任務。
    為了多執行緒結束後能對回 DataFrame 的正確位置，回傳時必須夾帶該列的 index。
    """
    if pd.isna(office) or pd.isna(sect) or pd.isna(landno):
        return index, None, None

    # 🧠 cache 命中
    cache_key = (office, sect, landno)
    if cache_key in cache:
        lat, lon = cache[cache_key]
        return index, lat, lon

    # 🧠 request jitter（超重要）
    time.sleep(random.uniform(2, 6))
    url = "https://landmaps.nlsc.gov.tw/S_Maps/qryTileMapIndex"
    params = {
        "type": 2,
        "flag": 2,
        "office": str(office),
        "sect": str(int(float(sect))).zfill(4),
        #"sect": str(sect),
        #"landno": str(int(float(landno))).zfill(8),
        "landno": str(landno),
        #"alpah": "0.5f",
        # 🚨 callback 不要固定
        "callback": f"_jqjsp{random.randint(1000,999999)}",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://maps.nlsc.gov.tw/",
        "Accept": "*/*",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    print("index**", index, "office**", params["office"], "sect**", params["sect"], "landno**", params["landno"])
    try:
        print("index", index, "office", params["office"], "sect", params["sect"], "landno", params["landno"])
        # 使用 Session 或縮短 timeout 避免遇到慢速連線卡死
        r = session.get(url,params=params,timeout=30,)
        print("status_code", r.status_code)
        #print(r.url)
        #print("index", index, "office/n", params["office"], "sect/n", params["sect"], "landno/n", params["landno"], "status_code", r.status_code)

        # 🚨 被限流
        if r.status_code == 429:
            if retry <= 0:
                return index, "429封鎖", "429封鎖"
            wait_time = random.uniform(30, 90)
            print(f"🚨 429 被限流，等待 {wait_time:.1f} 秒")
            time.sleep(wait_time)
            return fetch_single_coordinate(
                index,
                office,
                sect,
                landno,
                retry=retry-1
            )

        # 🧠 解析 JSONP
        #m = re.search(r'_jqjsp\((.*)\)', r.text)
        #m = re.search(r'_jqjsp\d+\((.*)\)', r.text)
        m = re.search(r'\((.*)\)', r.text)
        #print(f"{r.text[:100]}...")
        if not m:
            print(f"⚠️ 無法解析回傳內容: {r.text[:100]}...")
            return index, "解析失敗", "解析失敗"
        data = json.loads(m.group(1))
        if not data or not data[0]:
            print(f"⚠️ 查無資料: {params}")
            return index, "查無資料", "查無資料"
        item = data[0][0]
        #print(json.dumps(item, ensure_ascii=False, indent=2))
        if item.get("cy") is None or item.get("cx") is None:
            print(f"⚠️ 經緯度資料不完整: {item}")
            return index, "無經緯度", "無經緯度"
        # =================================================
        # 🧠 寫入 cache
        # =================================================
        cache[cache_key] = (item.get("cy"), item.get("cx"))
        print(f"✅ 成功獲得經緯度: {cache[cache_key]} for landno={landno}")
        return index, item.get("cy"), item.get("cx")
    except Exception as e:
        # 多執行緒大量發送時，如果少數幾筆被斷線，捕捉錯誤並返回 None，確保大部隊不卡住
        if retry <= 0:
            return index, f"錯誤:{str(e)[:20]}", f"錯誤:{str(e)[:20]}"
        wait_time = random.uniform(10, 30)
        print(f"⚠️ Exception retry {wait_time:.1f}s")
        time.sleep(wait_time)
        return fetch_single_coordinate(
            index,
            office,
            sect,
            landno,
            retry=retry-1
        )
def process_dataframe_multithreaded(target_df, workers=2):
    """
    將 DataFrame 轉換為執行緒任務，高速執行並直接回填「緯度」、「經度」欄位
    """
    print(f"🚀 開始啟動多執行緒查詢... 併發數: {workers}")
    # 先初始化 DataFrame 的新欄位為空值 (預防萬一)
    #target_df["緯度"] = None
    #target_df["經度"] = None
    # 用 dict 暫存多執行緒跑完的結果 {index: (lat, lon)}
    results_dict = {}
    # 使用 ThreadPoolExecutor 控制多執行緒大部隊
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # 建立所有人的代辦任務
        futures = []
        for row in target_df.itertuples(index=True):
            futures.append(
                executor.submit(
                    fetch_single_coordinate,
                    index=row.Index,
                    office=row.office,
                    sect=row.sect,
                    landno=row.landno,
                )
            )
        # tqdm 會在螢幕上渲染進度條，大量洗幾十萬筆資料時非常實用
        for future in tqdm(as_completed(futures), total=len(futures)):
            idx, lat, lon = future.result()
            results_dict[idx] = (lat, lon)
    # 🌟 100% 安全對齊回填：依據原本 DataFrame 的 index，把結果精準對齊塞回
    print("💾 正在將經緯度經緯度快速寫回 DataFrame 欄位中...")
    target_df["緯度"] = [results_dict.get(i, (None, None))[0] for i in target_df.index]
    target_df["經度"] = [results_dict.get(i, (None, None))[1] for i in target_df.index]

    print("🎉 多執行緒抓取與回填全部完成！")
    return target_df

#final_df = pd.read_pickle("f_test_12_1.pkl")
#final_df = pd.read_pickle("f_test_12_1.pkl")
#final_df = pd.read_pickle("f_test_預售_5.pkl")
final_df = pd.read_pickle("f_test_補_t1.pkl")

final_df["office"] = final_df["所區碼_精簡"]
final_df["sect"] = final_df["代碼"]
#final_df["landno"] = final_df["地號8碼"]
final_df["landno"] = '00010000'
#final_df["landno"] = final_df["地號"].fillna("1").apply(format_land_no)
#final_df = process_dataframe_multithreaded(final_df, workers=2)

#print(final_df[["地號", "緯度", "經度"]])

# final_df = pd.read_csv("ddf_test.csv")
# final_df["office"] = final_df["所區碼_精簡"]
# final_df["sect"] = final_df["代碼"]
#final_df["landno"] = final_df["地號"].apply(format_land_no).fillna("00010000")

condition = (final_df["緯度"].isna()| (final_df["緯度"] == "none")| (final_df["緯度"] == "解析失敗")| (final_df["緯度"] == "查無資料") | (final_df["緯度"] == "無經緯度"))
# 2. 切出子集送進多執行緒（因為移除了清空語法，現在 fetch_single_coordinate 依舊能看到原本的錯誤狀態）
processed_subset = process_dataframe_multithreaded(final_df[condition].copy(), workers=2)
target_columns = ["緯度", "經度"]
# 4. 用計算完的新經緯度，精準覆蓋回原本那幾列的位置，其餘正常資料完全不動
print("\n==== 🎯 寫入完成後的完整 DataFrame 範例 ====")
# final_df.loc[condition, target_columns] = processed_subset[target_columns].values
final_df.loc[processed_subset.index,target_columns] = processed_subset[target_columns]

#final_df.to_pickle("f_test_13_1.pkl")
#final_df.to_pickle("f_test_預售_6.pkl")
#final_df.to_pickle("f_test_補_t2.pkl")

