import os
import time
import googlemaps
import pandas as pd
from tqdm import tqdm  # 如果沒有請先 pip install tqdm
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# 1. 填入你的 Google Maps API Key
API_KEY = 'AIzaSyDrrl2sFppO8KpYpBnKZmK8lwkckSfyoTA'
gmaps = googlemaps.Client(key=API_KEY)

# 2. 讀取你的 CSV 檔案
csv_path = '經緯度_全_無地號小段_t8.csv'  
df = pd.read_csv(csv_path)


if 'use_google' not in df.columns: df['use_google'] = None

df['__temp_full_address__'] = (
    df['縣市'].fillna('').astype(str).str.strip() +
    df['鄉鎮市區'].fillna('').astype(str).str.strip() +
    df['土地位置建物門牌'].fillna('').astype(str).str.strip()
)
# 3. 嚴格篩選：只抓「用哪個地址==11」且「經度還是空的」
mask = (df['用哪個地址'] == 11) & (df['use_google']!=1)
unique_addresses = list(df[mask]['__temp_full_address__'].unique())

total_unique = len(unique_addresses)
print(f"📊 原始待處理資料：{len(df[mask])} 筆")
print(f"🎯 經過【去重優化】後，實際只需查詢：{total_unique} 筆不重複地址！")

results_map = {}
map_lock = Lock()
save_counter = 0

# 3. 定義單一不重複地址的查詢任務
def process_unique_address(address):
    global save_counter
    
    try:
        geocode_result = gmaps.geocode(address, language='zh-TW')
        
        with map_lock:
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                results_map[address] = {
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'status': 1
                }
            else:
                # Google 查不到此地址
                results_map[address] = {'lat': None, 'lng': None, 'status': -1}
                
    except Exception as e:
        error_msg = str(e)
        if "OVER_QUERY_LIMIT" in error_msg or "429" in error_msg:
            time.sleep(5)
        else:
            time.sleep(0.5)
        return

    # 定時安全回填與存檔（每查完 500 個不重複地址，就批量寫回硬碟一次）
    with map_lock:
        save_counter += 1
        if save_counter % 1000 == 0:
            intermediate_map_and_save()

# 4. 輔助函式：將目前的 map 結果批量寫回 df 並存檔
def intermediate_map_and_save():
    # 這裡必須在上鎖的狀態下執行，或者確保安全
    # 利用 pandas 的 map 功能，極速將字典資料對照回填
    for addr, info in list(results_map.items()):
        # 找出原本 df 中，所有符合這個地址且尚未被設定為 1 的索引
        sub_mask = (df['__temp_full_address__'] == addr) & (df['use_google'] != 1)
        if sub_mask.any():
            df.loc[sub_mask, '緯度'] = info['lat']
            df.loc[sub_mask, '經度'] = info['lng']
            df.loc[sub_mask, 'use_google'] = info['status']
            
    # 清除暫時的完整地址欄位後存檔，存完再補回來
    clean_df = df.drop(columns=['__temp_full_address__'])
    clean_df.to_csv('temp_csv_backup.csv', index=False)
    os.replace('temp_csv_backup.csv', csv_path)

# ========================================================
# 核心步驟 C：啟動多執行緒平行查詢
# ========================================================
MAX_WORKERS = 25

if total_unique > 0:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(tqdm(executor.map(process_unique_address, unique_addresses), total=total_unique, desc="去重極速查詢中"))

    # 5. 所有不重複地址查詢完畢，進行最終的批量對照回填與存檔
    print("\n🔄 正在將查詢結果批量回填至原始 3 萬筆資料中...")
    intermediate_map_and_save()
else:
    print("\n確認過眼神，沒有需要查詢的地址！")

# 清除暫時建立的欄位
if '__temp_full_address__' in df.columns:
    df = df.drop(columns=['__temp_full_address__'])

print("🎉 終極優化完成！重複地址已自動同步，且資料已安全存檔！")
