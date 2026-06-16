# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class GeoFeatures(models.Model):
    id = models.BigAutoField(primary_key=True)
    緯度 = models.FloatField(blank=True, null=True)
    經度 = models.FloatField(blank=True, null=True)
    poi_convenience_count_300m = models.IntegerField(blank=True, null=True)
    poi_convenience_count_500m = models.IntegerField(blank=True, null=True)
    poi_bank_count_500m = models.IntegerField(blank=True, null=True)
    poi_food_count_300m = models.IntegerField(blank=True, null=True)
    poi_food_count_500m = models.IntegerField(blank=True, null=True)
    poi_medical_count_500m = models.IntegerField(blank=True, null=True)
    poi_parking_count_500m = models.IntegerField(blank=True, null=True)
    distance_to_nearest_worship_m = models.FloatField(blank=True, null=True)
    distance_to_thsr_m = models.FloatField(blank=True, null=True)
    distance_to_tra_m = models.FloatField(blank=True, null=True)
    distance_to_mrt_m = models.FloatField(blank=True, null=True)
    geo_location = models.OneToOneField('GeoLocation', models.DO_NOTHING, db_column='geo_location', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'geo_features'


class GeoLocation(models.Model):
    id = models.BigAutoField(primary_key=True)
    縣市 = models.CharField(max_length=20, blank=True, null=True)
    鄉鎮市區 = models.CharField(max_length=30, blank=True, null=True)
    完整行政區 = models.CharField(max_length=50, blank=True, null=True)
    土地位置建物門牌 = models.CharField(max_length=500, blank=True, null=True)
    唯一地理位置 = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'geo_location'


class House591Existing(models.Model):
    id = models.BigAutoField(primary_key=True)
    建物型態 = models.CharField(max_length=100, blank=True, null=True)
    建案名稱 = models.CharField(max_length=150, blank=True, null=True)
    坪數 = models.FloatField(blank=True, null=True)
    單價_萬元坪 = models.FloatField(blank=True, null=True)
    移轉層次 = models.CharField(max_length=100, blank=True, null=True)
    is_presale = models.IntegerField()
    age_was_missing = models.IntegerField()
    屋齡 = models.FloatField(blank=True, null=True)
    post_id = models.BigIntegerField(unique=True, blank=True, null=True)
    kind_name = models.CharField(max_length=50, blank=True, null=True)
    類型 = models.FloatField(blank=True, null=True)
    車棚 = models.FloatField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    總價 = models.BigIntegerField(blank=True, null=True)
    主建物坪數 = models.FloatField(blank=True, null=True)
    unit_price = models.CharField(max_length=100, blank=True, null=True)
    layout = models.CharField(max_length=100, blank=True, null=True)
    floor = models.CharField(max_length=100, blank=True, null=True)
    photo = models.TextField(blank=True, null=True)
    community = models.CharField(max_length=150, blank=True, null=True)
    瀏覽次數 = models.IntegerField()
    url = models.TextField(blank=True, null=True)
    成交年 = models.IntegerField(blank=True, null=True)
    成交月 = models.IntegerField(blank=True, null=True)
    交易距今月數 = models.IntegerField(blank=True, null=True)
    time_index = models.IntegerField(blank=True, null=True)
    電梯 = models.IntegerField(blank=True, null=True)
    移轉層次_清理後 = models.IntegerField(blank=True, null=True)
    屋齡_temp = models.CharField(max_length=50, blank=True, null=True)
    乾淨地理位置 = models.TextField(blank=True, null=True)
    乾淨地址 = models.TextField(blank=True, null=True)
    去號 = models.CharField(max_length=150, blank=True, null=True)
    去弄 = models.CharField(max_length=150, blank=True, null=True)
    去巷 = models.CharField(max_length=150, blank=True, null=True)
    最後地址 = models.FloatField(blank=True, null=True)
    用哪個地址 = models.FloatField(blank=True, null=True)
    use_google = models.IntegerField()
    area_last_month_price = models.FloatField(blank=True, null=True)
    總_編碼 = models.FloatField(blank=True, null=True)
    坪數_屋齡_交互 = models.FloatField(blank=True, null=True)
    預測 = models.FloatField(blank=True, null=True)
    總樓層數 = models.IntegerField(blank=True, null=True)
    geo_location = models.ForeignKey(GeoLocation, models.DO_NOTHING, db_column='geo_location')

    class Meta:
        managed = True
        db_table = 'house_591_existing'


class House591Presale(models.Model):
    id = models.BigAutoField(primary_key=True)
    建物型態 = models.CharField(max_length=100, blank=True, null=True)
    建案名稱 = models.CharField(max_length=150, blank=True, null=True)
    坪數 = models.FloatField(blank=True, null=True)
    單價_萬元坪 = models.FloatField(blank=True, null=True)
    移轉層次 = models.CharField(max_length=100, blank=True, null=True)
    is_presale = models.IntegerField()
    age_was_missing = models.IntegerField()
    屋齡 = models.CharField(max_length=50, blank=True, null=True)
    屋齡2 = models.FloatField(blank=True, null=True)
    hid = models.FloatField(blank=True, null=True)
    建物型態_temp = models.FloatField(blank=True, null=True)
    坪數_temp = models.CharField(max_length=100, blank=True, null=True)
    價錢單位 = models.CharField(max_length=50, blank=True, null=True)
    總價範圍 = models.CharField(max_length=100, blank=True, null=True)
    格局 = models.CharField(max_length=100, blank=True, null=True)
    網址 = models.TextField(blank=True, null=True)
    有無管理組織 = models.FloatField(blank=True, null=True)
    土地移轉總面積平方公尺 = models.FloatField(blank=True, null=True)
    電梯 = models.IntegerField(blank=True, null=True)
    標題 = models.CharField(max_length=255, blank=True, null=True)
    交屋時間 = models.CharField(max_length=100, blank=True, null=True)
    總樓層 = models.CharField(max_length=100, blank=True, null=True)
    乾淨地理位置 = models.TextField(blank=True, null=True)
    乾淨地址 = models.TextField(blank=True, null=True)
    去號 = models.CharField(max_length=150, blank=True, null=True)
    去弄 = models.CharField(max_length=150, blank=True, null=True)
    去巷 = models.CharField(max_length=150, blank=True, null=True)
    最後地址 = models.FloatField(blank=True, null=True)
    用哪個地址 = models.FloatField(blank=True, null=True)
    總樓層數 = models.IntegerField(blank=True, null=True)
    交易距今月數 = models.IntegerField(blank=True, null=True)
    time_index = models.IntegerField(blank=True, null=True)
    成交年 = models.IntegerField(blank=True, null=True)
    成交月 = models.IntegerField(blank=True, null=True)
    坪數區間 = models.CharField(max_length=50, blank=True, null=True)
    area_last_month_price = models.FloatField(blank=True, null=True)
    總_編碼 = models.FloatField(blank=True, null=True)
    主建物坪數 = models.FloatField(blank=True, null=True)
    單價_萬元坪_均價 = models.FloatField(blank=True, null=True)
    預測_均價 = models.FloatField(blank=True, null=True)
    預測結果_最小值 = models.FloatField(blank=True, null=True)
    預測結果_最大值 = models.FloatField(blank=True, null=True)
    單價_萬元坪區間 = models.CharField(max_length=100, blank=True, null=True)
    geo_location = models.ForeignKey(GeoLocation, models.DO_NOTHING, db_column='geo_location')

    class Meta:
        managed = True
        db_table = 'house_591_presale'


class HouseHistoryTransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    建物型態 = models.CharField(max_length=100, blank=True, null=True)
    建案名稱 = models.CharField(max_length=150, blank=True, null=True)
    坪數 = models.FloatField(blank=True, null=True)
    單價_萬元坪 = models.FloatField(blank=True, null=True)
    移轉層次 = models.CharField(max_length=100, blank=True, null=True)
    is_presale = models.IntegerField()
    age_was_missing = models.IntegerField()
    屋齡 = models.FloatField(blank=True, null=True)
    成交年 = models.IntegerField(blank=True, null=True)
    成交月 = models.IntegerField(blank=True, null=True)
    交易距今月數 = models.IntegerField(blank=True, null=True)
    總樓層數 = models.FloatField(blank=True, null=True)
    土地移轉總面積平方公尺 = models.FloatField(blank=True, null=True)
    建物移轉總面積平方公尺 = models.FloatField(blank=True, null=True)
    有無管理組織 = models.IntegerField(blank=True, null=True)
    電梯 = models.IntegerField(blank=True, null=True)
    交易標的 = models.CharField(max_length=100, blank=True, null=True)
    主建物面積 = models.FloatField(blank=True, null=True)
    time_index = models.FloatField(blank=True, null=True)
    area_last_month_price = models.FloatField(blank=True, null=True)
    geo_location = models.ForeignKey(GeoLocation, models.DO_NOTHING, db_column='geo_location')

    class Meta:
        managed = True
        db_table = 'house_history_transaction'
