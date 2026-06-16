import os
import pandas as pd

root_folder='./house'
df_list = []
for f in os.listdir(root_folder):
    #print(f"正在處理資料夾: {f}")
    if f.endswith('all_districts_merged_a.csv') or f.endswith('all_districts_merged_b.csv'):
        file_path = os.path.join(root_folder, f)
        print(f"正在處理檔案: {file_path}")
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=[1])
        except:
            df = pd.read_csv(file_path, encoding='cp950', skiprows=[1],encoding_errors='ignore') 
        df_list.append(df)   

# 4. 合併所有 DataFrame
# ignore_index=True 讓索引從 0 開始連續編排
combined_df = pd.concat(df_list, axis=0, ignore_index=True)

combined_df.to_csv(f'{root_folder}/all_merged_data_new.csv', index=False, encoding='utf-8-sig')

print(f"--- 合併完成，共合併了 {len(df_list)} 個檔案 ---")