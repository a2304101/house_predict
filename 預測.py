#預測
import pickle
import lightgbm as lgb
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
# 1. 讀取模型與對照表
model = lgb.Booster(model_file=r'F:/桃竹苗/final/m/lgb_final_full_model.txt')
with open(r'F:/桃竹苗/final/m/encoding_assets.pkl', 'rb') as f:
    assets = pickle.load(f)

# 2. 重新定義預測用的編碼函數 (直接引用讀入的 assets)
def get_prediction_encoded_values(df_subset,assets):
    # 基礎映射
    p_val = df_subset['建案名稱'].map(assets['proj_map'])
    g_val = df_subset['唯一地理位置'].map(assets['geo_map'])
    d_val = df_subset['完整行政區'].map(assets['dist_map'])
    c_val = df_subset['縣市'].map(assets['city_map'])
    # 獲取訓練集中的樣本數 (關鍵！)
    
    p_cnt = df_subset['建案名稱'].map(assets['proj_counts']).fillna(0)
    g_cnt = df_subset['唯一地理位置'].map(assets['geo_counts']).fillna(0)

    # 執行層級降級邏輯 (門檻與訓練時一致)
    g_val_fixed = np.where(g_cnt <= 15, d_val, g_val)
    p_val_fixed = np.where(p_cnt <= 15, g_val_fixed, p_val)

    # 分流邏輯
    presale_logic = d_val.fillna(c_val) # 依你原本程式碼的邏輯
    house_logic = pd.Series(g_val_fixed).fillna(d_val).fillna(c_val)
    return np.where(df_subset['is_presale'] == 1, presale_logic, house_logic)
#########
def get_area_price_feature(df_to_predict, assets):
    """
    根據 time_index 搜尋：
    1. 找到完全一樣的 time_index -> 使用該月的 area_last_month_price
    2. 若找不到或 time_index 更大 -> 往後找最近（且小於）的資料
    """
    # 1. 取得對照表並確保排序（merge_asof 的必要條件）
    market_df = assets['historical_area_market'].copy()
    market_df['完整行政區'] = market_df['完整行政區'].replace({'宜蘭市':'宜蘭縣'}, regex=True)
    market_df['縣市'] = market_df['完整行政區'].apply(lambda x: x.split('_')[0])
    city_market = market_df.groupby(['縣市', 'time_index'])['area_last_month_price'].mean().reset_index()
    city_market['time_index']=city_market['time_index'].astype(int)
    lookup_table = market_df[['完整行政區', 'time_index', 'area_last_month_price']].copy()
    lookup_table['完整行政區'] = lookup_table['完整行政區'].astype(str)
    lookup_table['time_index'] = lookup_table['time_index'].astype(int)
    lookup_table = lookup_table.sort_values('time_index')
    # 2. 確保待預測資料也有排序（為了對齊，完成後會換回原順序）
    df_to_predict = df_to_predict.reset_index() # 紀錄原始順序
    df_temp = df_to_predict[['index', '完整行政區', 'time_index']].copy()
    df_temp['完整行政區'] = df_temp['完整行政區'].astype(str)
    df_temp['縣市'] = df_temp['完整行政區'].apply(lambda x: x.split('_')[0])
    df_temp = df_temp.sort_values('time_index')
    # 3. 執行核心邏輯：向後搜尋 (direction='backward')
    # by='完整行政區'：保證只在同行政區內找，不會跨區
    # direction='backward'：找「相同」或「最近但較小」的值
    res = pd.merge_asof(
        df_temp, 
        lookup_table, 
        on='time_index', 
        by='完整行政區', 
        direction='backward'
    )
    # 如果真的太舊（舊到對照表還沒開始），用該區第一筆資料保底
    if res['area_last_month_price'].isnull().any():
        earliest_map = market_df.sort_values('time_index').groupby('完整行政區')['area_last_month_price'].first().to_dict()
        res['area_last_month_price'] = res['area_last_month_price'].fillna(res['完整行政區'].astype(str).map(earliest_map))
    # 4. 第二次合併：針對剩餘的 NaN，用縣市級資料補齊
    # 這裡我們挑出第一次合併失敗的列，再做一次 merge_asof
    missing_mask = res['area_last_month_price'].isna()
    if missing_mask.any():
        # 把缺漏的部分拿出來
        df_missing = res.loc[missing_mask, ['index', '縣市', 'time_index']]
        # 對縣市做 merge_asof
        res_city = pd.merge_asof(
            df_missing.sort_values('time_index'),
            city_market.sort_values('time_index'),
            on='time_index', by='縣市', direction='backward'
        )    
        # 將補好的值填回原本的 res
        mapping = res_city.set_index('index')['area_last_month_price']
        res.loc[missing_mask, 'area_last_month_price'] = res['index'].map(mapping)  
    # 4. 回復原始資料順序並回傳結果
    res = res.sort_values('index').set_index('index')
    return res['area_last_month_price']
########
# 3. 對新資料進行特徵工程 (比照訓練過程)
# 假設 new_data 是你要預測的 DataFrame
features = ['縣市','鄉鎮市區','交易距今月數','成交年','成交月','完整行政區', '屋齡', '建物型態',
            '建案名稱','坪數','移轉層次', '總樓層數','area_last_month_price',
            '電梯','唯一地理位置','is_presale','age_was_missing','主建物坪數',
           'time_index', '緯度', '經度',
           'poi_convenience_count_300m', 'poi_convenience_count_500m',
           'poi_bank_count_500m', 'poi_food_count_300m', 'poi_food_count_500m',
           'poi_medical_count_500m', 'poi_parking_count_500m',
           'distance_to_nearest_worship_m', 'distance_to_thsr_m',
           'distance_to_tra_m', 'distance_to_mrt_m']+['總_編碼', '坪數_屋齡_交互']
#new_data=X.copy()
# new_data['area_last_month_price'] = get_area_price_feature(new_data, assets)
# new_data['總_編碼'] = np.log1p(get_prediction_encoded_values(new_data))
#new_data['土地持分率'] = new_data['土地移轉總面積平方公尺'] / (new_data['坪數'] + 1e-9)
#new_data['坪數_屋齡_交互'] = new_data['坪數'] * new_data['屋齡']

# 4. 記得移除字串欄位，否則模型會報錯
#X_test = new_data.drop(columns=['建案名稱', '唯一地理位置'])
a=pd.read_csv(r'F:/桃竹苗/final/m/591_housing_data_nopre2_t3_features.csv')
a['area_last_month_price'] = get_area_price_feature(a, assets)
a['總_編碼'] = np.log1p(get_prediction_encoded_values(a, assets))
a['坪數_屋齡_交互'] = a['坪數'] * a['屋齡']

X_test = a[model.feature_name()]
# 5. 進行預測並還原 log
###############
X_test = X_test.copy(deep=True)
# 其他 dtype 同步
saved_dtypes = pd.read_pickle(r'F:/桃竹苗/final/m/feature_dtypes.pkl')
# for col in X_all_train.columns:
#     if col not in ['縣市','鄉鎮市區','完整行政區', '建物型態']:
#         X_test[col] = X_test[col].astype(X_all_train[col].dtype)
for col, dtype_name in saved_dtypes.items():
    if col in X_test.columns:
        if col not in ['縣市','鄉鎮市區','完整行政區', '建物型態']:
            X_test.loc[:, col] = X_test[col].astype(dtype_name)         
label_encoders = pd.read_pickle(r'F:/桃竹苗/final/m/label_encoders.pkl')
X_test['完整行政區'] = X_test['完整行政區'].replace({'宜蘭縣':'宜蘭市'}, regex=True)
for col in ['縣市','鄉鎮市區','完整行政區', '建物型態']:
    X_test[col] = X_test[col].map(label_encoders[col]).fillna(-1).astype('int32') 
    
#X_test = X_test[X_all_train.columns]
#X_test = X_test[model.feature_name()]
#print(X_test.dtypes[['完整行政區','建物型態']])
#print(X_test.select_dtypes(include='category').columns.tolist())
################
final_preds = np.expm1(model.predict(X_test))
####################################
y = np.log1p(a['單價_萬元坪']) 
####################################
 # 【關鍵修改 2】：計算訓練集 MAE
train_preds = final_preds 
train_mae = mean_absolute_error(np.expm1(y), train_preds)
# 計算驗證集 MAE
mape = np.mean(np.abs((np.expm1(y) - train_preds) / (np.expm1(y)+ 1e-9))) * 100
print(f"訓練百分比誤差: {mape:.2f}%")
print(f"Train MAE: Fold  MAE: {train_mae:.4f} 萬元")
##############################################################
full_train_preds_log=np.log1p(final_preds)
full_train_preds_real = np.expm1(full_train_preds_log)
y_all_real = np.expm1(y)a
full_l1_log = mean_absolute_error(y, full_train_preds_log)

# 真實價格空間的指標
full_mae_real = mean_absolute_error(y_all_real, full_train_preds_real)
full_mse_real = mean_squared_error(y_all_real, full_train_preds_real)
full_rmse_real = np.sqrt(full_mse_real)
# 訓練百分比誤差 (MAPE)
full_mape = np.mean(np.abs((y_all_real - full_train_preds_real) / (y_all_real + 1e-9))) * 100

print("\n" + "="*40)
print("🎯 全數據總訓練 - 最終評估報告")
print("-" * 40)
print(f"Log 空間 MAE (train's l1): {full_l1_log:.6f}")
print(f"訓練百分比誤差 (MAPE):    {full_mape:.2f}%")
print("-" * 40)
print(f"真實房價 MAE:  {full_mae_real:.4f} 萬元")
print(f"真實房價 RMSE: {full_rmse_real:.4f} 萬元")
print(f"真實房價 MSE:  {full_mse_real:.2f}")
print("="*40)
# 提示：如果你的 MAPE 低於之前 5-Fold 的平均值，代表模型對歷史數據抓得很牢