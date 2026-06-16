import requests, json, time, random, os
import pandas as pd
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time, random

MAX_WORKERS = 3          # 建議 2~3 起跳
MIN_INTERVAL = 1.5       # 所有請求之間至少間隔秒數
lock = threading.Lock()
last_request_time = 0
request_lock = threading.Lock()
last_request_time = 0
def safe_get(session, url):
    global last_request_time

    with request_lock:
        now = time.time()

        wait_time = 1.5 - (now - last_request_time)

        if wait_time > 0:
            time.sleep(wait_time)

        last_request_time = time.time()

    res = session.get(
        url,
        timeout=30,
        verify=False
    )

    if res.status_code == 429:
        sleep_sec = random.uniform(30, 90)
        print(f"429，休息 {sleep_sec:.1f} 秒")
        time.sleep(sleep_sec)

        res = session.get(
            url,
            timeout=30,
            verify=False
        )

    return res
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CITY_MAP = {
    #"台北市": "Taipei-city",
     #"新北市": "NewTaipei-city",
     #"基隆市": "Keelung-city",
    # "宜蘭縣": "Yilan-county",
    # "新竹市": "Hsinchu-city",
    # "新竹縣": "Hsinchu-county",
    # "桃園市": "Taoyuan-city",
     "苗栗縣": "Miaoli-county",
     "台中市": "Taichung-city",
     "彰化縣": "Changhua-county",
    # "南投縣": "Nantou-county",
    # "雲林縣": "Yunlin-county",
    # "嘉義市": "Chiayi-city",
    # "嘉義縣": "Chiayi-county",
    # "台南市": "Tainan-city",
    # "高雄市": "Kaohsiung-city",
    # "屏東縣": "Pingtung-county",
    # "澎湖縣": "Penghu-county",
    # "台東縣": "Taitung-county",
    # "花蓮縣": "Hualien-county",
    # "金門縣": "Kinmen-county",
    # "連江縣": "Lienchiang-county",
}

BASE_URL = "https://www.sinyi.com.tw/buy/list/{city_code}/default-desc/{page}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.sinyi.com.tw/",
    "Connection": "keep-alive",
}

def build_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session

def get_soup(session, url):
    #res = session.get(url, timeout=30, verify=False)
    res = safe_get(session, url)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")
import re
def get_total_pages(session, city_code):
    url = BASE_URL.format(city_code=city_code, page=1)
    #res = session.get(url, timeout=30, verify=False)
    res = safe_get(session, url)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    nav_tag = soup.find("nav", {"aria-label": "SEO Pagination"})
    if not nav_tag:
        print(f"{city_code} 找不到分頁 nav，預設 1 頁")
        return 1

    pages = []

    for a in nav_tag.find_all("a", href=True):
        href = a["href"]

        # 例如 /buy/list/Taipei-city/default-desc/381
        match = re.search(rf"/buy/list/{re.escape(city_code)}/default-desc/(\d+)", href)
        if match:
            pages.append(int(match.group(1)))

    if pages:
        total_pages = max(pages)
        print(f"{city_code} 總頁數：{total_pages}")
        return total_pages

    print(f"{city_code} 分頁 href 解析失敗，預設 1 頁")
    return 1

def find_key(d, key):
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(d, list):
        for item in d:
            found = find_key(item, key)
            if found is not None:
                return found
    return None

def parse_house_list(html):
    soup = BeautifulSoup(html, "html.parser")

    # 方案 1：Next.js 常見資料區
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            data = json.loads(next_data.string)
            buy_reducer = find_key(data, "buyReducer")
            if buy_reducer and isinstance(buy_reducer, dict):
                house_list = buy_reducer.get("list", [])
                if house_list:
                    return house_list
        except Exception:
            pass

    # 方案 2：搜尋包含 buyReducer 的 script
    for script in soup.find_all("script"):
        text = script.string
        if not text or "buyReducer" not in text:
            continue

        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                continue

            data = json.loads(text[start_idx:end_idx])
            buy_reducer = find_key(data, "buyReducer")

            if buy_reducer and isinstance(buy_reducer, dict):
                house_list = buy_reducer.get("list", [])
                if house_list:
                    return house_list
        except Exception:
            continue

    return []

def save_checkpoint(rows, csv_path, json_path):
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def crawl_page(city_name, city_code, page):
    session = build_session()
    url = BASE_URL.format(city_code=city_code, page=page)

    try:
        res = safe_get(session, url)
        house_list = parse_house_list(res.text)

        for item in house_list:
            item["city_name"] = city_name
            item["city_code"] = city_code
            item["page"] = page
            item["source_url"] = url

        print(f"{city_name} 第 {page} 頁：{len(house_list)} 筆")
        return house_list

    except Exception as e:
        print(f"{city_name} 第 {page} 頁失敗：{e}")
        return []
    
def crawl_all():
    session = build_session()
    tasks = []
    all_rows = []

    # 先抓每個縣市總頁數
    city_pages = []
    for city_name, city_code in CITY_MAP.items():
        try:
            total_pages = get_total_pages(session, city_code)
            city_pages.append((city_name, city_code, total_pages))
            print(f"{city_name} 共 {total_pages} 頁")
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"{city_name} 總頁數失敗：{e}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for city_name, city_code, total_pages in city_pages:
            for page in range(1, total_pages + 1):
                tasks.append(
                    executor.submit(crawl_page, city_name, city_code, page)
                )

        for i, future in enumerate(as_completed(tasks), 1):
            rows = future.result()
            all_rows.extend(rows)

            if i % 50 == 0:
                save_checkpoint(
                    all_rows,
                    "sinyi_all_houses.csv",
                    "sinyi_all_houses.json"
                )
                print(f"已完成 {i}/{len(tasks)} 頁，累計 {len(all_rows)} 筆")

    save_checkpoint(
        all_rows,
        "sinyi_all_houses.csv",
        "sinyi_all_houses.json"
    )

    print(f"完成，總筆數：{len(all_rows)}")

if __name__ == "__main__":
    crawl_all()