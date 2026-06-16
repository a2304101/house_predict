import pandas as pd
from sqlalchemy import create_engine
import numpy as np
# 建立 SQLAlchemy 連線 (填入你 settings 的 MySQL 設定)
engine = create_engine("mysql+pymysql://newuser:@localhost:8888/final_h?charset=utf8mb4")


print("⏳ 正在匯入 591 非預售屋資料...")
df_existing = pd.read_pickle(r'F:/桃竹苗/final/m/591非預售.pkl')

cols_to_drop = [c for c in ['土地2', '土2'] if c in df_existing.columns]
df_existing = df_existing.drop(columns=cols_to_drop)
# 倒進剛剛用 Django 建好的 table 'house_591_existing'
df_existing = df_existing.where(pd.notnull(df_existing), None)

df_existing['post_id'] = pd.to_numeric(df_existing['post_id'],errors='coerce').astype('Int64')
existing_ids = set(pd.read_sql("SELECT post_id FROM house_591_existing",engine)['post_id'])
df_existing = (df_existing.drop_duplicates(subset=['post_id']))
df_existing = df_existing[~df_existing['post_id'].isin(existing_ids)]

df_existing.to_sql('house_591_existing', con=engine, if_exists='append', index=False, chunksize=5000)


print("⏳ 正在匯入 591 預售屋資料...")
df_presale = pd.read_pickle(r'F:/桃竹苗/final/m/591預售.pkl')
df_presale = df_presale.where(pd.notnull(df_presale), None)

df_presale['hid'] = pd.to_numeric(df_presale['hid'],errors='coerce').astype('Int64')
presale_ids = set(pd.read_sql("SELECT hid FROM house_591_presale",engine)['hid'])
df_presale = (df_presale.drop_duplicates(subset=['hid']))
df_presale = df_presale[~df_presale['hid'].isin(presale_ids)]

df_presale.to_sql('house_591_presale', con=engine, if_exists='append', index=False, chunksize=5000)


print("⏳ 正在匯入 舊歷史實價登錄資料...")
df_history = pd.read_pickle(r'F:/桃竹苗/final/m/歷史data.pkl')
df_history = df_history.where(pd.notnull(df_history), None)
df_history.to_sql('house_history_transaction', con=engine, if_exists='append', index=False, chunksize=5000)

print("🎉 全部資料已成功分區安全匯入 final_h 資料庫！")