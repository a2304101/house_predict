#t1234567.pkl 未補全_全_t2.pkl

import re
import pandas as pd
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