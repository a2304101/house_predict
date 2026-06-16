import requests

#API_URL = "http://localhost:8080/search.php"
API_URL = 'http://192.168.11.1:8080/search.php'

def match_text(display_name, target_city):
    if not display_name or not target_city:
        return False

    norm_display = str(display_name).replace("臺", "台")
    norm_target = str(target_city).replace("臺", "台")

    return norm_target in norm_display


def query_api(address, target_city, target_district):
    if not address or str(address).strip() in ["", "None"]:
        return None, None

    params = {
        "q": str(address).strip(),
        "format": "json",
        "limit": 10,
        "addressdetails": 1,
        "accept-language": "zh-TW",
    }

    try:
        r = requests.get(API_URL, params=params, timeout=3)

        if r.status_code != 200:
            return None, None

        data = r.json()

        for item in data:
            disp = item.get("display_name", "")
            if match_text(disp, target_city) and match_text(disp, target_district):
                return float(item["lat"]), float(item["lon"])

        for item in data:
            disp = item.get("display_name", "")
            if match_text(disp, target_city):
                return float(item["lat"]), float(item["lon"])

    except Exception:
        pass

    return None, None


def geocode_address(city, district, clean_info):
    candidates = [
        ("乾淨地理位置_full", f"{city}{district}{clean_info['乾淨地理位置']}"),
        ("只有乾淨地理位置", clean_info["乾淨地理位置"]),
        ("乾淨地址_full", f"{city}{district}{clean_info['乾淨地址']}"),
        ("只有乾淨地址", clean_info["乾淨地址"]),
        ("去號_full", f"{city}{district}{clean_info['去號']}"),
        ("只有去號", clean_info["去號"]),
        ("去弄_full", f"{city}{district}{clean_info['去弄']}"),
        ("只有去弄", clean_info["去弄"]),
        ("去巷_full", f"{city}{district}{clean_info['去巷']}"),
        ("只有去巷", clean_info["去巷"]),
    ]

    for index, (label, addr) in enumerate(candidates, start=1):
        lat, lon = query_api(addr, city, district)

        if lat and lon:
            return {
                "lat": lat,
                "lon": lon,
                "used_address": addr,
                "used_address_label": label,
                "used_address_level": index,
                "geocode_success": True,
            }

    return {
        "lat": None,
        "lon": None,
        "used_address": None,
        "used_address_label": "沒得到經緯度",
        "used_address_level": None,
        "geocode_success": False,
    }