import pandas as pd
from pyrosm import OSM
from shapely.geometry import Point

def extract_comprehensive_poi(pbf_path):
    print("🚀 正在載入 OSM PBF 檔案...")
    osm = OSM(pbf_path)
    
    # 1. 擴充後的自訂篩選器（網羅所有與房價、生活機能、嫌惡設施相關的標籤）
    custom_filter = {
        "shop": True, # 包含全聯、家樂福、四大超商、各類零售店
        "amenity": [
            # 餐飲類機能
            "restaurant", "cafe", "fast_food", "food_court", "pub", "bar",
            # 醫療機能 (剛需)
            "clinic", "hospital", "pharmacy",
            # 金融商業指標
            "bank", "atm",
            # 教育與學區
            "kindergarten", "school", "university", "library",
            # 日常生活與交通
            "market", "post_office", "bicycle_rental", "parking",
            # 潛在嫌惡設施 (負面特徵)
            "place_of_worship" 
        ]
    }
    
    print("🔍 正在高效掃描全台基礎設施與商店 (點與面)...")
    gdf = osm.get_data_by_custom_criteria(custom_filter=custom_filter)
    
    if gdf is None or len(gdf) == 0:
        print("❌ 找不到任何符合條件的 POI。")
        return pd.DataFrame()
    
    print(f"📊 成功撈出 {len(gdf)} 筆原始幾何資料，正在計算中心點座標...")
    
    # 2. 不管點（Node）還是面（Way），統一取中心點轉成經緯度
    centroids = gdf.geometry.centroid
    
    # 3. 建立精簡的 DataFrame
    shops_df = pd.DataFrame({
        "osm_id": gdf["id"],
        "name": gdf["name"] if "name" in gdf.columns else "None",
        "shop_type": gdf["shop"] if "shop" in gdf.columns else "None",
        "amenity_type": gdf["amenity"] if "amenity" in gdf.columns else "None",
        "lon": centroids.x,
        "lat": centroids.y
    })
    
    # 4. 精準標籤化分類：讓後續 KDTree 可以依欄位各自計算數量
    def get_main_type(row):
        # 如果是 shop 類，標記為 shop_xxx (例如: shop_convenience 代表便利商店)
        if pd.notna(row["shop_type"]) and row["shop_type"] != "None":
            return f"shop_{row['shop_type']}"
        # 如果是 amenity 類，標記為 amenity_xxx (例如: amenity_bank 代表銀行)
        if pd.notna(row["amenity_type"]) and row["amenity_type"] != "None":
            return f"amenity_{row['amenity_type']}"
        return "unknown"
    
    print("🏷️ 正在進行特徵類別標籤化...")
    shops_df["poi_type"] = shops_df.apply(get_main_type, axis=1)
    
    # 只保留空間計算需要的核心欄位
    shops_df = shops_df[["osm_id", "name", "poi_type", "lat", "lon"]]
    
    # 清洗掉經緯度有空值的異常資料
    shops_df = shops_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    
    # 補值：有些店神祕網友沒寫名字，給它 None 避免之後程式報錯
    shops_df["name"] = shops_df["name"].fillna("None")
    
    print(f"✅ 提取完成！最終獲得 {len(shops_df)} 筆全方位 POI 清單。")
    return shops_df

if __name__ == "__main__":
    # 確保檔案名稱與路徑正確
    pbf_file_path = r"E:/nominatim-data/taiwan-260512.osm.pbf" 
    
    # 執行函數
    taiwan_poi_df = extract_comprehensive_poi(pbf_file_path)
    
    if not taiwan_poi_df.empty:
        print("\n👀 前 10 筆產出資料範例（注意 poi_type 欄位）：")
        print(taiwan_poi_df[["name", "poi_type", "lat", "lon"]].head(10))
        
        # 查看撈出來的 POI 大分類分布，確認有沒有成功抓到各種類別
        print("\n📊 撈出的前 15 大 POI 類別統計：")
        print(taiwan_poi_df["poi_type"].value_counts().head(15))
        
        # 儲存成全新的 CSV 檔
        output_csv = "taiwan_comprehensive_pois.csv"
        taiwan_poi_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        taiwan_poi_df.to_pickle("taiwan_comprehensive_pois.pkl")
        print(f"\n💾 歷史級地理特徵清單已儲存至：{output_csv}")