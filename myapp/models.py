from django.db import models
from django.contrib.auth.models import User

class City(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="縣市"
    )

    class Meta:
        db_table = "city"
        verbose_name = "縣市"


class District(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name="縣市"
    )

    name = models.CharField(
        max_length=30,
        verbose_name="鄉鎮市區"
    )

    class Meta:
        db_table = "district"

        constraints = [
            models.UniqueConstraint(
                fields=["city", "name"],
                name="unique_city_district"
            )
        ]

        verbose_name = "鄉鎮市區"


class PropertyLocation(models.Model):
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        verbose_name="鄉鎮市區"
    )

    full_district = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="完整行政區"
    )

    full_address = models.CharField(
        max_length=500,
        db_index=True,
        verbose_name="土地位置建物門牌"
    )

    clean_geo = models.TextField(
        null=True,
        blank=True,
        verbose_name="乾淨地理位置"
    )

    clean_address = models.TextField(
        null=True,
        blank=True,
        verbose_name="乾淨地址"
    )

    unique_geo = models.TextField(
        null=True,
        blank=True,
        verbose_name="唯一地理位置"
    )

    remove_no = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="去號"
    )

    remove_lane = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="去弄"
    )

    remove_alley = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="去巷"
    )

    final_address = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="最後地址"
    )

    address_used = models.FloatField(
        null=True,
        blank=True,
        verbose_name="用哪個地址"
    )

    latitude = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="緯度"
    )

    longitude = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="經度"
    )

    class Meta:
        db_table = "property_location"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "district",
                    "full_address",
                    "latitude",
                    "longitude"
                ],
                name="unique_property_location"
            )
        ]

        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["full_address"]),
        ]

        verbose_name = "房屋地址位置"


class Property(models.Model):
    SOURCE_CHOICES = [
        ("591_existing", "591非預售"),
        ("591_presale", "591預售"),
        ("history", "歷史交易"),
        ("sinyi", "信義房屋"),
    ]
    
    is_training_valid = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="是否為有效訓練資料"
    )   
    filter_reason = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="篩選刪除原因"
    )  
      
    location = models.ForeignKey(
        PropertyLocation,
        on_delete=models.PROTECT,
        verbose_name="地理位置"
    )

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        db_index=True,
        verbose_name="資料來源"
    )

    import_batch_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="匯入批次key"
    )

    building_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="建物型態"
    )

    project_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="建案名稱"
    )

    area_ping = models.FloatField(
        null=True,
        blank=True,
        verbose_name="坪數"
    )

    unit_price = models.FloatField(
        null=True,
        blank=True,
        verbose_name="單價_萬元坪"
    )

    transfer_floor = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="移轉層次"
    )

    transfer_floor_clean = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="移轉層次_清理後"
    )

    total_floors = models.FloatField(
        null=True,
        blank=True,
        verbose_name="總樓層數"
    )

    building_age = models.FloatField(
        null=True,
        blank=True,
        verbose_name="屋齡"
    )

    building_age_text = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="屋齡_temp"
    )

    is_presale = models.BooleanField(
        default=False,
        db_index=True,  # 💡 補上這個
        verbose_name="is_presale"
    )

    age_was_missing = models.BooleanField(
        default=False,
        verbose_name="age_was_missing"
    )
    
    is_training_valid = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="是否為有效訓練資料"
    )
    
    deal_year = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="成交年"
    )

    deal_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="成交月"
    )

    months_since_deal = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="交易距今月數"
    )

    time_index = models.FloatField(
        null=True,
        blank=True,
        verbose_name="time_index"
    )

    elevator = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="電梯"
    )

    main_building_ping = models.FloatField(
        null=True,
        blank=True,
        verbose_name="主建物坪數"
    )

    class Meta:
        db_table = "property"

        indexes = [
            models.Index(fields=["source_type"]),
            models.Index(fields=["deal_year", "deal_month"]),
            models.Index(fields=["building_type"]),
            models.Index(fields=["area_ping"]),
            models.Index(fields=["unit_price"]),
            models.Index(fields=["building_age"]),
            models.Index(fields=["import_batch_key"]),
        ]

        verbose_name = "房屋主資料"


class PropertyPOIFeature(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    convenience_300m = models.IntegerField(default=0, verbose_name="poi_convenience_count_300m")
    convenience_500m = models.IntegerField(default=0, verbose_name="poi_convenience_count_500m")
    bank_500m = models.IntegerField(default=0, verbose_name="poi_bank_count_500m")
    food_300m = models.IntegerField(default=0, verbose_name="poi_food_count_300m")
    food_500m = models.IntegerField(default=0, verbose_name="poi_food_count_500m")
    medical_500m = models.IntegerField(default=0, verbose_name="poi_medical_count_500m")
    parking_500m = models.IntegerField(default=0, verbose_name="poi_parking_count_500m")

    distance_to_worship = models.FloatField(null=True, blank=True, verbose_name="distance_to_nearest_worship_m")
    distance_to_thsr = models.FloatField(null=True, blank=True, verbose_name="distance_to_thsr_m")
    distance_to_tra = models.FloatField(null=True, blank=True, verbose_name="distance_to_tra_m")
    distance_to_mrt = models.FloatField(null=True, blank=True, verbose_name="distance_to_mrt_m")

    class Meta:
        db_table = "property_poi_feature"
        verbose_name = "POI 特徵"


class PropertyPredictionFeature(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    area_last_month_price = models.FloatField(null=True, blank=True, verbose_name="area_last_month_price")
    total_encoded = models.FloatField(null=True, blank=True, verbose_name="總_編碼")
    area_age_interaction = models.FloatField(null=True, blank=True, verbose_name="坪數_屋齡_交互")

    prediction_price = models.FloatField(null=True, blank=True, verbose_name="預測_萬元坪")
    
    prediction = models.FloatField(null=True, blank=True, verbose_name="預測")
    prediction_avg = models.FloatField(null=True, blank=True, verbose_name="預測_均價")
    prediction_min = models.FloatField(null=True, blank=True, verbose_name="預測結果_最小值")
    prediction_max = models.FloatField(null=True, blank=True, verbose_name="預測結果_最大值")

    class Meta:
        db_table = "property_prediction_feature"
        verbose_name = "預測特徵"


class House591ExistingDetail(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    post_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="post_id"
    )

    kind_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="kind_name")
    type_value = models.FloatField(null=True, blank=True, verbose_name="類型")
    car_shed = models.FloatField(null=True, blank=True, verbose_name="車棚")

    title = models.CharField(max_length=255, null=True, blank=True, verbose_name="title")
    total_price = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="總價")
    unit_price_text = models.CharField(max_length=100, null=True, blank=True, verbose_name="unit_price")

    layout = models.CharField(max_length=100, null=True, blank=True, verbose_name="layout")
    floor = models.CharField(max_length=100, null=True, blank=True, verbose_name="floor")
    photo = models.TextField(null=True, blank=True, verbose_name="photo")
    community = models.CharField(max_length=150, null=True, blank=True, verbose_name="community")
    views = models.IntegerField(default=0, db_index=True, verbose_name="瀏覽次數")
    url = models.TextField(null=True, blank=True, verbose_name="url")

    use_google = models.IntegerField(default=0, verbose_name="use_google")

    class Meta:
        db_table = "house_591_existing_detail"
        verbose_name = "591非預售明細"


class House591PresaleDetail(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    hid = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="hid"
    )

    building_type_temp = models.FloatField(null=True, blank=True, verbose_name="建物型態_temp")
    area_temp = models.CharField(max_length=100, null=True, blank=True, verbose_name="坪數_temp")

    price_unit = models.CharField(max_length=50, null=True, blank=True, verbose_name="價錢單位")
    total_price_range = models.CharField(max_length=100, null=True, blank=True, verbose_name="總價範圍")
    unit_price_range = models.CharField(max_length=100, null=True, blank=True, verbose_name="單價_萬元坪區間")

    layout = models.CharField(max_length=100, null=True, blank=True, verbose_name="格局")
    url = models.TextField(null=True, blank=True, verbose_name="網址")

    has_management = models.FloatField(null=True, blank=True, verbose_name="有無管理組織")
    land_transfer_area_m2 = models.FloatField(null=True, blank=True, verbose_name="土地移轉總面積平方公尺")

    title = models.CharField(max_length=255, null=True, blank=True, verbose_name="標題")
    handover_time = models.CharField(max_length=100, null=True, blank=True, verbose_name="交屋時間")
    total_floor_text = models.CharField(max_length=100, null=True, blank=True, verbose_name="總樓層")

    area_range = models.CharField(max_length=50, null=True, blank=True, verbose_name="坪數區間")
    avg_unit_price = models.FloatField(null=True, blank=True, verbose_name="單價_萬元坪_均價")

    class Meta:
        db_table = "house_591_presale_detail"
        verbose_name = "591預售明細"


class HistoryTransactionDetail(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    land_transfer_area_m2 = models.FloatField(null=True, blank=True, verbose_name="土地移轉總面積平方公尺")
    building_transfer_area_m2 = models.FloatField(null=True, blank=True, verbose_name="建物移轉總面積平方公尺")

    has_management = models.IntegerField(null=True, blank=True, verbose_name="有無管理組織")
    transaction_target = models.CharField(max_length=100, null=True, blank=True, verbose_name="交易標的")
    main_building_area = models.FloatField(null=True, blank=True, verbose_name="主建物面積")

    class Meta:
        db_table = "history_transaction_detail"
        verbose_name = "歷史交易明細"
        
class SinyiDetail(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        verbose_name="房屋"
    )

    house_no = models.CharField(max_length=100, unique=True, verbose_name="houseNo")
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="name")

    image = models.TextField(null=True, blank=True, verbose_name="image")
    large_image = models.TextField(null=True, blank=True, verbose_name="largeImage")
    image_tag = models.TextField(null=True, blank=True, verbose_name="imageTag")

    comm_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="commId")
    comm_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="commName")

    discount = models.FloatField(null=True, blank=True, verbose_name="discount")
    address = models.TextField(null=True, blank=True, verbose_name="address")
    age_text = models.CharField(max_length=100, null=True, blank=True, verbose_name="age")

    houselandtype = models.CharField(max_length=100, null=True, blank=True, verbose_name="houselandtype")
    houselandtype_show = models.CharField(max_length=100, null=True, blank=True, verbose_name="houselandtypeShow")

    price_first = models.BigIntegerField(null=True, blank=True, verbose_name="priceFirst")
    area_land = models.FloatField(null=True, blank=True, verbose_name="地坪")

    is_has_balcony = models.IntegerField(null=True, blank=True, verbose_name="陽台")
    layout = models.CharField(max_length=100, null=True, blank=True, verbose_name="格局")

    is_parking = models.BooleanField(default=False, verbose_name="停車場")
    parking = models.TextField(
        null=True,
        blank=True,
        verbose_name="parking"
    )
    total_price = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="totalPrice"
    )    
    tags = models.TextField(null=True, blank=True, verbose_name="tags")
    three_months_clicks = models.IntegerField(default=0, db_index=True, verbose_name="點擊率")

    is_off = models.BooleanField(default=False, verbose_name="isOff")
    is_similar = models.BooleanField(default=False, verbose_name="isSimilar")
    share_url = models.TextField(null=True, blank=True, verbose_name="shareURL")

    status = models.IntegerField(null=True, blank=True, verbose_name="status")
    kind = models.IntegerField(null=True, blank=True, verbose_name="kind")
    object_type = models.IntegerField(null=True, blank=True, verbose_name="objectType")

    is_3dvr = models.BooleanField(default=False, verbose_name="3DVR")
    is_3dvr2 = models.BooleanField(default=False, verbose_name="Is3Dvr")

    zip_code = models.IntegerField(null=True, blank=True, verbose_name="zipCode")
    group_company = models.FloatField(null=True, blank=True, verbose_name="groupCompany")

    add_layout = models.TextField(null=True, blank=True, verbose_name="addLayout")
    total_layout = models.TextField(null=True, blank=True, verbose_name="totalLayout")

    is_has_video = models.BooleanField(default=False, verbose_name="isHasVideo")
    is_has_view = models.BooleanField(default=False, verbose_name="isHasView")

    city_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="city_name")
    city_code = models.CharField(max_length=50, null=True, blank=True, verbose_name="city_code")

    page = models.IntegerField(null=True, blank=True, verbose_name="page")
    source_url = models.TextField(null=True, blank=True, verbose_name="source_url")

    class Meta:
        db_table = "sinyi_detail"
        verbose_name = "信義房屋明細"
        indexes = [
            models.Index(fields=["house_no"]),
            models.Index(fields=["three_months_clicks"]),
            models.Index(fields=["discount"]),
            models.Index(fields=["price_first"]),
            models.Index(fields=["total_price"]),  # 💡 補上這個
        ]

class FavoriteProperty(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, verbose_name="房屋")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏時間")

    class Meta:
        db_table = "favorite_property"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"],
                name="unique_user_property_favorite"
            )
        ]
        verbose_name = "我的收藏"       