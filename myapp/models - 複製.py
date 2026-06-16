from django.db import models  # 導入 Django 的資料庫模型模組

class Product(models.Model):  # 定義商品主檔表，繼承 Django 的 Model 類
    """商品基本資訊表"""
    # 儲存對齊後的標準名稱，方便搜尋與歸類，最大長度 255 字元
    name = models.CharField(max_length=255, verbose_name="標準化型號名稱") 
    # 儲存品牌名稱，例如：ASUS, MSI，最大長度 50 字元
    brand = models.CharField(max_length=50, verbose_name="品牌") 
    # 儲存零件分類，例如：GPU, CPU, RAM，方便前端過濾
    category = models.CharField(max_length=50, verbose_name="分類(如:GPU, CPU)") 
    # 使用 JSON 格式儲存不同硬體的詳細參數（如功耗、頻率），提升擴展性
    specs_json = models.JSONField(default=dict, verbose_name="硬體詳細參數") 
    # 自動紀錄這筆商品資料在資料庫中建立的時間
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):  # 定義物件在後台或偵錯時顯示的文字格式
        return f"[{self.brand}] {self.name}" 

class Platform(models.Model):  # 定義台灣電商平台表
    """台灣 5 大電商平台資訊"""
    # 平台名稱，unique=True 確保「原價屋」等名稱不會重複建立
    name = models.CharField(max_length=100, unique=True, verbose_name="平台名稱") 
    # 儲存該平台的首頁 URL
    base_url = models.URLField(verbose_name="平台首頁連結") 
    # 選填欄位，用來儲存爬蟲特定的標記或識別碼
    crawler_target = models.CharField(max_length=100, blank=True) 

    def __str__(self):  # 回傳平台名稱作為顯示字串
        return self.name 

class PriceRecord(models.Model):  # 定義價格流水帳表，這是數據分析的核心
    """價格流水帳（機器學習與比價的核心）"""
    # 關聯到 Product 表，當商品被刪除時，對應的價格紀錄也會刪除
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history') 
    # 關聯到 Platform 表，追蹤這筆價格是來自哪個網站
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE) 
    # 儲存爬蟲當下抓到的完整文字，保留原始數據以便後續比對清洗
    original_title = models.CharField(max_length=500, verbose_name="原始爬取標題") 
    # 儲存整數價格，方便後續做運算與模型分析
    price = models.IntegerField(verbose_name="當前價格") 
    # 標記該商品在爬取當下是否有現貨
    is_stock = models.BooleanField(default=True, verbose_name="是否有庫存") 
    # 自動紀錄抓取的時間，db_index=True 建立資料庫索引以加速時間排序查詢
    created_at = models.DateTimeField(auto_now_add=True, db_index=True) 

    class Meta:  # 資料表的元數據配置
        # 建立複合索引：優化同時查詢「特定商品」且「按時間排序」的效能
        indexes = [
            models.Index(fields=['product', 'created_at']), 
        ]
        # 預設查詢結果按時間由新到舊排序
        ordering = ['-created_at'] 

    def __str__(self):  # 定義每一筆價格紀錄的顯示方式
        return f"{self.product.name} - {self.platform.name}: ${self.price}"