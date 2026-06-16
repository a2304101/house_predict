import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error

# 建立儲存模型的資料夾
if not os.path.exists('saved_models'):
    os.makedirs('saved_models')
    
# 1. 讀取與基本清理
root_folder = './house'
df = pd.read_csv(f'{root_folder}/all_merged_data.csv')

# 確保時間排序 (這對預測未來非常重要)
df = df.sort_values(['成交年', '成交月']).reset_index(drop=True)

# 2. 預處理：類別型特徵轉型
cat_features = ['鄉鎮市區', '建物型態', '建案名稱']
for col in cat_features:
    df[col] = df[col].astype('category')

# 3. 定義標籤 (Label) 與特徵 (Features)
# 對單價做 Log 轉換，讓模型更好學
y = np.log1p(df['單價_萬元坪']) 
X = df.drop(columns=['單價_萬元坪']) # 移除目標值，剩下的都是特徵


#df.to_csv(f'{root_folder}/11501_all_districts_merged_a_test.csv', index=False, encoding='utf-8-sig')

# 假設 X 是按時間（年、月）排序好的 89 萬筆資料
# n_splits=5 代表我們會切 5 份來進行輪流測試
# 使用 TimeSeriesSplit (時間序列分割)，確保模型是用「110-113年」預測「114年」，而非隨機亂跳
# --- 3. 設定交叉驗證機制 ---
# --- 3. 階段一：分組賽 (5-Fold CV) ---
tscv = TimeSeriesSplit(n_splits=5)
cv_models = []
best_iterations = []
oof_errors = []


# 這裡展示每一折(Fold)是如何拿資料的
# for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
#     # train_idx: 這是「過去」的資料索引（訓練集）
#     # val_idx: 這是緊接著訓練集之後的「未來」資料索引（驗證集）
#     X_train = X.iloc[train_idx]
#     X_val = X.iloc[val_idx]
#     print(f"第 {fold+1} 折:")
#     print(f"  訓練集筆數: {len(X_train)} (包含從索引 {train_idx[0]} 到 {train_idx[-1]})")
#     print(f"  驗證集筆數: {len(X_val)} (包含從索引 {val_idx[0]} 到 {val_idx[-1]})")

# --- 4. 訓練迴圈 ---
params = {
        'objective': 'regression', # 回歸任務：預測數值
        'metric': 'rmse',         # 評估指標：均方根誤差
        'boosting_type': 'gbdt',   # 提升樹類型
        'learning_rate': 0.03,     # 學習率，越小通常越準但跑越久
        'num_leaves': 63,          # 樹的葉子數，控制複雜度
        'device': 'gpu',           # 啟用 RTX 5070 加速
        'gpu_device_id': 0,        # 指定第一張顯卡
        'verbosity': -1  ,          # 減少多餘的日誌輸出
        'max_bin': 255              # 【核心修正】強制限制 Bin 數量，解決 GPU 報錯
}

print("開始執行 5-Fold 交叉驗證訓練...")
print("--- 正在執行分組賽 (5-Fold CV) ---")
for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    # 建立資料集
    dtrain = lgb.Dataset(X_tr, label=y_tr, categorical_feature=cat_features)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain, categorical_feature=cat_features)
    
    # 訓練
    m = lgb.train(
        params, 
        dtrain, 
        valid_sets=[dval], 
        num_boost_round=1000, 
        callbacks=[lgb.early_stopping(50)]
    )
    
    # 【存檔】儲存分組模型 (使用 LightGBM 內建格式，效率最高)
    model_filename = f'saved_models/lgb_fold_{fold+1}.txt'
    m.save_model(model_filename)
    print(f"Fold {fold+1} 模型已儲存至: {model_filename}")
    
    cv_models.append(m)
    best_iterations.append(m.best_iteration)
    
    preds = np.expm1(m.predict(X_val))
    error=mean_absolute_error(np.expm1(y_val), preds)
    oof_errors.append(error)
    print(f"Fold {fold+1} MAE: {error:.4f} 萬元")

# --- 4. 階段二：正規賽 (Full Training) --- 
print("\n--- 正規賽：全量訓練 ---")  
avg_iter = int(np.mean(best_iterations))
full_train_data = lgb.Dataset(X, label=y, categorical_feature=cat_features)

# 最終大模型
final_model = lgb.train(params, full_train_data, num_boost_round=avg_iter)  

# 【存檔】儲存最終大模型
final_model_path = 'saved_models/lgb_final_full_model.txt'
final_model.save_model(final_model_path)
print(f"最終大模型已儲存至: {final_model_path}")


# --- 5. 整合預測函數 ---
def predict_115_price(new_data):
    """
    這個函數展示了未來如何直接從硬碟讀取模型，不必重新訓練
    """
    all_preds = []
    
    # 載入 5 個分組模型
    for i in range(1, 6):
        m = lgb.Booster(model_file=f'saved_models/lgb_fold_{i}.txt')
        all_preds.append(np.expm1(m.predict(new_data)))
    
    # 載入最終大模型
    m_final = lgb.Booster(model_file='saved_models/lgb_final_full_model.txt')
    final_p = np.expm1(m_final.predict(new_data))
    
    # 整合輸出
    return (np.mean(all_preds, axis=0) + final_p) / 2

print("\n所有模型已完成訓練與存檔。")