import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Load cấu hình từ file .env
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent / "stock-liquidity-radar" / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[INFO] Đã nạp cấu hình từ: {env_path}")
else:
    load_dotenv()

AUTH_URL = os.getenv("NEO_AUTH_URL", "https://external.vpbanks.com.vn/auth/token")
USERNAME = os.getenv("NEO_USERNAME", "116c027612")
PASSWORD = os.getenv("NEO_PASSWORD", "@Baongoc12032006")
BASE_API_URL = os.getenv("NEO_API_URL", "https://neoapi.vpbanks.com.vn/neo-api")

OUTPUT_TXT_FILE = Path(__file__).parent / "stock_detail_data.txt"


def get_access_token():
    """Lấy JWT access_token từ API xác thực của VPBankS."""
    print(f"[AUTH] Đang đăng nhập lấy token cho user: {USERNAME}...")
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.post(AUTH_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if data.get("status") == 1 and "data" in data and "access_token" in data["data"]:
        token = data["data"]["access_token"]
        print("[AUTH] Đăng nhập thành công, đã lấy token.")
        return token
    else:
        raise RuntimeError(f"Đăng nhập thất bại: {data}")


def fetch_vn100_stocks(token):
    """
    Lấy danh sách chi tiết cổ phiếu thuộc rổ chỉ số VN100 (tất cả đều thuộc sàn HOSE)
    Sử dụng Endpoint 4.7 (/stock/stockDetailByIndex) với indexCode=VN100.
    """
    url = f"{BASE_API_URL.rstrip('/')}/stock/stockDetailByIndex"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-device": "crawler-app",
        "x-devicetype": "chrome",
        "Accept": "application/json"
    }
    params = {
        "indexCode": "VN100",
        "pageNo": 1,
        "pageSize": 1000
    }
    
    print(f"\n[FETCH] Đang lấy chi tiết cổ phiếu rổ VN100 từ {url}...")
    res = requests.get(url, headers=headers, params=params, timeout=30)
    res.raise_for_status()
    body = res.json()
    
    stocks = body.get("data", {}).get("content", [])
    print(f"[FETCH] Đã lấy thành công {len(stocks)} mã cổ phiếu thuộc rổ VN100 (sàn HOSE).")
    return stocks


def fetch_hose_stocks(token):
    """
    Lấy toàn bộ chi tiết cổ phiếu niêm yết trên sàn HOSE
    Sử dụng Endpoint 4.6 (/stock/stockDetail) với marketCode=HOSE.
    """
    url = f"{BASE_API_URL.rstrip('/')}/stock/stockDetail"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-device": "crawler-app",
        "x-devicetype": "chrome",
        "Accept": "application/json"
    }

    all_hose_stocks = []
    page_no = 1
    page_size = 1000
    total_pages = 1

    print(f"\n[FETCH] Đang lấy toàn bộ chi tiết cổ phiếu sàn HOSE từ {url}...")
    while page_no <= total_pages:
        params = {
            "marketCode": "HOSE",
            "pageNo": page_no,
            "pageSize": page_size
        }
        res = requests.get(url, headers=headers, params=params, timeout=30)
        res.raise_for_status()
        body = res.json()
        
        data_block = body.get("data", {})
        content = data_block.get("content", [])
        total_pages = data_block.get("totalPages", 1)
        all_hose_stocks.extend(content)
        
        print(f"  -> HOSE trang {page_no}/{total_pages}: +{len(content)} mã (Tổng: {len(all_hose_stocks)})")
        if data_block.get("last", False) or page_no >= total_pages:
            break
        page_no += 1
        time.sleep(0.3)

    return all_hose_stocks


def run_crawler():
    """
    Xóa dữ liệu cũ, cào dữ liệu mới cho sàn HOSE và rổ VN100, lưu lại vào file txt.
    """
    token = get_access_token()
    
    # 1. Cào 100 mã rổ VN100 (HOSE)
    vn100_stocks = fetch_vn100_stocks(token)
    vn100_symbols_set = {s.get("symbol") for s in vn100_stocks if s.get("symbol")}

    # 2. Cào toàn bộ sàn HOSE
    hose_stocks = fetch_hose_stocks(token)
    
    # Gắn cờ is_in_vn100 cho từng mã trên HOSE để dễ lọc
    for s in hose_stocks:
        s["is_in_vn100"] = s.get("symbol") in vn100_symbols_set

    # 3. Tạo cấu trúc kết quả JSON hoàn chỉnh
    final_result = {
        "metadata": {
            "title": "Dữ liệu chi tiết cổ phiếu sàn HOSE và rổ VN100",
            "marketCode": "HOSE",
            "indexCode": "VN100",
            "vn100_total": len(vn100_stocks),
            "hose_total": len(hose_stocks),
            "crawledAt": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "vn100_stocks": vn100_stocks,       # 100 mã cổ phiếu thuộc rổ VN100 (sàn HOSE)
        "hose_all_stocks": hose_stocks      # Toàn bộ mã niêm yết trên sàn HOSE (đã gắn cờ is_in_vn100)
    }

    # 4. Xóa dữ liệu cũ và ghi đè nội dung JSON mới vào file .txt tạm
    print(f"\n[SAVE] Xóa dữ liệu cũ và lưu dữ liệu mới vào: {OUTPUT_TXT_FILE}")
    with open(OUTPUT_TXT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)

    file_size_kb = OUTPUT_TXT_FILE.stat().st_size / 1024
    print(f"[DONE] Hoàn tất! File đã được ghi mới thành công ({file_size_kb:.2f} KB).")
    return OUTPUT_TXT_FILE


if __name__ == "__main__":
    try:
        run_crawler()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
