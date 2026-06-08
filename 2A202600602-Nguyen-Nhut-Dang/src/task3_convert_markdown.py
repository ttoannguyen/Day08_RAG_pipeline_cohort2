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

import sys
import json
from pathlib import Path
from markitdown import MarkItDown

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_doc_to_docx(doc_path: Path, docx_path: Path):
    """Sử dụng Word COM để convert .doc sang .docx trên Windows."""
    import win32com.client
    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(doc_path.resolve()))
        # wdFormatXMLDocument = 16
        doc.SaveAs2(str(docx_path.resolve()), FileFormat=16)
        doc.Close()
    finally:
        if word:
            word.Quit()


def convert_legal_docs():
    """Convert PDF/DOCX/DOC files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()

    for filepath in list(legal_dir.iterdir()):
        if filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            if ".temp." in filepath.name:
                continue
            print(f"Converting: {filepath.name}")
            
            temp_docx = None
            target_path = filepath
            
            if filepath.suffix.lower() == ".doc":
                temp_docx = filepath.with_suffix(".temp.docx")
                try:
                    convert_doc_to_docx(filepath, temp_docx)
                    target_path = temp_docx
                except Exception as e:
                    print(f"  [ERROR] Word COM conversion failed for {filepath.name}: {e}")
                    print("  Trying Docling fallback for DOC...")
                    try:
                        from docling.document_converter import DocumentConverter
                        converter = DocumentConverter()
                        result = converter.convert(str(filepath.resolve()))
                        output_path = output_dir / f"{filepath.stem}.md"
                        output_path.write_text(result.exported_markdown, encoding="utf-8")
                        print(f"  [OK] Saved (via Docling): {output_path}")
                        continue
                    except Exception as docling_err:
                        print(f"  [ERROR] Docling conversion failed: {docling_err}")
                        continue

            try:
                result = md.convert(str(target_path.resolve()))
                output_path = output_dir / f"{filepath.stem}.md"
                output_path.write_text(result.text_content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path}")
            except Exception as e:
                print(f"  [ERROR] MarkItDown failed for {filepath.name}: {e}")
                print("  Trying Docling fallback...")
                try:
                    from docling.document_converter import DocumentConverter
                    converter = DocumentConverter()
                    result = converter.convert(str(filepath.resolve()))
                    output_path = output_dir / f"{filepath.stem}.md"
                    output_path.write_text(result.exported_markdown, encoding="utf-8")
                    print(f"  [OK] Saved (via Docling): {output_path}")
                except Exception as docling_err:
                    print(f"  [ERROR] Docling conversion failed: {docling_err}")
            finally:
                if temp_docx and temp_docx.exists():
                    try:
                        temp_docx.unlink()
                    except Exception:
                        pass


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

                # Extract fields correctly
                title = data.get("title", "Unknown")
                url = data.get("url", "N/A")
                crawl_date = data.get("crawl_date") or data.get("date_crawled") or "N/A"
                content_text = data.get("content") or data.get("content_markdown") or ""

                # Thêm metadata header
                header = f"# {title}\n\n"
                header += f"**Source:** {url}\n"
                header += f"**Crawled:** {crawl_date}\n\n---\n\n"

                content = header + content_text
                output_path.write_text(content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path}")
            except Exception as e:
                print(f"  [ERROR] Error converting {filepath.name}: {e}")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n[OK] Done! Output tại:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()
