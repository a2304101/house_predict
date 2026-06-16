import pickle
import pandas as pd
from pyproj import Transformer
# with open('mapping_assets.pkl', 'rb') as f:
#     assets = pickle.load(f)
# # 取出字典
# city_map = assets['city_map']
# dist_map = assets['dist_map']
# full_dist_map = assets['full_dist_map']

# df_main=pd.read_csv("臺北市門牌位置數值資料2_20260504.csv")

# df_main['縣市名稱'] = df_main['省市縣市代碼'].astype(str).map(city_map)
# df_main['鄉鎮區名稱'] = df_main['鄉鎮市區代碼'].astype(str).map(dist_map)
# df_main['完整行政區'] = df_main['鄉鎮市區代碼'].astype(str).map(full_dist_map)
# print(df_main['完整行政區'].isna().sum())
# #####################################################################
# # 定義轉換器：從 TWD97 (EPSG:3826) 轉到 WGS84 (EPSG:4326)
# transformer = Transformer.from_crs("epsg:3826", "epsg:4326", always_xy=True)
# lons, lats = transformer.transform(df_main['橫座標'].values, df_main['縱座標'].values)
# df_main['lon'] = lons;df_main['lat'] = lats
# #####################################################################
# df_main.to_csv("臺北市門牌位置數值資料_增加市區.csv", index=False, encoding='utf-8-sig')
#####################################################################
import pandas as pd
import re

# 測試資料
addresses = [
    "新生北路二段31之1號七樓之5",
    "重慶北路三段236巷5弄2號四樓之1",
    "大湖山莊街219巷34弄3之3號",
    "中山北路二段59巷18號二樓之1"
]
def parse_taiwan_address(addr):
    # 定義正規表示式
    # 這裡的邏輯是按順序抓取：路段 -> 巷 -> 弄 -> 號
    regex = r"(?P<road>.+?(?:路|街|大道)(?:\w+段)?)(?P<lane>\d+巷)?(?P<alley>\d+弄)?(?P<no>[0-9、之\-]+)號"
    match = re.search(regex, addr)
    if match:
        res = match.groupdict()
        # 去除結尾的單位字，讓資料更乾淨 (可選)
        return {
            '街路段': res['road'] or "",
            '巷': res['lane'] or "",
            '弄': res['alley'] or "",
            '號':'號': res['no'].replace('號', '') if res['no'] else ""
        }
    return {'街路段': "", '巷': "", '弄': "", '號': ""}
# df = pd.DataFrame({'土地位置建物門牌': addresses})
# df_parsed = df['土地位置建物門牌'].apply(lambda x: pd.Series(parse_taiwan_address(x)))