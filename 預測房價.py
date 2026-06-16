import unicodedata
import re
import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
root_folder = './all_merged_data'
df = pd.read_csv('/kaggle/input/datasets/saber79/new-data/all_merged_data.csv')

df['土地位置建物門牌'] = df['土地位置建物門牌'].str.replace('宜蘭縣', '宜蘭市', regex=False)
df['土地位置建物門牌'] = df['土地位置建物門牌'].str.replace('臺', '台', regex=False)
df['土地位置建物門牌'] = df['土地位置建物門牌'].str.replace('永康市', '', regex=False)

# 2. 定義中文數字對照表
chs_map = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
def parse_chs(s):
        """解析如 '二十三' 或 '十一' 的中文字"""
        if not s: return 0
        if s == '十': return 10
        if len(s) == 1: return chs_map.get(s, 0)
        if len(s) == 2:
            if s[0] == '十': return 10 + chs_map.get(s[1], 0)
            return chs_map.get(s[0], 0) * 10
        if len(s) == 3:
            return chs_map.get(s[0], 0) * 10 + chs_map.get(s[2], 0)
        return 0
    
def normalize_to_half_width(text):
    if pd.isna(text):
        return text
    # NFKC 可以將全形「１２Ｆ」轉為半形「12F」
    return unicodedata.normalize('NFKC', str(text))

# 建議針對關鍵文字欄位統一處理
cols_to_fix = ['土地位置建物門牌', '建物型態', '移轉層次', '總樓層數']
for col in cols_to_fix:
    df[col] = df[col].apply(normalize_to_half_width)

###################################################移轉層次
def extract_floor_from_address(address):
    if pd.isna(address): return None
    # 搜尋門牌中的樓層資訊，例如：十二樓、3樓、六樓之五
    match = re.search(r'([一二三四五六七八九十百\d]+)\s*[樓Ff]', str(address))
    if match:
        return match.group(1) + '層' # 補上「層」字以符合原本的格式
    return None

# 針對移轉層次缺失的列，從門牌嘗試補回
mask = df['移轉層次'].isna()
df.loc[mask, '移轉層次'] = df.loc[mask, '土地位置建物門牌'].apply(extract_floor_from_address)

def final_impute_transfer_level(row):
    # 如果已經有提取到樓層，就維持原狀
    if pd.notna(row['移轉層次']):
        return row['移轉層次']
    b_type = str(row['建物型態'])
    # 針對公寓補 3 樓
    if '公寓' in b_type:
        return '三層'
    # 針對華廈與大樓，若有總樓層則取一半，否則補 4 樓
    if '華廈' in b_type or '住宅大樓' in b_type:
        # 假設總樓層數已經轉為數字，否則簡單補四層
        return '四層'
    # 其餘補一層 (店面或地坪交易機率高)
    return '一層'

# 執行最終補值
df.loc[df['移轉層次'].isna(), '移轉層次'] = df[df['移轉層次'].isna()].apply(final_impute_transfer_level, axis=1)

def transfer_level_to_int(text):
    if pd.isna(text) or str(text).lower() == 'nan':
        return np.nan

    # 1. 基礎清理：轉半形、移除空格與雜訊字眼
    # 移除如「陽台、騎樓、電梯樓梯間、見其他登記事項」等不影響高度的字眼
    text = str(text).replace(' ', '')
    noise = ['陽台', '陽臺', '騎樓', '走廊', '電梯樓梯間', '見其他登記事項', 
             '平台', '露台', '通道', '門廳', '屋頂突出物', '夾層', '見使用執照', '停車場']
    for n in noise:
        text = text.replace(n, '')
    text = text.strip(',')
    
    if text == '全' or text == '整棟' or text == '一棟':
        return 1  # 「全」或整棟通常從 1 樓開始算
        
    if text == '地下層':
        return -1
        
    if text == '':
        return np.nan
        
    # 3. 提取所有樓層數字
    floors_raw = re.findall(r'(地下)?([一二三四五六七八九十百\d]+)', text)
    
    results_ground = []
    results_basement = []
    
    for prefix, f_str in floors_raw:
        val = parse_chs(f_str) if not f_str.isdigit() else int(f_str)
        if prefix == '地下' or 'B' in text.upper():
            results_basement.append(val * -1)
        else:
            results_ground.append(val)
            
    # 4. 終極邏輯判定
    if results_ground:
        # 如果有地上層，不論有沒有地下層，都取地上層的最高樓
        # 因為價值核心在地上（特別是一樓或高樓層景觀）
        return max(results_ground)
    elif results_basement:
        # 只有地下層時，才回傳負值（取最靠近地面的，如 -1 比 -3 貴）
        return max(results_basement)

# 執行轉換
df['移轉層次'] = df['移轉層次'].apply(transfer_level_to_int)
###################################################總樓層數
def normalize_total_floor(x):
    # 1. 處理基礎空值與型別轉換
    if pd.isna(x) or x is None or x=='0':
        return np.nan
    s = str(x).strip().replace('層', '') # 移除「層」字

    # 2. 處理異常雜訊：將不具意義的字串轉為 NaN
    # 如 '見其他登記事項', '000', '社登', '0', '(空白)', '00Z' 等
    noise_patterns = ['見其他登記事項', '社登', '空白', '00Z', '00Y','099','000','(空白)','nan',]
    if any(p in s for p in noise_patterns) or s == '':
        return np.nan

    # 4. 執行轉換邏輯
    if s.isdigit():
        return int(s)
    else:
        # 使用正則提取中文字部分
        match = re.search(r'([一二三四五六七八九十百]+)', s)
        if match:
            return parse_chs(match.group(1)) 

# 執行轉換
df['總樓層數'] = df['總樓層數'].apply(normalize_total_floor)

def impute_total_floors(row):
# 假設 transfer_level_int 是你之前轉好的數字
    level = row['移轉層次'] 
    b_type = str(row['建物型態'])
    # 基本邏輯補值
    if '公寓' in b_type:
        val = 5
    elif '透天' in b_type:
        val = 3
    elif '華廈' in b_type:
        val = 7
    elif '住宅大樓' in b_type:
        val = 14
    elif '套房' in b_type:
        val = 12  
    elif '其他' in b_type:
        val = 2      
    else:
        val = 4 # 預設值
        
    # 確保總樓層不會低於移轉層次
    if pd.notna(level) and level > val:
        return int(level)
    return val

mask = df['總樓層數'].isna()
df.loc[mask, '總樓層數'] = df[mask].apply(impute_total_floors, axis=1)
#############################################################補移轉層次 見其他登記事項
def fix_missing_level_with_total_floor(row):
    level_text = row['移轉層次']
    total_floor = row['總樓層數'] # 假設已轉為數字

    # 判斷是否為「見其他登記事項」或空值
    if pd.isna(level_text):
        if pd.notna(total_floor) and total_floor > 0:
            # 取總樓層的 60% 位置，並四捨五入
            inferred_level = round(total_floor * 0.6)
            return inferred_level
        else:
            return np.nan        
    # 如果已有數字或正常中文，則回傳原始值（交給後續轉換函式）
    return level_text
df['移轉層次'] = df.apply(fix_missing_level_with_total_floor, axis=1)    
#############################################################非預售屋
# 定義各區域的合理邊界
def filter_price(row):
    city = row['縣市']
    price = row['單價_萬元坪']
    if city == '台北市':
        return 20 <= price <= 250  # 台北市低於 20 萬極少見
    elif city in ['新北市', '新竹縣', '新竹市', '台中市']:
        return 10 <= price <= 150
    else:
        return 5 <= price <= 100   # 其他縣市 5 萬是底線
mask = df.apply(filter_price, axis=1)
df = df[mask]    

#df = df[df['is_presale'] == 0]
#df = df[df['縣市']=='台北市']
#df = df[df['單價_萬元坪']<125]
#df = df[df['成交年'] >= 2023]
#根據各區的平均單價進行排序與分組
dist_rank = df.groupby('完整行政區')['單價_萬元坪'].mean().sort_values(ascending=False)
# 使用 qcut 將行政區分為 5 個等級 (0是最高價, 4是最低價)
df['行政區等級'] = pd.qcut(dist_rank, 5, labels=False).reindex(df['完整行政區']).values

# 類別特徵只保留基數合理的
cat_features = ['完整行政區', '建物型態','行政區等級']
for col in cat_features:
    df[col] = df[col].astype('category')


# 計算每個行政區在不同年份的平均單價 (比起按月，按年更穩定且類別少)
region_year_map = df.groupby(['完整行政區', '成交年'])['單價_萬元坪'].mean()
# 將均價映射回原資料，作為「區域年度基準價」
df['區域年度基準價'] = df.set_index(['完整行政區', '成交年']).index.map(region_year_map)

# 使用「行政區等級」與「交易距今月數」的乘積
# 行政區等級 (1-5) 乘上 月數 (1-180)
# 這是一個數值特徵，類別數為 0，但能學到：高價區隨時間增加的幅度
df['區級_時間_加權'] = (df['行政區等級'].astype(int) + 1) * df['交易距今月數']

new_features = [
    '行政區等級',        # 類別 (5類) -> 區分精華/郊區
    #'區域年度基準價',     # 數值 -> 提供該區當年的價格天花板
    #'區域半年移動均價',   # 數值 -> 提供市場動能
    #'區級_時間_加權'      # 數值 -> 模擬不同等級區域的時間成長曲線
]#未加


# 3. 定義標籤 (Label) 與特徵 (Features)
# 對單價做 Log 轉換，讓模型更好學
features = ['交易距今月數','成交月','完整行政區','縣市', '屋齡', '建物型態','建案名稱','坪數','is_presale','age_was_missing']+new_features
#已忽略 '建案名稱_編碼'
#target_map_project = df.groupby('建案名稱')['單價_萬元坪'].mean()
#df['建案名稱_編碼'] = df['建案名稱'].map(target_map_project)

y = np.log1p(df['單價_萬元坪']) 

X = df[features]# 這裡 X 就會包含 '建案名稱' 了
tscv = TimeSeriesSplit(n_splits=5)
cv_models = []
best_iterations = []
oof_errors = []
params = {
        'objective': 'regression', # 回歸任務：預測數值
        'metric': ['rmse', 'mae'], # 同時追蹤兩個指標
        'boosting_type': 'gbdt',   # 提升樹類型 gbdt dart
        'min_data_in_leaf': 50,       # 每個葉子至少要有 100 筆資料，強迫模型找通用規律
        'max_depth': 7,             # 限制深度，防止死背資料
        'learning_rate': 0.05,     # 學習率，越小通常越準但跑越久
        'num_leaves': 64,          # 樹的葉子數，控制複雜度
        'min_child_samples': 30,   # 讓模型敢於學更細的規律
        'lambda_l1': 10.0 ,         # 加入 L1 正規化，減少過擬合
        'lambda_l2': 5,            # 加入 L2 正規化
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'device': 'gpu',           # 啟用 RTX 5070 加速
        'gpu_device_id': 0,        # 指定第一張顯卡
        'verbosity': -1            # 減少多餘的日誌輸出
}

print("開始執行 5-Fold 交叉驗證訓練...")

def extract_section_name(row): 
    address = str(row['土地位置建物門牌'])
    city = str(row['縣市']) if pd.notna(row['縣市']) else ""
    dist = str(row['鄉鎮市區']) if pd.notna(row['鄉鎮市區']) else ""
    city_dist = city + "_" + dist
    # 1. 徹底清洗
    # clean_addr = re.sub(f"^{city}", "", address)
    # clean_addr = re.sub(f"^{dist}", "", clean_addr)
    # --- 強化版清洗階段 ---
    clean_addr = address
    # 使用 while 迴圈確保「完全移除」開頭所有重複的縣市與行政區名稱
    # 這樣即便出現「桃園市觀音區桃園市觀音區...」，也會被剝到剩下核心地址
    while True:
        prev_addr = clean_addr
        if city and clean_addr.startswith(city):
            clean_addr = clean_addr[len(city):].strip()
        if dist and clean_addr.startswith(dist):
            clean_addr = clean_addr[len(dist):].strip()

        # 如果這一輪沒有任何變化，代表已經剝乾淨了
        if clean_addr == prev_addr:
            break
    clean_addr = re.sub(r'\d+鄰', '', clean_addr)
    #clean_addr = re.sub(r'^[^路街]+?里(?![路街])', '', clean_addr)
    clean_addr = clean_addr.strip()
    # ---------------------
    # 2. 優先級 1：修正後的路段抓取邏輯
    # 重點：將 '.+?段' 放在前面，確保「段」不會被後面的「路/街」攔截
    #m = re.search(r'(.+?段|.+?(?:路|街|大道|園區|縣道))', clean_addr)
    #m = re.search(r'(.+?路[\d一二三四五六七八九十]+段|.+?段|.+?(?:大道|園區|縣道)|.+?(?:路|街))', clean_addr)
    m = re.search(r'(.+?路[\d一二三四五六七八九十]+段|.+?段|.+?(?:大道|園區|縣道)|.+?[路街])', clean_addr)
    if m:
        target = re.sub(r'^.+?[村里]', '', m.group(1)) # 剝離路名前的村里
        return city_dist + "_" + target
    # 3. 優先級 2：巷、弄
    m = re.search(r'(.+?(?:巷|弄))', clean_addr)
    if m: 
        target = re.sub(r'^.+?[村里]', '', m.group(1)) # 剝離巷弄前的村里
        return city_dist + "_" + m.group(1)

    # --- 新增階段 ---
    # 4. 優先級 2.5：村、里 (針對無路名地區，如：士林里15號)
    # 使用負向先行斷言 (?![路街]) 確保這個「里」不是「里路」或「里街」的一部分
    #m = re.search(r'(.+?[村里](?![路街]))', clean_addr)
    m = re.search(r'(.+?[村里])', clean_addr)
    if m:
        return city_dist + "_" + m.group(1)
    # ----------------
    # 4. 優先級 3：社區名或聚落地名
    # 抓取「號」、「地號」或「第一個數字」之前的純中文部分
    m = re.search(r'^([^\d地號]+)', clean_addr)
    if m and m.group(1).strip():
        return city_dist + "_" + m.group(1).strip()
        
    # 5. 優先級 4：保底機制
    # 如果剩下的是數字或地號，直接回傳行政區加上標籤
    if re.search(r'\d+', clean_addr) or '地號' in clean_addr:
        return city_dist + "_區域內地號或門牌"

    return None

# 執行提取
df['唯一地理位置'] = df.apply(extract_section_name, axis=1)
# 觀察結果

print(df[['土地位置建物門牌', '唯一地理位置']])