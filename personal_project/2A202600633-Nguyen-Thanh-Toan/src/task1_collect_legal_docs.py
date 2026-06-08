"""
Task 1 — Thu thập văn bản pháp luật về ma tuý và các chất cấm.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản pháp luật (PDF/DOCX) từ các nguồn chính thống.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, có năm ban hành.

Gợi ý nguồn:
    - https://thuvienphapluat.vn
    - https://vanban.chinhphu.vn
    - https://luatvietnam.vn

Gợi ý văn bản:
    - Luật Phòng, chống ma tuý 2021 (73/2021/QH15)
    - Nghị định 105/2021/NĐ-CP
    - Bộ luật Hình sự 2015 (sửa đổi 2017) - Chương XX
    - Nghị định 57/2022/NĐ-CP về danh mục chất ma tuý
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")



def check_existing_files():
    """Kiểm tra các file pháp luật hiện có trong thư mục."""
    valid_extensions = {".pdf", ".docx", ".doc"}
    files = [f for f in DATA_DIR.iterdir()
             if f.is_file() and f.suffix.lower() in valid_extensions]
    
    print(f"\nTìm thấy {len(files)} file pháp luật:")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.2f} KB)")
        if f.stat().st_size <= 1024:
            print(f"    ⚠ Cảnh báo: File {f.name} có kích thước quá nhỏ, có thể bị lỗi.")
            
    if len(files) >= 3:
        print("\n✓ Đã đủ tối thiểu 3 file pháp luật theo yêu cầu!")
        return True
    else:
        print(f"\n⚠ Chưa đủ số lượng file (Hiện có {len(files)}/3). Hãy bổ sung thêm.")
        return False


if __name__ == "__main__":
    setup_directory()
    check_existing_files()

