# import geopandas as gpd
# gdf_points = gpd.read_file('taiwan-260512-free.shp.zip/gis_osm_places_free_1.shp')
# print(gdf_points.head())

# gdf_points['lon'] = gdf_points.geometry.x
# gdf_points['lat'] = gdf_points.geometry.y

# # 4. 轉成 pandas 方便你 90 萬筆比對
# osm_df = gdf_points[['name', 'fclass', 'lon', 'lat']].copy()
#####################
# import pandas as pd
# file_path = "臺北市門牌位置數值資料2_20260504.CSV"
# df_address = pd.read_csv(file_path)

# from pyproj import Transformer
# # 定義轉換器：從 TWD97 (EPSG:3826) 轉到 WGS84 (EPSG:4326)
# transformer = Transformer.from_crs("epsg:3826", "epsg:4326", always_xy=True)
# lons, lats = transformer.transform(df_address['橫座標'].values, df_address['縱座標'].values)
# # 套用轉換
# df_address['lon'] = lons
# df_address['lat'] = lats
####################
import pdfplumber
import pandas as pd
pdf_path = "2022-08-03_62e9f224e4e68_縣市代碼_20220703184855.pdf"
all_data = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        # 提取頁面中的表格
        table = page.extract_table()
        if table:
            # 轉換為 DataFrame (假設第一列是標題)
            df_page = pd.DataFrame(table[1:], columns=table[0])
            all_data.append(df_page)

# 合併所有頁面的資料
df_codes = pd.concat(all_data, ignore_index=True)
# 清理資料：移除換行符號或空白
df_codes = df_codes.map(lambda x: str(x).replace('\n', '').strip() if x else x)
# 預覽結果
print(df_codes.head())


# 確保代碼是字串型態，避免前導零消失
df_codes['縣市代碼'] = df_codes['縣市代碼'].astype(str)
df_codes['鄉鎮區代碼'] = df_codes['鄉鎮區代碼'].astype(str)
# 1. 製作縣市對照字典 (Key: 65000 -> Value: 新北市)
# 我們先去重，因為縣市代碼會重複出現
city_map = dict(zip(df_codes['縣市代碼'], df_codes['縣市名稱']))
# 2. 製作鄉鎮區對照字典 (Key: 65000010 -> Value: 板橋區)
dist_map = dict(zip(df_codes['鄉鎮區代碼'], df_codes['鄉鎮區名稱']))
# 3. 如果需要「完整行政區」字典 (Key: 65000010 -> Value: 新北市板橋區)
df_codes['完整行政區'] = df_codes['縣市名稱'] + df_codes['鄉鎮區名稱']
full_dist_map = dict(zip(df_codes['鄉鎮區代碼'], df_codes['完整行政區']))

import pickle
encoding_assets = {
    'city_map': city_map,
    'dist_map': dist_map,
    'full_dist_map': full_dist_map
}