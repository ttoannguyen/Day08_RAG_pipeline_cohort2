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

import io
import json
import os
import shutil
from pathlib import Path

from markitdown import MarkItDown

PROJECT_DIR = Path(__file__).parent.parent
LANDING_DIR = PROJECT_DIR / "data" / "landing"
OUTPUT_DIR = PROJECT_DIR / "data" / "standardized"
TESSDATA_DIR = PROJECT_DIR / "tessdata"
MIN_CONTENT_CHARS = 200


def _is_already_converted(output_path: Path) -> bool:
    """Bỏ qua nếu file .md đã tồn tại và có đủ nội dung."""
    if not output_path.exists():
        return False
    try:
        return len(output_path.read_text(encoding="utf-8").strip()) >= MIN_CONTENT_CHARS
    except OSError:
        return False


def _configure_tesseract() -> bool:
    """Tìm binary Tesseract trên Windows/Linux/macOS."""
    import pytesseract

    if shutil.which("tesseract"):
        return True

    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return True
    return False


def _extract_pdf_text(filepath: Path) -> str:
    """Fallback: đọc text layer có sẵn trong PDF (không OCR)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""

    doc = fitz.open(filepath)
    return "\n\n".join(page.get_text() for page in doc).strip()


def _ocr_pdf_text(filepath: Path, dpi: int = 200) -> str:
    """
    OCR PDF dạng scan: render từng trang thành ảnh rồi nhận dạng bằng Tesseract.

    Cần cài Tesseract OCR trên máy:
        winget install UB-Mannheim.TesseractOCR
    Và gói tiếng Việt (vie.traineddata) trong thư mục tessdata của Tesseract.
    """
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu thư viện OCR. Chạy: pip install pymupdf pytesseract Pillow"
        ) from exc

    if not _configure_tesseract():
        raise RuntimeError(
            "Chưa cài Tesseract OCR. Chạy: winget install UB-Mannheim.TesseractOCR"
        )

    tess_config = ""
    if (TESSDATA_DIR / "vie.traineddata").exists():
        # Không bọc path trong dấu ngoặc — pytesseract truyền thẳng cho tesseract CLI
        tess_config = f"--tessdata-dir {TESSDATA_DIR}"

    doc = fitz.open(filepath)
    chunks: list[str] = []
    total = len(doc)

    for i, page in enumerate(doc):
        print(f"    OCR page {i + 1}/{total}...")
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            text = pytesseract.image_to_string(
                img, lang="vie+eng", config=tess_config
            )
        except pytesseract.TesseractError:
            text = pytesseract.image_to_string(
                img, lang="eng", config=tess_config
            )
        if text.strip():
            chunks.append(text.strip())

    return "\n\n".join(chunks).strip()


def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()

    if not legal_dir.exists():
        print("  (skip) legal dir not found")
        return

    for filepath in legal_dir.iterdir():
        if filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            output_path = output_dir / f"{filepath.stem}.md"
            if _is_already_converted(output_path):
                print(f"  Skip (đã convert): {output_path.name}")
                continue

            print(f"Converting: {filepath.name}")
            result = md.convert(str(filepath))
            content = (result.text_content or "").strip()

            if len(content) < MIN_CONTENT_CHARS and filepath.suffix.lower() == ".pdf":
                content = _extract_pdf_text(filepath)

            if len(content) < MIN_CONTENT_CHARS and filepath.suffix.lower() == ".pdf":
                print(f"  PDF scan detected — running OCR for: {filepath.name}")
                try:
                    content = _ocr_pdf_text(filepath)
                except RuntimeError as exc:
                    print(f"  OCR failed: {exc}")
                    content = ""

            if len(content) < MIN_CONTENT_CHARS:
                if output_path.exists():
                    output_path.unlink()
                print(
                    f"  Skip: {filepath.name} — không đủ nội dung sau OCR "
                    f"({len(content)} chars)."
                )
                continue

            output_path.write_text(content, encoding="utf-8")
            print(f"  Saved: {output_path}")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.exists():
        print("  (skip) news dir not found")
        return

    for filepath in news_dir.iterdir():
        if filepath.suffix.lower() == ".json":
            output_path = output_dir / f"{filepath.stem}.md"
            if _is_already_converted(output_path):
                print(f"  Skip (đã convert): {output_path.name}")
                continue

            print(f"Converting: {filepath.name}")
            data = json.loads(filepath.read_text(encoding="utf-8"))

            header = f"# {data.get('title', 'Unknown')}\n\n"
            header += f"**Source:** {data.get('url', 'N/A')}\n"
            header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"

            content = header + data.get("content_markdown", "")
            output_path.write_text(content, encoding="utf-8")
            print(f"  Saved: {output_path}")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n✓ Done! Output tại:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()
