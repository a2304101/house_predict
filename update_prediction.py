import os
import math
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "final.settings")
django.setup()

from myapp.models import (
    Property,
    PropertyPredictionFeature,
    House591ExistingDetail,
    House591PresaleDetail,
)


BATCH_SIZE = 10000


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


def print_progress(title, done, total):
    if total == 0:
        percent = 100
    else:
        percent = done / total * 100

    print(f"\r{title}：{done}/{total} ({percent:.2f}%)", end="", flush=True)


def update_591_existing(path):
    print("\n開始更新 591非預售：只更新 預測_萬元坪")

    df = pd.read_pickle(path)

    if "post_id" in df.columns:
        df = df.drop_duplicates(subset=["post_id"], keep="first")

    rows_by_post_id = {}

    for row in df.to_dict("records"):
        post_id = clean(row.get("post_id"))
        if post_id is not None:
            rows_by_post_id[int(post_id)] = row

    details = House591ExistingDetail.objects.select_related(
        "property",
        "property__propertypredictionfeature"
    ).exclude(post_id__isnull=True)

    total = details.count()
    done = 0
    matched = 0
    updates = []

    for detail in details.iterator(chunk_size=BATCH_SIZE):
        done += 1

        row = rows_by_post_id.get(int(detail.post_id))
        if row:
            pred = detail.property.propertypredictionfeature
            pred.prediction_price = clean(row.get("預測_萬元坪"))
            updates.append(pred)
            matched += 1

        if len(updates) >= BATCH_SIZE:
            PropertyPredictionFeature.objects.bulk_update(
                updates,
                ["prediction_price"],
                batch_size=BATCH_SIZE
            )
            updates = []

        if done % 1000 == 0 or done == total:
            print_progress("591非預售", done, total)

    if updates:
        PropertyPredictionFeature.objects.bulk_update(
            updates,
            ["prediction_price"],
            batch_size=BATCH_SIZE
        )

    print(f"\n591非預售更新完成，匹配 {matched} 筆")


def update_591_presale(path):
    print("\n開始更新 591預售：更新 預測_萬元坪、坪數_屋齡_交互")

    df = pd.read_pickle(path)

    if "hid" in df.columns:
        df = df.drop_duplicates(subset=["hid"], keep="first")

    rows_by_hid = {}

    for row in df.to_dict("records"):
        hid = clean(row.get("hid"))
        if hid is not None:
            rows_by_hid[float(hid)] = row

    details = House591PresaleDetail.objects.select_related(
        "property",
        "property__propertypredictionfeature"
    ).exclude(hid__isnull=True)

    total = details.count()
    done = 0
    matched = 0
    updates = []

    for detail in details.iterator(chunk_size=BATCH_SIZE):
        done += 1

        row = rows_by_hid.get(float(detail.hid))
        if row:
            pred = detail.property.propertypredictionfeature
            pred.prediction_price = clean(row.get("預測_萬元坪"))
            pred.area_age_interaction = clean(row.get("坪數_屋齡_交互"))
            updates.append(pred)
            matched += 1

        if len(updates) >= BATCH_SIZE:
            PropertyPredictionFeature.objects.bulk_update(
                updates,
                ["prediction_price", "area_age_interaction"],
                batch_size=BATCH_SIZE
            )
            updates = []

        if done % 1000 == 0 or done == total:
            print_progress("591預售", done, total)

    if updates:
        PropertyPredictionFeature.objects.bulk_update(
            updates,
            ["prediction_price", "area_age_interaction"],
            batch_size=BATCH_SIZE
        )

    print(f"\n591預售更新完成，匹配 {matched} 筆")


def update_history(path):
    print("\n開始更新 歷史資料：更新 預測_萬元坪、總_編碼、坪數_屋齡_交互")

    df = pd.read_pickle(path)

    props = Property.objects.filter(
        source_type="history"
    ).select_related(
        "propertypredictionfeature"
    ).order_by("id")

    total = min(props.count(), len(df))
    done = 0
    updates = []

    records = df.to_dict("records")

    for prop, row in zip(props.iterator(chunk_size=BATCH_SIZE), records):
        done += 1

        pred = prop.propertypredictionfeature
        pred.prediction_price = clean(row.get("預測_萬元坪"))
        pred.total_encoded = clean(row.get("總_編碼"))
        pred.area_age_interaction = clean(row.get("坪數_屋齡_交互"))

        updates.append(pred)

        if len(updates) >= BATCH_SIZE:
            PropertyPredictionFeature.objects.bulk_update(
                updates,
                ["prediction_price", "total_encoded", "area_age_interaction"],
                batch_size=BATCH_SIZE
            )
            updates = []

        if done % 1000 == 0 or done == total:
            print_progress("歷史資料", done, total)

    if updates:
        PropertyPredictionFeature.objects.bulk_update(
            updates,
            ["prediction_price", "total_encoded", "area_age_interaction"],
            batch_size=BATCH_SIZE
        )

    print(f"\n歷史資料更新完成，共更新 {done} 筆")


if __name__ == "__main__":
    update_591_existing(r"F:/桃竹苗/final/m/591非預售.pkl")
    update_591_presale(r"F:/桃竹苗/final/m/591預售.pkl")
    update_history(r"F:/桃竹苗/final/m/歷史data.pkl")

    print("\n全部更新完成")