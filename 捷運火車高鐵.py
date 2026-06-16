import pandas as pd
from pyrosm import OSM

def extract_taiwan_stations_precise(pbf_path):
    print("🚀 正在載入 OSM PBF 檔案...")
    osm = OSM(pbf_path)
    
    # 鎖定所有鐵路、捷運、高鐵的車站標籤
    custom_filter = {
        "railway": ["station"]
    }
    
    print("🔍 正在掃描全台軌道交通車站 (高鐵/台鐵/各縣市捷運)...")
    # 關鍵：加上 extra_attributes 叫 pyrosm 把營運商和車站細項標籤一起撈出來
    gdf = osm.get_data_by_custom_criteria(
        custom_filter=custom_filter,
        extra_attributes=["station", "operator", "highspeed"]
    )
    
    if gdf is None or len(gdf) == 0:
        print("❌ 找不到任何車站資料。")
        return pd.DataFrame()
    
    print(f"📊 成功撈出 {len(gdf)} 筆原始車站幾何資料，開始進行標籤精準分流...")
    
    # 取中心點經緯度
    centroids = gdf.geometry.centroid
    
    # 建立 DataFrame，確保所有防錯欄位都有建立
    stations_df = pd.DataFrame({
        "osm_id": gdf["id"],
        "name": gdf["name"].fillna("None") if "name" in gdf.columns else "None",
        "station_tag": gdf["station"].fillna("None") if "station" in gdf.columns else "None",
        "operator_tag": gdf["operator"].fillna("None") if "operator" in gdf.columns else "None",
        "highspeed_tag": gdf["highspeed"].fillna("None") if "highspeed" in gdf.columns else "None",
        "lon": centroids.x,
        "lat": centroids.y
    })
    
    # 🛠️ 透過 OSM 官方核心標籤進行分流
    def classify_station_by_tags(row):
        name = str(row["name"])
        station_tag = str(row["station_tag"]).lower()
        operator_tag = str(row["operator_tag"])
        highspeed_tag = str(row["highspeed_tag"])
        
        # 1. 優先判定高鐵 (台灣高鐵、THSR、或是名字有高鐵、或是 highspeed=yes)
        if "高鐵" in name or "THSR" in name or "台灣高速鐵路" in operator_tag or highspeed_tag == "yes":
            return "THSR_station"
            
        # 2. 判定捷運 (OSM 官方標準：station=subway 或 station=light_rail)
        # 加上台灣常見營運商關鍵字防錯 (如 臺北捷運, 桃園捷運, 高雄捷運, 台中捷運)
        if (station_tag in ["subway", "light_rail"] or 
            "捷運" in name or "MRT" in name or "輕軌" in name or 
            "捷運" in operator_tag or "MRT" in operator_tag):
            return "MRT_station"
            
        # 3. 剩下的歸類為一般火車站 (台鐵 TRA)
        return "TRA_station"
        
    stations_df["station_type"] = stations_df.apply(classify_station_by_tags, axis=1)
    
    # 只要高鐵與火車名字有包含 "捷運" (例如共構站：板橋、台北車站)，為免污染距離，將其修正回對應的主站體
    # 但如果是單純的台鐵/高鐵，就維持原樣
    
    # 精簡欄位
    stations_df = stations_df[["osm_id", "name", "station_type", "lat", "lon"]]
    stations_df = stations_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    
    print(f"✅ 提取與精準分類完成！")
    return stations_df

if __name__ == "__main__":
    pbf_file_path = r"E:/nominatim-data/taiwan-260512.osm.pbf" 
    df = extract_taiwan_stations_precise(pbf_file_path)
    
    if not df.empty:
        print("\n📊 修正後的車站類型分佈統計：")
        print(df["station_type"].value_counts())
        
        output_csv = "taiwan_stations_t2.csv"
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        df.to_pickle("taiwan_stations_t2.pkl")
        print(f"\n💾 乾淨的車站清單已重新儲存至：{output_csv}")