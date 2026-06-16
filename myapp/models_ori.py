from django.db import models  # 導入 Django 的資料庫模型模組

class BaseHouseFeatureModel(models.Model):
    """
    【共通基底抽象類別】
    完美對齊三張表共通的特徵欄位（不包含型態衝突的「屋齡」）
    """
    縣市 = models.CharField(max_length=20, db_index=True)
    鄉鎮市區 = models.CharField(max_length=30, db_index=True)
    完整行政區 = models.CharField(max_length=50, null=True, blank=True)
    土地位置建物門牌 = models.CharField(max_length=500, db_index=True)
    建物型態 = models.CharField(max_length=100, null=True, blank=True)
    建案名稱 = models.CharField(max_length=150, null=True, blank=True)
    坪數 = models.FloatField(null=True, blank=True)
    單價_萬元坪 = models.FloatField(null=True, blank=True)
    移轉層次 = models.CharField(max_length=100, null=True, blank=True)
    is_presale = models.IntegerField(default=0)
    age_was_missing = models.IntegerField(default=0)
    唯一地理位置 = models.TextField(null=True, blank=True)
    緯度 = models.FloatField(null=True, blank=True, db_index=True)
    經度 = models.FloatField(null=True, blank=True, db_index=True)

    # POI 數量與交通距離
    poi_convenience_count_300m = models.IntegerField(default=0)
    poi_convenience_count_500m = models.IntegerField(default=0)
    poi_bank_count_500m = models.IntegerField(default=0)
    poi_food_count_300m = models.IntegerField(default=0)
    poi_food_count_500m = models.IntegerField(default=0)
    poi_medical_count_500m = models.IntegerField(default=0)
    poi_parking_count_500m = models.IntegerField(default=0)
    distance_to_nearest_worship_m = models.FloatField(null=True, blank=True)
    distance_to_thsr_m = models.FloatField(null=True, blank=True)
    distance_to_tra_m = models.FloatField(null=True, blank=True)
    distance_to_mrt_m = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True
        
# ==========================================
# 1. 591 非預售資料表 (208,324 筆) -> 屋齡為數字
# ==========================================
class House591Existing(BaseHouseFeatureModel):
    屋齡 = models.FloatField(null=True, blank=True) # 👈 這裡維持 float64 數字
    總樓層數 = models.IntegerField(null=True, blank=True) # 👈 補上這行
    
    post_id = models.BigIntegerField(unique=True, null=True, blank=True)
    kind_name = models.CharField(max_length=50, null=True, blank=True)
    類型 = models.FloatField(null=True, blank=True)
    車棚 = models.FloatField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    總價 = models.BigIntegerField(null=True, blank=True)
    主建物坪數 = models.FloatField(null=True, blank=True)
    unit_price = models.CharField(max_length=100, null=True, blank=True)
    layout = models.CharField(max_length=100, null=True, blank=True)
    floor = models.CharField(max_length=100, null=True, blank=True)
    photo = models.TextField(null=True, blank=True)
    community = models.CharField(max_length=150, null=True, blank=True)
    瀏覽次數 = models.IntegerField(default=0)
    url = models.TextField(null=True, blank=True)
    
    # 時間與地址
    成交年 = models.IntegerField(null=True, blank=True)
    成交月 = models.IntegerField(null=True, blank=True)
    交易距今月數 = models.IntegerField(null=True, blank=True)
    time_index = models.IntegerField(null=True, blank=True)
    電梯 = models.IntegerField(null=True, blank=True)
    移轉層次_清理後 = models.IntegerField(null=True, blank=True)
    屋齡_temp = models.CharField(max_length=50, null=True, blank=True)
    乾淨地理位置 = models.TextField(null=True, blank=True)
    乾淨地址 = models.TextField(null=True, blank=True)
    去號 = models.CharField(max_length=150, null=True, blank=True)
    去弄 = models.CharField(max_length=150, null=True, blank=True)
    去巷 = models.CharField(max_length=150, null=True, blank=True)
    最後地址 = models.FloatField(null=True, blank=True)
    用哪個地址 = models.FloatField(null=True, blank=True)
    use_google = models.IntegerField(default=0)
    
    # 預測
    area_last_month_price = models.FloatField(null=True, blank=True)
    總_編碼 = models.FloatField(null=True, blank=True)
    坪數_屋齡_交互 = models.FloatField(null=True, blank=True)
    預測 = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'house_591_existing'        

# ==========================================
# 2. 591 預售屋資料表 (8,832 筆) -> 🔥 屋齡單獨維持 object/str
# ==========================================
class House591Presale(BaseHouseFeatureModel):
    屋齡 = models.CharField(max_length=50, null=True, blank=True) # 👈 完美鎖定為字串 (object)！
    屋齡2 = models.FloatField(null=True, blank=True)            # 👈 數值型態留給屋齡2
    
    hid = models.FloatField(null=True, blank=True)
    建物型態_temp = models.FloatField(null=True, blank=True)
    坪數_temp = models.CharField(max_length=100, null=True, blank=True)
    價錢單位 = models.CharField(max_length=50, null=True, blank=True)
    總價範圍 = models.CharField(max_length=100, null=True, blank=True)
    單價_萬元坪區間 = models.CharField(max_length=100, null=True, blank=True)
    格局 = models.CharField(max_length=100, null=True, blank=True)
    網址 = models.TextField(null=True, blank=True)
    有無管理組織 = models.FloatField(null=True, blank=True) 
    土地移轉總面積平方公尺 = models.FloatField(null=True, blank=True)
    電梯 = models.IntegerField(null=True, blank=True)
    標題 = models.CharField(max_length=255, null=True, blank=True)
    交屋時間 = models.CharField(max_length=100, null=True, blank=True)
    總樓層 = models.CharField(max_length=100, null=True, blank=True)
    
    # 地址清洗
    乾淨地理位置 = models.TextField(null=True, blank=True)
    乾淨地址 = models.TextField(null=True, blank=True)
    去號 = models.CharField(max_length=150, null=True, blank=True)
    去弄 = models.CharField(max_length=150, null=True, blank=True)
    去巷 = models.CharField(max_length=150, null=True, blank=True)
    最後地址 = models.FloatField(null=True, blank=True)
    用哪個地址 = models.FloatField(null=True, blank=True)
    
    # 分析與預測特徵
    總樓層數 = models.IntegerField(null=True, blank=True)
    交易距今月數 = models.IntegerField(null=True, blank=True)
    time_index = models.IntegerField(null=True, blank=True)
    成交年 = models.IntegerField(null=True, blank=True)
    成交月 = models.IntegerField(null=True, blank=True)
    坪數區間 = models.CharField(max_length=50, null=True, blank=True)
    area_last_month_price = models.FloatField(null=True, blank=True)
    總_編碼 = models.FloatField(null=True, blank=True)
    主建物坪數 = models.FloatField(null=True, blank=True)
    
    # 預售屋開價預測
    單價_萬元坪_均價 = models.FloatField(null=True, blank=True)
    預測_均價 = models.FloatField(null=True, blank=True)
    預測結果_最小值 = models.FloatField(null=True, blank=True)
    預測結果_最大值 = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'house_591_presale'   
# ==========================================
# 3. 舊歷史交易登錄資料表 (970,806 筆) -> 屋齡為數字
# ==========================================
class HistoryTransaction(BaseHouseFeatureModel):
    屋齡 = models.FloatField(null=True, blank=True) # 👈 這裡維持 float64 數字
    
    成交年 = models.IntegerField(null=True, blank=True)
    成交月 = models.IntegerField(null=True, blank=True)
    交易距今月數 = models.IntegerField(null=True, blank=True)
    總樓層數 = models.FloatField(null=True, blank=True)
    土地移轉總面積平方公尺 = models.FloatField(null=True, blank=True)
    建物移轉總面積平方公尺 = models.FloatField(null=True, blank=True)
    有無管理組織 = models.IntegerField(null=True, blank=True)
    電梯 = models.IntegerField(null=True, blank=True)
    交易標的 = models.CharField(max_length=100, null=True, blank=True)
    主建物面積 = models.FloatField(null=True, blank=True)
    time_index = models.FloatField(null=True, blank=True)
    area_last_month_price = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'house_history_transaction'             