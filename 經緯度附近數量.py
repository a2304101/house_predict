import numpy as np
import pandas as pd
from scipy.spatial import KDTree
import time

def build_features_with_kdtree(house_pickle_path, poi_csv_path, station_pickle_path, output_csv_path, output_pickle_path):
    print("⏳ 正在載入 90 萬筆房價資料與剛剛生成的 POI 資料...")
    start_time = time.time()
    
    # 載入資料
    house_df = pd.read_pickle(house_pickle_path)
    house_df['distance_to_mrt_m']=None
    poi_df = pd.read_csv(poi_csv_path)
    #house_df = house_df[house_df['土地位置建物門牌']=='雲林縣斗六市榴八街156號'].copy()
    # --- 經緯度與公尺轉換基準 ---
    # 在台灣緯度下，經緯度 1 度大約是 110000 公尺 (110公里)
    # 500 公尺 大約等於 0.0045 度
    RADIUS_500M = 0.0045  # 500公尺
    RADIUS_300M = 0.0027  # 300公尺
    
    print("🌲 開始為不同類別的設施建立空間索引 (KDTree)...")
    
    # 1. 提取四大超商/便利商店 (台灣最強機能指標)
    conv_df = poi_df[poi_df['poi_type'] == 'shop_convenience']
    conv_tree = KDTree(conv_df[['lat', 'lon']].to_numpy()) if not conv_df.empty else None
    print(f"   -> 已建立超商索引，共 {len(conv_df)} 筆點位")
    
    # 2. 提取金融機構 (銀行)
    bank_df = poi_df[poi_df['poi_type'] == 'amenity_bank']
    bank_tree = KDTree(bank_df[['lat', 'lon']].to_numpy()) if not bank_df.empty else None
    print(f"   -> 已建立銀行索引，共 {len(bank_df)} 筆點位")
    
    # 3. 提取所有餐飲類 (包含餐廳、咖啡廳、速食、美食街)
    food_types = ['amenity_restaurant', 'amenity_cafe', 'amenity_fast_food', 'amenity_food_court']
    food_df = poi_df[poi_df['poi_type'].isin(food_types)]
    food_tree = KDTree(food_df[['lat', 'lon']].to_numpy()) if not food_df.empty else None
    print(f"   -> 已建立餐飲類索引，共 {len(food_df)} 筆點位")
    
    # 4. 提取醫療機構 (大樹藥局這種藥局、診所、醫院)
    medical_types = ['amenity_clinic', 'amenity_hospital', 'amenity_pharmacy']
    med_df = poi_df[poi_df['poi_type'].isin(medical_types)]
    med_tree = KDTree(med_df[['lat', 'lon']].to_numpy()) if not med_df.empty else None
    print(f"   -> 已建立醫療院所索引，共 {len(med_df)} 筆點位")

    # 5. 提取宮廟/宗教場所 (潛在嫌惡設施)
    worship_df = poi_df[poi_df['poi_type'] == 'amenity_place_of_worship']
    worship_tree = KDTree(worship_df[['lat', 'lon']].to_numpy()) if not worship_df.empty else None
    print(f"   -> 已建立宮廟索引，共 {len(worship_df)} 筆點位")

    # 6. 提取停車場 (開車族剛需，從你撈出的範例中可以看到很多 amenity_parking)
    parking_df = poi_df[poi_df['poi_type'] == 'amenity_parking']
    parking_tree = KDTree(parking_df[['lat', 'lon']].to_numpy()) if not parking_df.empty else None
    print(f"   -> 已建立停車場索引，共 {len(parking_df)} 筆點位")
    need_calc_mask = house_df['distance_to_mrt_m'].isna() 
    # 準備房屋的經緯度陣列 (90萬筆)
    #house_coords = house_df[['緯度', '經度']].to_numpy()
    house_coords = house_df.loc[need_calc_mask, ['緯度', '經度']].to_numpy()
    print("\n⚡ 正在以超高速計算 90 萬筆房屋的空間特徵 (預估 2-3 分鐘)...")
    
    # 算數量 (500m 內)
    if conv_tree:
        house_df.loc[need_calc_mask, 'poi_convenience_count_300m'] = [len(idx) for idx in conv_tree.query_ball_point(house_coords, r=RADIUS_300M)]
        house_df.loc[need_calc_mask, 'poi_convenience_count_500m'] = [len(idx) for idx in conv_tree.query_ball_point(house_coords, r=RADIUS_500M)]
    else:
        house_df.loc[need_calc_mask, 'poi_convenience_count_300m'] = 0
        house_df.loc[need_calc_mask, 'poi_convenience_count_500m'] = 0
        
    if bank_tree:
        house_df.loc[need_calc_mask, 'poi_bank_count_500m'] = [len(idx) for idx in bank_tree.query_ball_point(house_coords, r=RADIUS_500M)]
    else:
        house_df.loc[need_calc_mask, 'poi_bank_count_500m'] = 0
        
    if food_tree:
        house_df.loc[need_calc_mask, 'poi_food_count_300m'] = [len(idx) for idx in food_tree.query_ball_point(house_coords, r=RADIUS_300M)]
        house_df.loc[need_calc_mask, 'poi_food_count_500m'] = [len(idx) for idx in food_tree.query_ball_point(house_coords, r=RADIUS_500M)]
    else:
        house_df.loc[need_calc_mask, 'poi_food_count_300m'] = 0
        house_df.loc[need_calc_mask, 'poi_food_count_500m'] = 0

    if med_tree:
        house_df.loc[need_calc_mask, 'poi_medical_count_500m'] = [len(idx) for idx in med_tree.query_ball_point(house_coords, r=RADIUS_500M)]
    else:
        house_df.loc[need_calc_mask, 'poi_medical_count_500m'] = 0

    if parking_tree:
        house_df.loc[need_calc_mask, 'poi_parking_count_500m'] = [len(idx) for idx in parking_tree.query_ball_point(house_coords, r=RADIUS_500M)]
    else:
        house_df.loc[need_calc_mask, 'poi_parking_count_500m'] = 0

    # 算最近距離 (算與最近宮廟的距離，單位：公尺)
    if worship_tree:
        distances, _ = worship_tree.query(house_coords, k=1)
        house_df.loc[need_calc_mask, 'distance_to_nearest_worship_m'] = np.round(distances * 110000).astype(int)
    else:
        house_df.loc[need_calc_mask, 'distance_to_nearest_worship_m'] = 99999

    #print(f"\n💾 正在將產出的房價特徵新檔案儲存至 {output_csv_path}...")
    end_time = time.time()
    print(f"✅ 狂賀！90 萬筆資料的地理特徵全部計算完畢！總耗時: {round(end_time - start_time, 2)} 秒")
###########################
    print("⏳ 正在載入資料中...")
    
    
    station_df = pd.read_pickle(station_pickle_path)
    #house_df.loc[house_df['土地位置建物門牌']=='雲林縣斗六市榴八街156號', ['緯度', '經度']] = [23.72911, 120.57947]
    
    DEGREE_TO_METER = 110000  # 經緯度轉公尺
    
    print("🌲 正在為高鐵、台鐵、捷運各別建立 KDTree...")
    
    # 1. 高鐵 (THSR) 最近距離
    thsr_df = station_df[station_df['station_type'] == 'THSR_station']
    if not thsr_df.empty:
        thsr_tree = KDTree(thsr_df[['lat', 'lon']].to_numpy())
        dist, _ = thsr_tree.query(house_coords, k=1)
        house_df.loc[need_calc_mask, 'distance_to_thsr_m'] = np.round(dist * DEGREE_TO_METER).astype(int)
    else:
        house_df.loc[need_calc_mask, 'distance_to_thsr_m'] = 99999

    # 2. 火車站 (TRA) 最近距離
    tra_df = station_df[station_df['station_type'] == 'TRA_station']
    if not tra_df.empty:
        tra_tree = KDTree(tra_df[['lat', 'lon']].to_numpy())
        dist, _ = tra_tree.query(house_coords, k=1)
        house_df.loc[need_calc_mask, 'distance_to_tra_m'] = np.round(dist * DEGREE_TO_METER).astype(int)
    else:
        house_df.loc[need_calc_mask, 'distance_to_tra_m'] = 99999

    # 3. 捷運站 (MRT) 最近距離
    mrt_df = station_df[station_df['station_type'] == 'MRT_station']
    if not mrt_df.empty:
        mrt_tree = KDTree(mrt_df[['lat', 'lon']].to_numpy())
        dist, _ = mrt_tree.query(house_coords, k=1)
        calculated_dist = np.round(dist * DEGREE_TO_METER).astype(int)
        house_df.loc[need_calc_mask, 'distance_to_mrt_m'] = np.minimum(calculated_dist, 5000)
    else:
        house_df.loc[need_calc_mask, 'distance_to_mrt_m'] = 5000

    print(f"💾 正在儲存附加交通特徵後的房價資料至 {output_csv_path}...")
    house_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
    house_df.to_pickle(output_pickle_path)
    
    end_time = time.time()
    print(f"✅ 90 萬筆交通距離特徵計算完成！總耗時: {round(end_time - start_time, 2)} 秒")

if __name__ == "__main__":
    # 記得把這行改為你實際存檔的 90 萬筆房價 CSV 檔名
    #house_pickle = "地號_無地號_t2_features.pkl" 
    #house_pickle = '591_預售_經緯度_全_t10.pkl'
    #house_pickle = '未補全_全_t2.pkl'
    #house_pickle = '未補全_合併後_t2.pkl'
    #house_pickle = '591_housing_data_nopre2_t3.pkl'
    house_pickle = 'cinyi_t1.pkl'
    
    # 剛剛生成的 15 萬筆商店清單
    poi_csv = "taiwan_comprehensive_pois.csv" 
    station_pickle = "taiwan_stations_t2.pkl"
    # 輸出的最終結果檔名
    #output_csv = "地號_無地號_t3_features.csv"
    #output_pickle = "地號_無地號_t3_features.pkl"
    #output_csv = "591_預售_經緯度_全_t10_features.csv"
    #output_pickle = "591_預售_經緯度_全_t10_features.pkl"
    #output_csv = "未補全_全_t2_features.csv"
    #output_pickle = "未補全_全_t2_features.pkl"
    # output_csv = "未補全_合併後_t2_features.csv"
    # output_pickle = "未補全_合併後_t2_features.pkl"
    #output_csv = "591_housing_data_nopre2_t3_features.csv"
    #output_pickle = "591_housing_data_nopre2_t3_features.pkl"
    output_csv = "cinyi_t2.csv"
    output_pickle = "cinyi_t2.pkl"
    build_features_with_kdtree(house_pickle, poi_csv, station_pickle , output_csv, output_pickle)