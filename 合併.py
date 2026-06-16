import pandas as pd

# 讀取檔案
df_full = pd.read_csv("乾淨地理位置_全.csv")
df_full['緯度'] = None
df_fill = pd.read_csv("f_test_7.csv")

# 只保留需要的欄位，避免重複欄位污染
fill_map = df_fill[
    ['土地位置建物門牌', '緯度', '經度']
].drop_duplicates(subset=['土地位置建物門牌'])

# merge
merged = df_full.merge(
    fill_map,
    on='土地位置建物門牌',
    how='left',
    suffixes=('', '_new')
)

merged['緯度_new'] = pd.to_numeric(
    merged['緯度_new'],
    errors='coerce'
)

merged['經度_new'] = pd.to_numeric(
    merged['經度_new'],
    errors='coerce'
)
# 只填補原本缺失的經緯度
lat_condition = (
    merged['緯度'].isna()
) | (
    merged['緯度'] == '無經緯度'
)

lon_condition = (
    merged['經度'].isna()
) | (
    merged['經度'] == '無經度'
)

merged.loc[lat_condition, '緯度'] = merged.loc[lat_condition, '緯度_new'].values
merged.loc[lon_condition, '經度'] = merged.loc[lon_condition, '經度_new'].values

# 清除暫存欄位
merged = merged.drop(columns=['緯度_new', '經度_new'])

# 輸出
merged.to_csv(
    "乾淨地理位置_全_已補經緯度.csv",
    index=False,
    encoding='utf-8-sig'
)

print("原始筆數:", len(df_full))
print("補值來源筆數:", len(fill_map))
print("輸出筆數:", len(merged))




