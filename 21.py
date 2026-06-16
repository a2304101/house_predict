import os
import pandas as pd
import numpy as np
#aa=0
o1=0
o2=0
bad_lines_list = []
def collect_bad_lines(line):
    bad_lines_list.append(line)
    return None  # 回傳 None 表示跳過該行，不讀入 df

def forecast_ready_cleaning_with_tracking(file_path):
    global o1, o2
    print(f"--- 啟動深度清洗與預測特徵提取: {file_path} ---")
    
    # 【第一步：讀取資料】
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=[1],on_bad_lines=collect_bad_lines,engine='python')
    except:
        df = pd.read_csv(file_path, encoding='cp950', skiprows=[1],encoding_errors='ignore',on_bad_lines=collect_bad_lines,engine='python')
    
    # 補齊 A 檔缺失的預售屋特有欄位
    #print(df.columns)
    
    city_map = {
    'A': '台北市', 'B': '台中市', 'C': '基隆市', 'D': '台南市',
    'E': '高雄市','F': '新北市', 'G': '宜蘭市', 'H': '桃園市', 
    'I': '嘉義市','J': '新竹縣', 'K': '苗栗縣', 'M': '南投縣', 
    'N': '彰化縣', 'O': '新竹市', 'P': '雲林縣', 'Q': '嘉義縣',
    'T': '屏東縣','U': '花蓮縣','V': '台東縣', 'W': '金門縣', 'X': '澎湖縣', 'Z': '連江縣'}
    file_name = os.path.basename(file_path)
    city_code = file_name[0].upper()  # 取得首字母 A-Z
    df['縣市']=city_map[city_code]
    df['完整行政區'] = df['縣市'] + "_" + df['鄉鎮市區'].astype(str)
    
    if '建案名稱' not in df.columns:
        file_type = 'A'
        df['建案名稱'] = '一般成屋' # 預設為一般成屋，因為 A 檔沒有建案名稱欄位
        df['age_was_missing'] = df['建築完成年月'].isna().astype(int)
    # 補齊 B 檔缺失的成屋特有欄位
    else:
        file_type = 'B' # 這裡一定要加這行！
        df['建築完成年月'] = None
        df['is_presale'] = 1  
        df['age_was_missing'] = 1
        df['屋齡'] = -2
        # 預售屋習慣剔除解約資料
        if '解約情形' in df.columns:
            df = df[df['解約情形'].isna()]
            
    # 移除欄位名稱可能的空格
    df.columns = df.columns.str.strip()
    print(f"0. 原始總筆數: {len(df)} 筆")
    o1+=len(df)
    # 【第二步：時間格式轉換 (拆分年月 與 屋齡計算)】
    def parse_year_month(date_val):
        try:
            val = str(int(date_val))
            m_year = int(val[:-4]) + 1911 # 西元化
            month = int(val[-4:-2])
            return m_year, month
        except:
            return None, None

    def parse_construction_year(date_val):
        try:
            val = str(int(date_val))
            # 取得完工民國年並轉西元
            tw_year = int(val[:-4]) if len(val) >= 5 else int(val[:-2])
            return tw_year + 1911
        except:
            return None
    def parse_year_month(date_val):
        try:
            val = str(int(date_val))
            # 判斷是 7 位數 (1050520) 還是 6 位數 (981201)
            if len(val) == 7:
                year = int(val[:3]) + 1911
                month = int(val[3:5])
                day = int(val[5:])
            elif len(val) == 6:
                year = int(val[:2]) + 1911
                month = int(val[2:4])
                day = int(val[4:])
            else:
                return None, None , pd.NaT
            return year, month ,pd.Timestamp(year=year, month=month, day=day)
        except:
            return None, None,pd.NaT    

    # 1. 拆分成交年、成交月
    df[['成交年', '成交月', 'tmp_date']] = df['交易年月日'].apply(lambda x: pd.Series(parse_year_month(x)))
    #新增「交易距今月數」特徵
    df = df.dropna(subset=['tmp_date'])
    df['交易距今月數'] = (df['tmp_date'].dt.year - 2011) * 12 + df['tmp_date'].dt.month
    df = df.drop(columns=['tmp_date'])
    
    # 2. 處理完工年
    df['完工年'] = df['建築完成年月'].apply(parse_construction_year) 
    
    #print(df['建築完成年月'].isna().sum(), "筆建築完成年月缺失")
    # 3. 處理屋齡：使用「成交年」減去「完工年」，反映交易當下的真實屋齡
    if file_type == 'A':
        df['屋齡'] = df['成交年'] - df['完工年']
        
        # 4. 預售屋處理：屋齡若為負數（預售中）設為 0
        #df.loc[df['屋齡'] < 0, '屋齡'] = 0
        df['is_presale'] = (df['屋齡'] < 0).astype(int)
        
        # 5. 補值策略：
        # 為了避免預售屋的負值拉低中位數，導致老屋被補成「年輕屋」
        # 我們在計算中位數時，先排除負值 (只計算 >= 0 的部分)
        df['屋齡'] = df.groupby(['鄉鎮市區', '建物型態'])['屋齡'].transform(lambda x: x.fillna(x[x >= 0].median()))
        
        # 若該區完全沒資料，同樣補正數的中位數
        df['屋齡'] = df['屋齡'].fillna(df[df['屋齡'] >= 0]['屋齡'].median())
        
    # 6. 剔除無法解析成交時間的資料
    df = df.dropna(subset=['成交年', '成交月'])
    
    print(f"1. 時間與屋齡處理完成，成交年範圍: {int(df['成交年'].min())} - {int(df['成交年'].max())}")
    print(f"1. 時間與屋齡處理完成，剩餘: {len(df)} 筆")

    # 數值標準化
    cols_to_fix = ['總價元', '車位總價元', '單價元平方公尺', '建物移轉總面積平方公尺', '車位移轉總面積平方公尺']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 【第三步：車位去噪與單價換算】
    def get_net_unit_price(row):   
        if row['車位總價元'] > 0 and (row['建物移轉總面積平方公尺'] - row['車位移轉總面積平方公尺']) > 0:
            return (row['總價元'] - row['車位總價元']) / (row['建物移轉總面積平方公尺'] - row['車位移轉總面積平方公尺'])
        
        elif "車位0" not in str(row['交易筆棟數']) and row['車位總價元'] == 0:
            return None 
        
        return row['單價元平方公尺']
    #print(df['主要用途'].unique())
    df['淨單價_平米'] = df.apply(get_net_unit_price, axis=1)
    df = df.dropna(subset=['淨單價_平米'])
    df['單價_萬元坪'] = (df['淨單價_平米'] * 3.3058) / 10000
    df['坪數'] = df['建物移轉總面積平方公尺'] * 0.3025
    print(f"2. 車位去噪完成，剩餘: {len(df)} 筆")

    # 【第四步：備註噪音過濾】
    # --- 安全防護動作 ---
    # 2. 強制轉成字串，並把 NaN 轉成空字串
    #if '備註' in df.columns:
    df['備註'] = df['備註'].astype(str).replace('nan', '')
    
    noise_keywords = ['更名', '總價款不變', '二親等', '親友', '關係人', '員工', '信託', '分件登記', 
    '協議價購','僅車位交易', '地上權', '公共設施', '道路用地', '地清', 
    '未辦繼承', '判決', '未登記建物', '無水', '無電', '讓渡', '判決共有分割','瑕疵',
    '農作物', '農地', '農業設施', '格局不明', '標讓售','毗連耕地','多數決', '畸零地', '合併使用',
    '無權占用','承購', '滅失', '借名登記','交通用地', '權利轉售', '解約', '農舍', '私設通路',
    '滲漏水', '不負修繕責任','申報書序號','排除侵害','公同共有','事故屋','私設道路','加油站',
    '換約','親屬','氯離子','減少價金','特殊關係','共有人','二等親','關係人間','調解','和解',
    '拍賣','標售','預售屋權利','換約','平轉','非自然身故','海砂屋','輻射屋','權利買賣']
    pre_sale_noise = [
    '百億分之', '無法輸入', '分割後移轉', '分割移轉', 
    '地號面積', '持分為十萬分之', '申報人','毛胚屋', '一般事務所', '店鋪']
    
    df = df[~df['備註'].str.contains('|'.join(noise_keywords), na=False)]
    df = df[~df['備註'].str.contains('|'.join(pre_sale_noise), na=False)]

    #else:print("注意：備註欄位不存在，已跳過備註噪音過濾步驟。")  
    
    unique_notes = df['備註'].astype(str).unique() 
    with open('unique_notes.txt', 'a', encoding='utf-8-sig') as f:
        for note in unique_notes:
            f.write(f"{note}\n")
    b_notes =  df['建物型態'].astype(str).unique()  
    with open('b_notes.txt', 'a', encoding='utf-8-sig') as f:
        for note in b_notes:
            f.write(f"{note}\n")    
            
    c_notes  =  df['主要用途'].astype(str).unique()        
    with open('c_notes.txt', 'a', encoding='utf-8-sig') as f:
        for note in c_notes:
            f.write(f"{note}\n")
            
    print(f"3. 備註噪音過濾完成，剩餘: {len(df)} 筆")

    # 【第五步：主要用途與型態過濾】
    # 1. 關鍵：先強制轉型為字串 (解決 floating 報錯)
    df['建物型態'] = df['建物型態'].astype(str)
    df['主要用途'] = df['主要用途'].astype(str)
    
    #新增b檔電梯欄位
    def infer_logic(row):
        b_type = str(row['建物型態'])
        floor = row['總樓層數'] 
        # 1. 住宅大樓、華廈、套房：預售與現代成屋市場中幾乎 100% 有電梯
        if any(x in b_type for x in ['住宅大樓', '華廈', '套房']):
            return 1  # 代表「有」     
        # 2. 公寓：傳統五層以下無電梯，但若總樓層 > 5 則視為新式電梯公寓
        if '公寓' in b_type:
            return 1 if floor > 5 else 0     
        # 3. 透天厝：標準產品無電梯，除非是高樓層電梯別墅
        if '透天厝' in b_type:
            # 實務經驗：預售透天若超過 4 層樓，配備電梯機率極高
            return 1 if floor > 4 else 0           
        # 4. 其他型態（如商辦、工廠等）根據樓層判斷
        return 1 if floor > 5 else 0
    if file_type == 'B':
        df['電梯'] = df.apply(infer_logic, axis=1)
    
    
    valid_types = ['住宅大樓', '公寓', '華廈', '套房', '透天厝', '其他']
    exclude_uses = ['工業', '商業', '辦公', '店面', '倉庫', '工廠', '農舍', '市場']
    clude_uses=['住家用','住商用','住商辦用'] 
    df = df[df['建物型態'].str.contains('|'.join(valid_types), na=False)]
    #df = df[~df['主要用途'].str.contains('|'.join(exclude_uses), na=False)]
    df = df[df['主要用途'].str.contains('|'.join(clude_uses), na=True)]
    #df = df[df['主要用途'].str.contains('住', na=False)]
    # 3. 增加的一條：刪除建物型態是「其他」且主要用途是「空」的資料
    # 使用 ~ (反向選取) 排除掉符合該條件的列
    df = df[~((df['建物型態'] == '其他') & (df['主要用途'].isna()))]
    print(f"4. 用途與型態過濾完成，剩餘: {len(df)} 筆")
    
    # 【第六步：行政區統計去噪】
    #df['lower_bound'] = df.groupby('鄉鎮市區')['單價_萬元坪'].transform(lambda x: x.quantile(0.05) if len(x) > 20 else 0)
    #df['upper_bound'] = df.groupby('鄉鎮市區')['單價_萬元坪'].transform(lambda x: x.quantile(0.95) if len(x) > 20 else float('inf'))
    #df_final = df[(df['單價_萬元坪'] >= df['lower_bound']) & (df['單價_萬元坪'] <= df['upper_bound'])].copy()
    df_final = df
    #print(f"5. 行政區極端值過濾完成，樣本少於20筆之行政區已全數保留，最終剩餘: {len(df_final)} 筆")
    o2+=len(df_final)
    # 【第七步：最終選取預測必要的屬性】
    # 這裡加入了 '屋齡' 欄位
    if '主建物面積' not in df_final.columns:
        df_final['主建物面積'] = df_final['建物移轉總面積平方公尺']* 0.62
    final_features = ['縣市','鄉鎮市區','完整行政區', '成交年', '成交月', '交易距今月數', '屋齡', '建物型態', '坪數', '單價_萬元坪','建案名稱','土地位置建物門牌',
                      '土地移轉總面積平方公尺','移轉層次','總樓層數','建物移轉總面積平方公尺','有無管理組織','電梯','is_presale', 'age_was_missing','交易標的','主建物面積']
    
    # 安全檢查
    if '鄉鎮市區' not in df_final.columns:
        df_final = df_final.reset_index()
        # 只有在 reset_index 之後才進行更名，避免平常破壞欄位結構
    df_final = df_final.rename(columns={'index': '鄉鎮市區', 'level_0': '鄉鎮市區'})
    
    
    df_output = df_final[final_features].copy()
    
    print(f"--- 清洗結束！最終保留欄位: {df_output.columns.tolist()} ---")
    print(f"--- 最終精華數據: {len(df_output)} 筆 ---")
    return df_output

import glob
#if __name__ == "__main__":
    # 執行程式
    
# 1. 取得資料夾內所有結尾為 _a.csv 的檔案路徑
# * 代表匹配任何字元 (例如 a_lvr_land_a.csv, b_lvr_land_a.csv...)

dd='house'
t1='a'
folders = [f for f in os.listdir(dd) if os.path.isdir(os.path.join(dd, f))]
all_processed_data = []
for y_m in folders:
    #y_m=11501
    file_list = glob.glob(f'./{dd}/{y_m}/*_{t1}.csv')   
    print(f"找到 {len(file_list)} 個成屋檔案待處理...")
    #all_processed_data = []

    #2. 迴圈處理每一個檔案
    for file_path in file_list:
        try:
            clean_df = forecast_ready_cleaning_with_tracking(file_path)
            # 檢查是否有產出資料（避免空檔案）
            if not clean_df.empty:
                all_processed_data.append(clean_df)
                print(f"✅ 成功處理: {file_path}")
        except Exception as e:
            print(f"❌ 處理 {file_path} 時發生錯誤: {e}")
    # 3. 合併所有處理後的 DataFrame
    # if all_processed_data:
    #     final_merged_df = pd.concat(all_processed_data, axis=0, ignore_index=True)
    #     final_merged_df.to_csv(f'./{dd}/{y_m}_all_districts_merged_{t1}.csv', index=False, encoding='utf-8-sig')
    #     print(f"合併完成！最終總筆數: {len(final_merged_df)}")
    # else:
    #     print("沒有任何資料被合併。")
if all_processed_data:
    final_merged_df = pd.concat(all_processed_data, axis=0, ignore_index=True)
    final_merged_df.to_csv(f'./{dd}/{dd}_final_merged_{t1}.csv', index=False, encoding='utf-8-sig')
    print(f"合併完成！最終總筆數: {len(final_merged_df)}")    
# 單獨處理 A 檔，並輸出到 final_prediction_data.csv
# clean_df = forecast_ready_cleaning_with_tracking('./house/11501/a_lvr_land_a.csv')
# clean_df.to_csv('final_prediction_data.csv', index=False, encoding='utf-8-sig')


# 2. 讀取 unique_notes.txt，去除空行和 'nan'，並去重排序後輸出到 unique_rows_only.txt
def aa():
    filea=['unique_notes.txt','b_notes.txt','c_notes.txt']
    for file in filea:
        with open(file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        data = [line.strip() for line in lines if line.strip() and line.strip() != 'nan']    
        
        df_unique_rows = pd.DataFrame(data, columns=['原始備註全文'])
        df_unique_rows = df_unique_rows.drop_duplicates().sort_values(by='原始備註全文').reset_index(drop=True)
        print(f"原始總行數: {len(lines)}")
        print(f"去重後獨立行數: {len(df_unique_rows)}")
        #df_unique_rows.to_csv('unique_rows_only.csv', index=False, encoding='utf-8-sig')
        with open(f'{file.split(".")[0]}_only.txt', 'w', encoding='utf-8-sig') as f:
                for note in df_unique_rows['原始備註全文']:
                    f.write(f"{note}\n")
aa()

def bb():
# 檢查是否有壞行
    if bad_lines_list:
        print(f"總共跳過了 {len(bad_lines_list)} 筆資料")
        for i, line in enumerate(bad_lines_list):
            print(f"壞行 {i+1} 內容: {line}")
    else:
        print("檔案非常乾淨，沒有任何壞行。")
bb()        
print(f"原始總筆數: {o1} 筆")
print(f"最終總筆數: {o2} 筆")