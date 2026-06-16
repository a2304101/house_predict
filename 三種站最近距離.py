import numpy as np
import pandas as pd
from scipy.spatial import KDTree
import time

def calculate_station_distances(house_pickle_path, station_pickle_path, output_csv_path, output_pickle_path):
    print("⏳ 正在載入資料中...")
    start_time = time.time()
    
    house_df = pd.read_pickle(house_pickle_path)
    station_df = pd.read_pickle(station_pickle_path)
    house_df.loc[house_df['土地位置建物門牌']=='雲林縣斗六市榴八街156號', ['緯度', '經度']] = [23.72911, 120.57947]
    house_coords = house_df[['緯度', '經度']].to_numpy()
    DEGREE_TO_METER = 110000  # 經緯度轉公尺
    
    print("🌲 正在為高鐵、台鐵、捷運各別建立 KDTree...")
    
    # 1. 高鐵 (THSR) 最近距離
    thsr_df = station_df[station_df['station_type'] == 'THSR_station']
    if not thsr_df.empty:
        thsr_tree = KDTree(thsr_df[['lat', 'lon']].to_numpy())
        dist, _ = thsr_tree.query(house_coords, k=1)
        house_df['distance_to_thsr_m'] = np.round(dist * DEGREE_TO_METER).astype(int)
    else:
        house_df['distance_to_thsr_m'] = 99999

    # 2. 火車站 (TRA) 最近距離
    tra_df = station_df[station_df['station_type'] == 'TRA_station']
    if not tra_df.empty:
        tra_tree = KDTree(tra_df[['lat', 'lon']].to_numpy())
        dist, _ = tra_tree.query(house_coords, k=1)
        house_df['distance_to_tra_m'] = np.round(dist * DEGREE_TO_METER).astype(int)
    else:
        house_df['distance_to_tra_m'] = 99999

    # 3. 捷運站 (MRT) 最近距離
    mrt_df = station_df[station_df['station_type'] == 'MRT_station']
    if not mrt_df.empty:
        mrt_tree = KDTree(mrt_df[['lat', 'lon']].to_numpy())
        dist, _ = mrt_tree.query(house_coords, k=1)
        calculated_dist = np.round(dist * DEGREE_TO_METER).astype(int)
        house_df['distance_to_mrt_m'] = np.minimum(calculated_dist, 5000)
    else:
        house_df['distance_to_mrt_m'] = 5000

    print(f"💾 正在儲存附加交通特徵後的房價資料至 {output_csv_path}...")
    house_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
    house_df.to_pickle(output_pickle)
    
    end_time = time.time()
    print(f"✅ 90 萬筆交通距離特徵計算完成！總耗時: {round(end_time - start_time, 2)} 秒")

if __name__ == "__main__":
    # 修改為你實際的 90 萬筆房價檔名 (可以是之前跑完商店特徵的那個檔案，直接疊加進去)
    house_pickle = "地號_無地號_t1_features.pkl" 
    station_pickle = "taiwan_stations_t2.pkl"
    output_csv = "地號_無地號_t2_features.csv"
    output_pickle = "地號_無地號_t2_features.pkl"
    calculate_station_distances(house_pickle, station_pickle, output_csv, output_pickle)