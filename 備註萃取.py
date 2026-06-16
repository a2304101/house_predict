import os
import pandas as pd

bad_lines_list = []
def collect_bad_lines(line):
    bad_lines_list.append(line)
    return None  # 回傳 None 表示跳過該行，不讀入 df

root_folder='./house'
for root, dirs, files in os.walk(root_folder):
    for n in dirs:
        r1=os.path.join(root, n)
        print(f"正在處理資料夾: {r1}")
        for f in os.listdir(r1):
            if f.endswith('_a.csv') or f.endswith('_b.csv'):
                file_path = os.path.join(r1, f)
                print(f"正在處理檔案: {file_path}")
                try:
                    df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=[1],on_bad_lines=collect_bad_lines,engine='python')
                except:
                    df = pd.read_csv(file_path, encoding='cp950', skiprows=[1],encoding_errors='ignore',on_bad_lines=collect_bad_lines,engine='python')

                # 在這裡可以對 df 進行後續的資料清洗和分析
                df['備註'] = df['備註'].astype(str).replace('nan', '')    
                unique_notes = df['備註'].astype(str).unique() 
                with open('unique_notes_total.txt', 'a', encoding='utf-8-sig') as f:
                    for note in unique_notes:
                        f.write(f"{note}\n")

def aa():
    filea=['unique_notes_total.txt','b_notes.txt','c_notes.txt']
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