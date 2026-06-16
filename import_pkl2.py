import os
import math
import uuid
import django
import pandas as pd
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "final.settings")
django.setup()

from myapp.models import (
    City,
    District,
    PropertyLocation,
    Property,
    PropertyPOIFeature,
    PropertyPredictionFeature,
    House591ExistingDetail,
    House591PresaleDetail,
    HistoryTransactionDetail,
    SinyiDetail,
)

BATCH_SIZE = 10000

CITY_CACHE = {}
DISTRICT_CACHE = {}
LOCATION_CACHE = {}


def clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def clean_str(value):
    value = clean(value)
    if value is None:
        return None
    return str(value)


def clean_bool(value):
    value = clean(value)
    if value is None:
        return False
    try:
        return bool(int(value))
    except Exception:
        return False


def get_value(row, col):
    return clean(row.get(col))


def get_location(row):
    city_name = get_value(row, "縣市") or "未知縣市"
    district_name = get_value(row, "鄉鎮市區") or "未知區域"
    full_address = get_value(row, "土地位置建物門牌") or "未知地址"
    latitude = get_value(row, "緯度")
    longitude = get_value(row, "經度")

    if city_name not in CITY_CACHE:
        CITY_CACHE[city_name], _ = City.objects.get_or_create(name=city_name)

    city = CITY_CACHE[city_name]
    district_key = (city.id, district_name)

    if district_key not in DISTRICT_CACHE:
        DISTRICT_CACHE[district_key], _ = District.objects.get_or_create(
            city=city,
            name=district_name,
        )

    district = DISTRICT_CACHE[district_key]

    loc_key = (
        district.id,
        full_address,
        latitude,
        longitude,
    )

    if loc_key not in LOCATION_CACHE:
        LOCATION_CACHE[loc_key], _ = PropertyLocation.objects.get_or_create(
            district=district,
            full_address=full_address,
            latitude=latitude,
            longitude=longitude,
            defaults={
                "full_district": get_value(row, "完整行政區"),
                "clean_geo": get_value(row, "乾淨地理位置"),
                "clean_address": get_value(row, "乾淨地址"),
                "unique_geo": get_value(row, "唯一地理位置"),
                "remove_no": get_value(row, "去號"),
                "remove_lane": get_value(row, "去弄"),
                "remove_alley": get_value(row, "去巷"),
                "final_address": clean_str(get_value(row, "最後地址")),
                "address_used": get_value(row, "用哪個地址"),
            },
        )

    return LOCATION_CACHE[loc_key]


def make_property(row, source_type):
    building_age = get_value(row, "屋齡")

    if "屋齡_temp" in row:
        building_age_text = clean_str(get_value(row, "屋齡_temp"))
    else:
        building_age_text = clean_str(building_age)

    total_floors = get_value(row, "總樓層數")
    if total_floors is None:
        total_floors = get_value(row, "總樓層")

    return Property(
        location=get_location(row),
        source_type=source_type,
        building_type=get_value(row, "建物型態"),
        project_name=get_value(row, "建案名稱"),
        area_ping=get_value(row, "坪數"),
        unit_price=get_value(row, "單價_萬元坪"),
        transfer_floor=get_value(row, "移轉層次"),
        transfer_floor_clean=get_value(row, "移轉層次_清理後"),
        total_floors=total_floors,
        building_age=building_age,
        building_age_text=building_age_text,
        is_presale=clean_bool(get_value(row, "is_presale")),
        age_was_missing=clean_bool(get_value(row, "age_was_missing")),
        is_training_valid=clean_bool(get_value(row, "is_training_valid")),
        deal_year=get_value(row, "成交年"),
        deal_month=get_value(row, "成交月"),
        months_since_deal=get_value(row, "交易距今月數"),
        time_index=get_value(row, "time_index"),
        elevator=get_value(row, "電梯"),
        main_building_ping=get_value(row, "主建物坪數"),
    )


def bulk_insert_properties(props):
    batch_key = str(uuid.uuid4())

    for prop in props:
        prop.import_batch_key = batch_key

    Property.objects.bulk_create(props, batch_size=BATCH_SIZE)

    created_props = list(
        Property.objects
        .filter(import_batch_key=batch_key)
        .order_by("id")
    )

    if len(created_props) != len(props):
        raise RuntimeError(
            f"Property 數量不一致：預期 {len(props)}，實際 {len(created_props)}"
        )

    return created_props


def make_poi(property_id, row):
    return PropertyPOIFeature(
        property_id=property_id,
        convenience_300m=get_value(row, "poi_convenience_count_300m") or 0,
        convenience_500m=get_value(row, "poi_convenience_count_500m") or 0,
        bank_500m=get_value(row, "poi_bank_count_500m") or 0,
        food_300m=get_value(row, "poi_food_count_300m") or 0,
        food_500m=get_value(row, "poi_food_count_500m") or 0,
        medical_500m=get_value(row, "poi_medical_count_500m") or 0,
        parking_500m=get_value(row, "poi_parking_count_500m") or 0,
        distance_to_worship=get_value(row, "distance_to_nearest_worship_m"),
        distance_to_thsr=get_value(row, "distance_to_thsr_m"),
        distance_to_tra=get_value(row, "distance_to_tra_m"),
        distance_to_mrt=get_value(row, "distance_to_mrt_m"),
    )


def make_prediction(property_id, row):
    return PropertyPredictionFeature(
        property_id=property_id,
        area_last_month_price=get_value(row, "area_last_month_price"),
        total_encoded=get_value(row, "總_編碼"),
        area_age_interaction=get_value(row, "坪數_屋齡_交互"),
        prediction_price=get_value(row, "預測_萬元坪"),
        prediction=get_value(row, "預測"),
        prediction_avg=get_value(row, "預測_均價"),
        prediction_min=get_value(row, "預測結果_最小值"),
        prediction_max=get_value(row, "預測結果_最大值"),
    )


def save_591_existing_batch(props, rows):
    with transaction.atomic():
        created_props = bulk_insert_properties(props)

        poi_list = []
        pred_list = []
        detail_list = []

        for prop, row in zip(created_props, rows):
            pid = prop.id
            poi_list.append(make_poi(pid, row))
            pred_list.append(make_prediction(pid, row))

            detail_list.append(House591ExistingDetail(
                property_id=pid,
                post_id=get_value(row, "post_id"),
                kind_name=get_value(row, "kind_name"),
                type_value=get_value(row, "類型"),
                car_shed=get_value(row, "車棚"),
                title=get_value(row, "title"),
                total_price=get_value(row, "總價"),
                unit_price_text=get_value(row, "unit_price"),
                layout=get_value(row, "layout"),
                floor=get_value(row, "floor"),
                photo=get_value(row, "photo"),
                community=get_value(row, "community"),
                views=get_value(row, "瀏覽次數") or 0,
                url=get_value(row, "url"),
                use_google=get_value(row, "use_google") or 0,
            ))

        PropertyPOIFeature.objects.bulk_create(poi_list, batch_size=BATCH_SIZE)
        PropertyPredictionFeature.objects.bulk_create(pred_list, batch_size=BATCH_SIZE)
        House591ExistingDetail.objects.bulk_create(detail_list, batch_size=BATCH_SIZE)


def save_591_presale_batch(props, rows):
    with transaction.atomic():
        created_props = bulk_insert_properties(props)

        poi_list = []
        pred_list = []
        detail_list = []

        for prop, row in zip(created_props, rows):
            pid = prop.id
            poi_list.append(make_poi(pid, row))
            pred_list.append(make_prediction(pid, row))

            detail_list.append(House591PresaleDetail(
                property_id=pid,
                hid=get_value(row, "hid"),
                building_type_temp=get_value(row, "建物型態_temp"),
                area_temp=clean_str(get_value(row, "坪數_temp")),
                price_unit=get_value(row, "價錢單位"),
                total_price_range=get_value(row, "總價範圍"),
                unit_price_range=get_value(row, "單價_萬元坪區間"),
                layout=get_value(row, "格局"),
                url=get_value(row, "網址"),
                has_management=get_value(row, "有無管理組織"),
                land_transfer_area_m2=get_value(row, "土地移轉總面積平方公尺"),
                title=get_value(row, "標題"),
                handover_time=get_value(row, "交屋時間"),
                total_floor_text=get_value(row, "總樓層"),
                area_range=get_value(row, "坪數區間"),
                avg_unit_price=get_value(row, "單價_萬元坪_均價"),
            ))

        PropertyPOIFeature.objects.bulk_create(poi_list, batch_size=BATCH_SIZE)
        PropertyPredictionFeature.objects.bulk_create(pred_list, batch_size=BATCH_SIZE)
        House591PresaleDetail.objects.bulk_create(detail_list, batch_size=BATCH_SIZE)


def save_history_batch(props, rows):
    with transaction.atomic():
        created_props = bulk_insert_properties(props)

        poi_list = []
        pred_list = []
        detail_list = []

        for prop, row in zip(created_props, rows):
            pid = prop.id
            poi_list.append(make_poi(pid, row))
            pred_list.append(make_prediction(pid, row))

            detail_list.append(HistoryTransactionDetail(
                property_id=pid,
                land_transfer_area_m2=get_value(row, "土地移轉總面積平方公尺"),
                building_transfer_area_m2=get_value(row, "建物移轉總面積平方公尺"),
                has_management=get_value(row, "有無管理組織"),
                transaction_target=get_value(row, "交易標的"),
                main_building_area=get_value(row, "主建物面積"),
            ))

        PropertyPOIFeature.objects.bulk_create(poi_list, batch_size=BATCH_SIZE)
        PropertyPredictionFeature.objects.bulk_create(pred_list, batch_size=BATCH_SIZE)
        HistoryTransactionDetail.objects.bulk_create(detail_list, batch_size=BATCH_SIZE)

def import_sinyi(path):
    print("開始匯入 信義房屋")

    df = pd.read_pickle(path)

    if "houseNo" in df.columns:
        df = df.drop_duplicates(subset=["houseNo"], keep="first")

    existing_house_nos = set(
        SinyiDetail.objects
        .exclude(house_no__isnull=True)
        .values_list("house_no", flat=True)
    )

    props = []
    rows = []
    count = 0
    skipped = 0

    for row in df.to_dict("records"):
        house_no = clean_str(get_value(row, "houseNo"))

        if house_no and house_no in existing_house_nos:
            skipped += 1
            continue

        props.append(make_property(row, "sinyi"))
        rows.append(row)

        if house_no:
            existing_house_nos.add(house_no)

        if len(props) >= BATCH_SIZE:
            save_sinyi_batch(props, rows)
            count += len(props)
            print(f"信義房屋 已匯入 {count} 筆，跳過 {skipped} 筆")
            props = []
            rows = []

    if props:
        save_sinyi_batch(props, rows)
        count += len(props)

    print(f"信義房屋 完成，共匯入 {count} 筆，跳過 {skipped} 筆")
    
def save_sinyi_batch(props, rows):
    with transaction.atomic():
        created_props = bulk_insert_properties(props)

        poi_list = []
        pred_list = []
        detail_list = []

        for prop, row in zip(created_props, rows):
            pid = prop.id

            poi_list.append(make_poi(pid, row))
            pred_list.append(make_prediction(pid, row))

            house_no = get_value(row, "houseNo")

            detail_list.append(SinyiDetail(
                property_id=pid,
                house_no=clean_str(house_no),
                name=get_value(row, "name"),
                image=get_value(row, "image"),
                large_image=get_value(row, "largeImage"),
                image_tag=get_value(row, "imageTag"),
                total_price=get_value(row, "totalPrice"),
                comm_id=get_value(row, "commId"),
                comm_name=get_value(row, "commName"),

                discount=get_value(row, "discount"),
                address=get_value(row, "address"),
                age_text=get_value(row, "age"),

                houselandtype=get_value(row, "houselandtype"),
                houselandtype_show=get_value(row, "houselandtypeShow"),

                price_first=get_value(row, "priceFirst"),
                area_land=get_value(row, "areaLand"),

                is_has_balcony=get_value(row, "isHasBalcony"),
                layout=get_value(row, "layout"),

                is_parking=clean_bool(get_value(row, "isParking")),
                parking=get_value(row, "parking"),

                tags=get_value(row, "tags"),
                three_months_clicks=get_value(row, "threeMonthsClicks") or 0,

                is_off=clean_bool(get_value(row, "isOff")),
                is_similar=clean_bool(get_value(row, "isSimilar")),
                share_url=get_value(row, "shareURL"),

                status=get_value(row, "status"),
                kind=get_value(row, "kind"),
                object_type=get_value(row, "objectType"),

                is_3dvr=clean_bool(get_value(row, "3DVR")),
                is_3dvr2=clean_bool(get_value(row, "Is3Dvr")),

                zip_code=get_value(row, "zipCode"),
                group_company=get_value(row, "groupCompany"),

                add_layout=get_value(row, "addLayout"),
                total_layout=get_value(row, "totalLayout"),

                is_has_video=clean_bool(get_value(row, "isHasVideo")),
                is_has_view=clean_bool(get_value(row, "isHasView")),

                city_name=get_value(row, "city_name"),
                city_code=get_value(row, "city_code"),

                page=get_value(row, "page"),
                source_url=get_value(row, "source_url"),
            ))

        PropertyPOIFeature.objects.bulk_create(poi_list, batch_size=BATCH_SIZE)
        PropertyPredictionFeature.objects.bulk_create(pred_list, batch_size=BATCH_SIZE)
        SinyiDetail.objects.bulk_create(detail_list, batch_size=BATCH_SIZE)
        
def import_591_existing(path):
    print("開始匯入 591 非預售")

    df = pd.read_pickle(path)

    if "post_id" in df.columns:
        df = df.drop_duplicates(subset=["post_id"], keep="first")

    existing_post_ids = set(
        House591ExistingDetail.objects
        .exclude(post_id__isnull=True)
        .values_list("post_id", flat=True)
    )

    props = []
    rows = []
    count = 0
    skipped = 0

    for row in df.to_dict("records"):
        post_id = get_value(row, "post_id")

        if post_id and post_id in existing_post_ids:
            skipped += 1
            continue

        props.append(make_property(row, "591_existing"))
        rows.append(row)

        if post_id:
            existing_post_ids.add(post_id)

        if len(props) >= BATCH_SIZE:
            save_591_existing_batch(props, rows)
            count += len(props)
            print(f"591非預售 已匯入 {count} 筆，跳過 {skipped} 筆")
            props = []
            rows = []

    if props:
        save_591_existing_batch(props, rows)
        count += len(props)

    print(f"591非預售 完成，共匯入 {count} 筆，跳過 {skipped} 筆")


def import_591_presale(path):
    print("開始匯入 591 預售")

    df = pd.read_pickle(path)

    if "hid" in df.columns:
        df = df.drop_duplicates(subset=["hid"], keep="first")

    props = []
    rows = []
    count = 0

    for row in df.to_dict("records"):
        props.append(make_property(row, "591_presale"))
        rows.append(row)

        if len(props) >= BATCH_SIZE:
            save_591_presale_batch(props, rows)
            count += len(props)
            print(f"591預售 已匯入 {count} 筆")
            props = []
            rows = []

    if props:
        save_591_presale_batch(props, rows)
        count += len(props)

    print(f"591預售 完成，共匯入 {count} 筆")


def import_history(path):
    print("開始匯入 歷史交易")

    df = pd.read_pickle(path)

    props = []
    rows = []
    count = 0

    for row in df.to_dict("records"):
        props.append(make_property(row, "history"))
        rows.append(row)

        if len(props) >= BATCH_SIZE:
            save_history_batch(props, rows)
            count += len(props)
            print(f"歷史交易 已匯入 {count} 筆")
            props = []
            rows = []

    if props:
        save_history_batch(props, rows)
        count += len(props)

    print(f"歷史交易 完成，共匯入 {count} 筆")


if __name__ == "__main__":
    # import_591_existing(r"F:/桃竹苗/final/m/591非預售.pkl")
    # import_591_presale(r"F:/桃竹苗/final/m/591預售.pkl")
    # import_history(r"F:/桃竹苗/final/m/歷史data.pkl")
    import_sinyi(r"F:/桃竹苗/final/m/信義_t3.pkl")
    
    print("全部匯入完成")