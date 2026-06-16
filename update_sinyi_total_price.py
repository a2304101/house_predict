import os
import math
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "final.settings")
django.setup()

from myapp.models import SinyiDetail

BATCH_SIZE = 5000


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


df = pd.read_pickle(r"F:/桃竹苗/final/m/信義_t3.pkl")
df = df.drop_duplicates(subset=["houseNo"], keep="first")

price_map = {}

for row in df.to_dict("records"):
    house_no = clean_str(row.get("houseNo"))
    if house_no:
        price_map[house_no] = clean(row.get("totalPrice"))

qs = SinyiDetail.objects.exclude(house_no__isnull=True)

updates = []
done = 0
matched = 0
total = qs.count()

for obj in qs.iterator(chunk_size=BATCH_SIZE):
    done += 1

    if obj.house_no in price_map:
        obj.total_price = price_map[obj.house_no]
        updates.append(obj)
        matched += 1

    if len(updates) >= BATCH_SIZE:
        SinyiDetail.objects.bulk_update(
            updates,
            ["total_price"],
            batch_size=BATCH_SIZE
        )
        updates = []

    if done % 1000 == 0 or done == total:
        print(f"\r更新中 {done}/{total}，匹配 {matched}", end="", flush=True)

if updates:
    SinyiDetail.objects.bulk_update(
        updates,
        ["total_price"],
        batch_size=BATCH_SIZE
    )

print(f"\n完成，匹配更新 {matched} 筆")