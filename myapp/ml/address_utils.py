import re
import pandas as pd


def extract_section_name(address, city, district):
    address = str(address)
    city = str(city) if pd.notna(city) else ""
    district = str(district) if pd.notna(district) else ""

    clean_addr = address
    clean_addr = clean_addr.replace("巿", "市")
    clean_addr = clean_addr.replace(city, "")
    clean_addr = clean_addr.replace(district, "")

    addr = str(clean_addr).strip()
    addr = re.sub(r"\s+", "", addr)
    addr = re.sub(r"[–—]", "-", addr)
    addr = addr.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    addr = re.sub(r"(\d+)(?:[-之,至;.、~。及附內]\d+)+", r"\1", addr)
    addr = re.sub(r"[一二三四五六七八九十\d\-]+鄰", "", addr)
    addr = re.sub(r"\d+衖", "", addr)
    addr = re.sub(r"(地下)?\d+樓之?\d*", "", addr)
    addr = re.sub(r"[一二三四五六七八九十]+樓之?[一二三四五六七八九十]*", "", addr)

    return addr


def build_clean_address(address, city, district):
    clean_geo = extract_section_name(address, city, district)

    clean_address = pd.Series([clean_geo]).str.extract(
        r"^(.*?號)", expand=False
    ).fillna(clean_geo).iloc[0]

    clean_address = re.sub(r"等.*?筆.*$", "", clean_address)
    clean_address = re.sub(
        r"([\d一二三四五六七八九十百]+)(?:、[\d一二三四五六七八九十百]+)+號",
        r"\1號",
        clean_address,
    )

    remove_no = re.sub(
        r"[\d一二三四五六七八九十百]+(?:[-之][\d一二三四五六七八九十百]+)*號",
        "",
        clean_address,
    ).strip()

    remove_lane = re.sub(r"\d+弄", "", remove_no).strip()
    remove_alley = re.sub(r"\d+巷", "", remove_lane).strip()
    remove_alley = re.split(r"(?i)[與和&、及X,.;]|vs|v.s", remove_alley)[0].strip()
    remove_alley = re.sub(r"[\(（].*?[\)）]", "", remove_alley).strip()
    remove_alley = re.sub(r"[A-Z].*$", "", remove_alley)
    remove_alley = re.sub(r"[a-z旁]", "", remove_alley)
    remove_alley = re.sub(r"約?\d+公尺", "", remove_alley)
    remove_alley = re.sub(r"(\d+|內)$", "", remove_alley)

    return {
        "乾淨地理位置": clean_geo,
        "乾淨地址": clean_address,
        "去號": remove_no,
        "去弄": remove_lane,
        "去巷": remove_alley,
        "最後地址": None,
    }