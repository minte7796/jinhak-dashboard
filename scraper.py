import requests
import re
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "latest_ratios.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

TARGET_UNIVERSITIES = [
    {
        "id": "kwangwoon",
        "univ": "광운대학교",
        "campus": "본교",
        "admission_type": "학생부교과 지역균형전형",
        "major": "컴퓨터정보공학부",
        "ratio_url": "https://ratio.uwayapply.com/Sl5KTjlKZiUmOiZKN2ZUZg==",
        "system": "유웨이어플라이",
        "jeonhyeong_keyword": "지역균형",
        "major_keyword": "컴퓨터정보공학부",
        "color": "#991b1b",
        "badge_color": "bg-red-50 text-red-700 border-red-200"
    },
    {
        "id": "kyonggi",
        "univ": "경기대학교",
        "campus": "수원",
        "admission_type": "학생부교과 학교장추천전형",
        "major": "산업경영공학과",
        "ratio_url": "https://ratio.uwayapply.com/Sl5KJXJyV2FiOUpmJSY6Jko3ZlRm",
        "system": "유웨이어플라이",
        "jeonhyeong_keyword": "학교장추천",
        "major_keyword": "산업경영공학과",
        "color": "#1e40af",
        "badge_color": "bg-blue-50 text-blue-700 border-blue-200"
    },
    {
        "id": "dankook",
        "univ": "단국대학교",
        "campus": "죽전",
        "admission_type": "학생부교과 지역균형전형",
        "major": "소프트웨어학과",
        "ratio_url": "https://addon.jinhakapply.com/RatioV1/RatioH/Ratio10420521.html",
        "system": "진학어플라이",
        "jeonhyeong_keyword": "지역균형선발",
        "major_keyword": "소프트웨어학과",
        "color": "#0369a1",
        "badge_color": "bg-sky-50 text-sky-700 border-sky-200"
    },
    {
        "id": "catholic",
        "univ": "가톨릭대학교",
        "campus": "성심",
        "admission_type": "학생부교과 지역균형전형",
        "major": "데이터사이언스학과",
        "ratio_url": "https://addon.jinhakapply.com/RatioV1/RatioH/Ratio10030381.html",
        "system": "진학어플라이",
        "jeonhyeong_keyword": "지역균형전형",
        "major_keyword": "데이터사이언스학과",
        "color": "#047857",
        "badge_color": "bg-emerald-50 text-emerald-700 border-emerald-200"
    },
    {
        "id": "hankyong",
        "univ": "한경국립대학교",
        "campus": "안성",
        "admission_type": "학생부교과 일반전형",
        "major": "인공지능학과",
        "ratio_url": "https://addon.jinhakapply.com/RatioV1/RatioH/Ratio30161171.html",
        "system": "진학어플라이",
        "jeonhyeong_keyword": "일반전형_안성",
        "major_keyword": "인공지능학과",
        "color": "#b45309",
        "badge_color": "bg-amber-50 text-amber-700 border-amber-200"
    },
    {
        "id": "tukorea",
        "univ": "한국공학대학교",
        "campus": "시흥",
        "admission_type": "학생부교과 지역균형",
        "major": "인공지능학과",
        "ratio_url": "https://addon.jinhakapply.com/RatioV1/RatioH/Ratio30170741.html",
        "system": "진학어플라이",
        "jeonhyeong_keyword": "지역균형",
        "major_keyword": "인공지능학과",
        "color": "#6d28d9",
        "badge_color": "bg-purple-50 text-purple-700 border-purple-200"
    }
]

def fetch_page_content(target):
    """Fetches HTML with thread-safe requests and clean headers."""
    url = target["ratio_url"]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://apply.jinhakapply.com/' if 'jinhak' in url else 'https://ratio.uwayapply.com/'
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5, verify=False)
        if resp.status_code == 200:
            content = resp.content
            for enc in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    text = content.decode(enc)
                    if any(k in text for k in [target["major_keyword"], target["jeonhyeong_keyword"], "경쟁률"]):
                        return text
                except (UnicodeDecodeError, LookupError):
                    continue
            return content.decode('utf-8', errors='replace')
        else:
            print(f"[{target['univ']}] Fetch status: {resp.status_code}")
    except Exception as e:
        print(f"[{target['univ']}] Fetch error: {e}")

    return None

def parse_university_data(target, old_item=None):
    """Extract quota, applicants, ratio, and last updated time for a single university target."""
    result = {
        "id": target["id"],
        "univ": target["univ"],
        "campus": target.get("campus", ""),
        "admission_type": target["admission_type"],
        "major": target["major"],
        "quota": old_item.get("quota", "-") if old_item else "-",
        "applicants": old_item.get("applicants", "-") if old_item else "-",
        "ratio": old_item.get("ratio", "-") if old_item else "-",
        "ratio_num": old_item.get("ratio_num", 0.0) if old_item else 0.0,
        "update_time": old_item.get("update_time", "확인 중") if old_item else "확인 중",
        "ratio_url": target["ratio_url"],
        "system": target["system"],
        "color": target["color"],
        "badge_color": target["badge_color"],
        "status": "정상",
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        html = fetch_page_content(target)
        if not html:
            if old_item and old_item.get("quota") != "-":
                result["status"] = "접속 지연 (이전 데이터 유지)"
            else:
                result["status"] = "접속 제한 (해외IP/Cloudflare 차단)"
            return result

        soup = BeautifulSoup(html, 'html.parser')
        full_text = soup.get_text()

        # 1. Extract University Official Last Updated Time
        m_uway = re.search(r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*\d{1,2}시(?:\s*\d{1,2}분)?(?:\s*기준)?)', full_text)
        if m_uway:
            result["update_time"] = m_uway.group(1).strip()
        else:
            m_jinhak = re.search(r'(\d{4}[-.]\s*\d{1,2}[-.]\s*\d{1,2}\s*(?:오전|오후)?\s*\d{1,2}:\d{1,2}(?:\s*현재)?)', full_text)
            if m_jinhak:
                result["update_time"] = m_jinhak.group(1).strip()
            else:
                m_fallback = re.search(r'(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}[일]?\s*(?:[오전|오후]*\s*\d{1,2}[:시]\s*\d{1,2}))', full_text)
                if m_fallback:
                    result["update_time"] = m_fallback.group(1).strip()

        # 2. Extract Table & Major Information
        tables = soup.find_all('table')
        target_table = None

        for table in tables:
            caption = table.caption.get_text().strip() if table.caption else ""
            prev = table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span', 'p'])
            prev_txt = prev.get_text().strip() if prev else ""
            full_title = f"{caption} {prev_txt}".strip()

            if target["jeonhyeong_keyword"] in full_title:
                target_table = table
                break

        if not target_table:
            for table in tables:
                t_head = table.get_text()[:200]
                if target["jeonhyeong_keyword"] in t_head:
                    target_table = table
                    break

        matched_row = None
        exact_matched_row = None
        partial_matched_row = None

        if target_table:
            for tr in target_table.find_all('tr'):
                cells = [re.sub(r'\s+', ' ', td.get_text().strip().replace('\xa0', ' ')) for td in tr.find_all(['td', 'th'])]
                if not cells:
                    continue
                if any(cell == target["major_keyword"] for cell in cells):
                    exact_matched_row = cells
                    break
                elif any(target["major_keyword"] in cell and len(cell) < 30 for cell in cells):
                    partial_matched_row = cells

            matched_row = exact_matched_row or partial_matched_row

        # 3. Parse numbers (quota, applicants, ratio) from matched_row
        if matched_row:
            for i in range(len(matched_row) - 1, -1, -1):
                val = matched_row[i]
                if ":" in val:
                    result["ratio"] = val
                    rm = re.search(r'([\d.]+)\s*:', val)
                    if rm:
                        result["ratio_num"] = float(rm.group(1))

                    num_cells = []
                    for j in range(i - 1, -1, -1):
                        c = matched_row[j].replace(',', '').strip()
                        if c.isdigit():
                            num_cells.append(c)
                        elif num_cells:
                            break
                    if len(num_cells) >= 2:
                        result["applicants"] = num_cells[0]
                        result["quota"] = num_cells[1]
                    elif len(num_cells) == 1:
                        result["applicants"] = num_cells[0]
                    result["status"] = "정상"
                    break
        else:
            if old_item and old_item.get("quota") != "-":
                result["status"] = "데이터 갱신 지연 (이전 데이터 유지)"
            else:
                result["status"] = "대상 데이터 탐색 실패"

    except Exception as e:
        print(f"[{target['univ']}] Parse error: {e}")
        result["status"] = f"오류 발생: {str(e)}"

    return result

def scrape_all_targets():
    """Scrapes all 6 targets concurrently and saves to cache."""
    os.makedirs(DATA_DIR, exist_ok=True)

    old_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                prev_json = json.load(f)
                for item in prev_json.get("items", []):
                    old_data[item["id"]] = item
        except Exception:
            pass

    # Concurrent parallel scraping with individual thread safety
    def do_task(t):
        return parse_university_data(t, old_data.get(t["id"]))

    with ThreadPoolExecutor(max_workers=6) as executor:
        raw_results = list(executor.map(do_task, TARGET_UNIVERSITIES))

    items = []
    total_quota = 0
    total_applicants = 0
    highest_ratio_item = None
    highest_ratio = -1.0

    for data in raw_results:
        prev_item = old_data.get(data["id"])
        if prev_item and str(prev_item.get("applicants", "")).isdigit() and str(data["applicants"]).isdigit():
            prev_app = int(prev_item["applicants"])
            curr_app = int(data["applicants"])
            diff_app = curr_app - prev_app
            data["diff_applicants"] = diff_app
        else:
            data["diff_applicants"] = 0

        if prev_item and prev_item.get("ratio_num") is not None:
            prev_r = float(prev_item.get("ratio_num", 0.0))
            curr_r = float(data.get("ratio_num", 0.0))
            data["diff_ratio"] = round(curr_r - prev_r, 2)
        else:
            data["diff_ratio"] = 0.0

        if str(data["quota"]).isdigit():
            total_quota += int(data["quota"])
        if str(data["applicants"]).isdigit():
            total_applicants += int(data["applicants"])

        if data["ratio_num"] > highest_ratio:
            highest_ratio = data["ratio_num"]
            highest_ratio_item = {
                "univ": data["univ"],
                "major": data["major"],
                "ratio": data["ratio"],
                "ratio_num": data["ratio_num"]
            }

        items.append(data)

    avg_ratio = round(total_applicants / total_quota, 2) if total_quota > 0 else 0.0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = {
        "updated_at": now_str,
        "school_year": "2027학년도",
        "category": "수시모집",
        "total_targets": len(items),
        "total_quota": total_quota,
        "total_applicants": total_applicants,
        "avg_ratio": f"{avg_ratio:.2f} : 1",
        "avg_ratio_num": avg_ratio,
        "highest_ratio_item": highest_ratio_item,
        "items": items
    }

    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []

        history_entry = {
            "timestamp": now_str,
            "total_applicants": total_applicants,
            "avg_ratio_num": avg_ratio,
            "univ_ratios": {item["univ"]: item["ratio_num"] for item in items}
        }
        history.append(history_entry)
        if len(history) > 100:
            history = history[-100:]

        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return summary

def get_latest_data(force_refresh=False):
    """Retrieve cached data, or trigger a live refresh if cache is missing or force_refresh is True."""
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data and "items" in data and len(data["items"]) == len(TARGET_UNIVERSITIES):
                    return data
        except Exception:
            pass

    return scrape_all_targets()
