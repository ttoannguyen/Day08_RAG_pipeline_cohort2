"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Cài đặt:
    pip install markitdown

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

import json
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def extract_text_via_ocr(pdf_path: str) -> str:
    """Sử dụng EasyOCR và PyMuPDF để trích xuất văn bản từ file PDF scan."""
    import fitz
    import easyocr

    print(f"  [OCR] Dang khoi tao EasyOCR cho tieng Viet va quet (co the mat 1-2 phut)...")
    doc = fitz.open(pdf_path)
    reader = easyocr.Reader(['vi'])
    
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        result = reader.readtext(img_bytes, detail=0)
        page_text = " ".join(result)
        pages_text.append(f"## Page {page_num + 1}\n\n{page_text}\n")
        print(f"    - Quet xong trang {page_num + 1}/{len(doc)}")
        
    return "\n".join(pages_text)


def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()

    for filepath in legal_dir.iterdir():
        if filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            print(f"Converting: {filepath.name}")
            try:
                # Thử convert bằng MarkItDown
                result = md.convert(str(filepath))
                text_content = result.text_content

                # Nếu là file PDF và văn bản trích xuất được quá ít (< 100 ký tự), thực hiện OCR
                if filepath.suffix.lower() == ".pdf" and len(text_content.strip()) < 100:
                    print(f"  [!] Phat hien file PDF scan (khong co chu chon duoc): {filepath.name}")
                    text_content = extract_text_via_ocr(str(filepath))

                output_path = output_dir / f"{filepath.stem}.md"
                output_path.write_text(text_content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path}")
            except Exception as e:
                print(f"  [ERROR] Failed to convert {filepath.name}: {e}")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in news_dir.iterdir():
        if filepath.suffix.lower() == ".json":
            print(f"Converting: {filepath.name}")
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                output_path = output_dir / f"{filepath.stem}.md"

                # Thêm metadata header
                header = f"# {data.get('title', 'Unknown')}\n\n"
                header += f"**Source:** {data.get('url', 'N/A')}\n"
                header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"

                content = header + data.get("content_markdown", "")
                output_path.write_text(content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path}")
            except Exception as e:
                print(f"  [ERROR] Failed to convert {filepath.name}: {e}")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown with OCR fallback)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n[OK] Done! Output tai:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()
