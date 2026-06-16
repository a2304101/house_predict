import pandas as pd
import asyncio
import aiohttp
from tqdm import tqdm

# 設定
#CSV_FILE = '經緯度_全_無地號小段_t7.pkl' # 你的原始檔
#CSV_FILE = 'processed_results3_後_無地號小段.csv'
#CSV_FILE = '未補全_不含地號小段_t1.csv'
CSV_FILE = '591_housing_data_nopre2_t1.csv'
#OUTPUT_FILE = '經緯度_全_無地號小段_t8.csv'  # 結果檔
#OUTPUT_FILE = 'processed_results3_後_無地號小段_t1.csv'  
#OUTPUT_FILE = '未補全_不含地號小段_t2.csv'  
OUTPUT_FILE = '591_housing_data_nopre2_t2.csv'
#OUTPUT_FILE2 = '經緯度_全_無地號小段_t8.pkl'
#OUTPUT_FILE2 = 'processed_results3_後_無地號小段_t1.pkl'  
#OUTPUT_FILE2 = '未補全_不含地號小段_t2.pkl'  
OUTPUT_FILE2 = '591_housing_data_nopre2_t2.pkl' 
API_URL = "http://localhost:8080/search.php"
CONCURRENT_LIMIT = 60       # 16GB RAM + 本地 SSD 建議設 50-80

def match_text(display_name, target_city):
    """
    檢查 API 回傳的 display_name 裡面是否包含指定的縣市
    相容 '台' 與 '臺' 的互換
    """
    if not display_name or pd.isna(target_city) or not target_city:
        return False
    norm_display = str(display_name).replace('臺', '台')
    norm_target = str(target_city).replace('臺', '台')
    return norm_target in norm_display

async def query_api(session, address , target_city, target_district):
    """單純呼叫 API 的輔助函數"""
    if pd.isna(address) or not str(address).strip() or str(address) == 'None' or str(address).endswith('None'):
        return None, None
    
    params = {
        'q': str(address).strip(),
        'format': 'json',
        'limit': 10,                # 🎯 拿回最多 10 筆結果來供篩選
        'addressdetails': 1,
        'accept-language': 'zh-TW'
    }
    try:
        async with session.get(API_URL, params=params, timeout=3) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    # 🌟 階段一：精確比對【縣市 + 鄉鎮市區】都要符合
                    for item in data:
                        disp = item.get('display_name', '')
                        if match_text(disp, target_city) and match_text(disp, target_district):
                            return item['lat'], item['lon']
                    
                    # 🌟 階段二：降級比對，只要【縣市】符合就好
                    for item in data:
                        disp = item.get('display_name', '')
                        if match_text(disp, target_city):
                            return item['lat'], item['lon']
                    
                    
                    return None, None
    except:
        pass
    return None, None

async def fetch_lat_lon(session, semaphore, addr_1, addr_2, addr_3, addr_4, addr_5 , addr_6, addr_7, addr_8, addr_9, addr_10 , addr_11, addr_12 , target_city , target_district):
    """四級降級查詢核心函數"""
    async with semaphore:
        # 第一級：乾淨地理位置_full (標記 1)
        lat, lon = await query_api(session, addr_1 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 1
        # 第二級：只有乾淨地理位置 (標記 2)
        lat, lon = await query_api(session, addr_2 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 2
        # 第三級：乾淨地址_full (標記 3)
        lat, lon = await query_api(session, addr_3 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 3
        # 第四級：只有乾淨地址 (標記 4)
        lat, lon = await query_api(session, addr_4 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 4 
        # 第五級：去號_full (標記 5)
        lat, lon = await query_api(session, addr_5 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 5    
        # 第六級：只有去號 (標記 6)
        lat, lon = await query_api(session, addr_6 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 6 
        # 第七級： 去弄_full(標記 7)
        lat, lon = await query_api(session, addr_7 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 7
        # 第八級： 只有去弄(標記 8)
        lat, lon = await query_api(session, addr_8 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 8
        # 第九級： 去巷_full(標記 9)
        lat, lon = await query_api(session, addr_9 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 9
        # 第十分： 只有去巷(標記 10)
        lat, lon = await query_api(session, addr_10 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 10
        # 第十一级：最後地址_full (標記 11)
        lat, lon = await query_api(session, addr_11 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 11
        # 第十二级：只有最後地址 (標記 12)
        lat, lon = await query_api(session, addr_12 , target_city, target_district)
        if lat and lon:
            return addr_1, float(lat), float(lon), 12
        
        # 通通沒搜到
        return addr_1, None, None, None

async def main():
    # 1. 讀取資料
    print("正在讀取 CSV 檔案...")
    df = pd.read_csv(CSV_FILE)
    df['最後地址']=None ; df['用哪個地址']=None
    #df = df[~df['土地位置建物門牌'].str.contains('地號|小段')]
    df['縣市'] = df['縣市'].replace('宜蘭市','宜蘭縣')
    #(df['用哪個地址']>=9) (df['緯度'].isna())
    condition =  (~df['土地位置建物門牌'].astype(str).str.contains("地號|小段",na=False))  #& (df['乾淨地理位置'].fillna('').str.strip().ne('')) 
    target_df = df.loc[condition].copy()
    # 2. 【動態讀取並拼接】直接建立一個乾淨的臨時 DataFrame 來提取唯一地址
    print("正在動態生成不重複的查詢地址組合...")
    temp_unique_df = pd.DataFrame({
        '乾淨地理位置_full': target_df['縣市'] + target_df['鄉鎮市區'] + target_df['乾淨地理位置'].fillna('').astype(str),
        '只有乾淨地理位置': target_df['乾淨地理位置'].fillna('').astype(str),
        '乾淨地址_full': target_df['縣市'] + target_df['鄉鎮市區'] + target_df['乾淨地址'].fillna('').astype(str),
        '只有乾淨地址': target_df['乾淨地址'].fillna('').astype(str),
        '去號_full': target_df['縣市'] + target_df['鄉鎮市區'] + target_df['去號'].fillna('').astype(str),
        '只有去號': target_df['去號'].fillna('').astype(str),
        '去弄_full': target_df['縣市'] + target_df['鄉鎮市區'] + target_df['去弄'].fillna('').astype(str),
        '只有去弄': target_df['去弄'].fillna('').astype(str),
        '去巷_full': target_df['縣市'] + target_df['鄉鎮市區'] + target_df['去巷'].fillna('').astype(str),
        '只有去巷' : target_df['去巷'].fillna('').astype(str), 
        '最後地址_full' : target_df['縣市'] + target_df['鄉鎮市區'] + target_df['最後地址'].fillna('').astype(str),
        '只有最後地址': target_df['最後地址'].fillna('').astype(str),
        '原始縣市': target_df['縣市'], # 🎯 把縣市留著，等一下過濾要用
        '鄉鎮市區': target_df['鄉鎮市區']
    }).drop_duplicates(subset=['乾淨地理位置_full'])
    
    print(f"原始資料: {len(target_df)} 筆, 唯一地址 (需查詢次數): {len(temp_unique_df)} 筆")
    
    results_map = {} # 用來存放對應結果的字典
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    
    # 3. 開始非同步查詢temp_unique_df
    async with aiohttp.ClientSession() as session:
        records = temp_unique_df.to_dict('records')
        tasks = [
            fetch_lat_lon(session, semaphore, row['乾淨地理位置_full'], row['只有乾淨地理位置'], row['乾淨地址_full'], row['只有乾淨地址'], row['去號_full'], row['只有去號'], row['去弄_full'], row['只有去弄'], row['去巷_full'], row['只有去巷'], row['最後地址_full'], row['只有最後地址'] , row['原始縣市'], row['鄉鎮市區']) 
            for row in records
        ]
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="地理編碼降級查詢中"):
            key_addr, lat, lon, use_type = await f
            results_map[key_addr] = (lat, lon, use_type)

    # 4. 將結果對應回原始 90 萬筆的 DataFrame
    print("正在將結果精準對應回原始資料...")
    # 對應時，原始 df 同樣要在內存中動態合成 key 來與 results_map 對接
    df_lookup_key = target_df['縣市'] + target_df['鄉鎮市區'] + target_df['乾淨地理位置'].fillna('').astype(str)
    df.loc[condition, '緯度'] = df_lookup_key.map(lambda x: results_map.get(x, (None, None, None))[0]).values
    df.loc[condition, '經度'] = df_lookup_key.map(lambda x: results_map.get(x, (None, None, None))[1]).values
    df.loc[condition, '用哪個地址'] = df_lookup_key.map(lambda x: results_map.get(x, (None, None, None))[2]).values

    # 5. 儲存
    df['縣市'] = df['縣市'].replace('宜蘭縣','宜蘭市')
    print(f"正在將結果寫入 {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    df.to_pickle(OUTPUT_FILE2)
    print("全部完成！原始欄位完好如初，經緯度已順利補上。")

    return df, df_lookup_key, results_map
if __name__ == "__main__":
    #asyncio.run(main())
    df, df_lookup_key, results_map = asyncio.run(main())
    #df['乾淨地理位置'].isna().sum() df['緯度'].isna().sum() (df['緯度'].isna())  