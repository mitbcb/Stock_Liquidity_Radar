import os
import sys
import json
from pathlib import Path

# Đường dẫn file dữ liệu
DATA_FILE = Path(__file__).parent / "stock_detail_data.txt"

# Danh sách các trường cần lọc trích xuất theo đúng yêu cầu
TARGET_FIELDS = [
    "symbol",
    "closePrice",
    "refPrice",
    "ceilingPrice",
    "floorPrice",
    "openPrice",
    "highPrice",
    "lowPrice",
    "totalTradingVolume",
    "totalTradingValue",
    "bidPrice1",
    "bidPrice2",
    "bidPrice3",
    "bidVolume1",
    "bidVolume2",
    "bidVolume3",
    "askPrice1",
    "askPrice2",
    "askPrice3",
    "askVolume1",
    "askVolume2",
    "askVolume3"
]

# Ánh xạ tên trường từ raw API sang tên trường chuẩn yêu cầu
FIELD_MAPPING = {
    "bidVolume1": ["bidVolume1", "bidVol1"],
    "bidVolume2": ["bidVolume2", "bidVol2"],
    "bidVolume3": ["bidVolume3", "bidVol3"],
    "askVolume1": ["askVolume1", "askVol1"],
    "askVolume2": ["askVolume2", "askVol2"],
    "askVolume3": ["askVolume3", "askVolume", "askVol3"]
}


def parse_numeric(val):
    """
    Chuyển đổi kiểu dữ liệu số an toàn (giữ nguyên nếu là ATO, ATC hoặc None)
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        try:
            if "." in val_str:
                return float(val_str)
            return int(val_str)
        except ValueError:
            return val_str
    return val


def clean_stock_item(raw_item):
    """
    Trích xuất và chuẩn hóa đúng các trường yêu cầu cho một mã cổ phiếu.
    """
    cleaned = {}
    for field in TARGET_FIELDS:
        val = None
        # Kiểm tra nếu trường có alias/mapping
        if field in FIELD_MAPPING:
            for candidate in FIELD_MAPPING[field]:
                if candidate in raw_item and raw_item[candidate] is not None:
                    val = raw_item[candidate]
                    break
        else:
            val = raw_item.get(field)
            
        # Chuẩn hóa giá trị số cho các trường giá / khối lượng
        if field != "symbol":
            cleaned[field] = parse_numeric(val)
        else:
            cleaned[field] = val

    return cleaned


def clean_data_file(file_path=DATA_FILE):
    """
    Đọc file stock_detail_data.txt, lọc sạch các trường thừa,
    và ghi đè lại vào file với các field yêu cầu.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    print(f"[CLEANER] Đang đọc file: {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = {}

    # Giữ lại metadata tổng quan
    if "metadata" in data:
        cleaned_data["metadata"] = data["metadata"]
        cleaned_data["metadata"]["cleaned_fields"] = TARGET_FIELDS

    # Lọc danh sách vn100_stocks nếu có
    if "vn100_stocks" in data and isinstance(data["vn100_stocks"], list):
        print(f"[CLEANER] Đang lọc {len(data['vn100_stocks'])} mã rổ VN100...")
        cleaned_data["vn100_stocks"] = [clean_stock_item(item) for item in data["vn100_stocks"]]

    # Lọc danh sách hose_all_stocks nếu có
    if "hose_all_stocks" in data and isinstance(data["hose_all_stocks"], list):
        print(f"[CLEANER] Đang lọc {len(data['hose_all_stocks'])} mã sàn HOSE...")
        cleaned_data["hose_all_stocks"] = [clean_stock_item(item) for item in data["hose_all_stocks"]]

    # Nếu file là dạng danh sách trực tiếp (list) hoặc mảng stocks thông thường
    if "stocks" in data and isinstance(data["stocks"], list):
        print(f"[CLEANER] Đang lọc {len(data['stocks'])} mã trong mảng stocks...")
        cleaned_data["stocks"] = [clean_stock_item(item) for item in data["stocks"]]
    elif isinstance(data, list):
        print(f"[CLEANER] Đang lọc danh sách phẳng gồm {len(data)} mã...")
        cleaned_data = [clean_stock_item(item) for item in data]

    # Ghi đè vào file dữ liệu cũ
    print(f"[CLEANER] Đang lưu dữ liệu đã lọc vào file cũ: {file_path}...")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    new_size_kb = file_path.stat().st_size / 1024
    print(f"[DONE] Hoàn tất! Kích thước file sau khi lọc: {new_size_kb:.2f} KB.")
    return file_path


if __name__ == "__main__":
    try:
        clean_data_file()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
