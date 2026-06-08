"""
Task 2 — Crawl bài báo về nghệ sĩ liên quan tới ma tuý.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài báo từ các trang tin tức Việt Nam.
    2. Sử dụng Crawl4AI hoặc thư viện crawling tương tự.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).

Cài đặt:
    pip install crawl4ai
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Danh sách URL bài báo cần crawl do người dùng cung cấp
ARTICLE_URLS = [
    "https://tuoitre.vn/ca-si-chi-dan-nguoi-mau-an-tay-co-tien-truc-phuong-to-chuc-su-dung-ma-tuy-ra-sao-2026040214370414.htm",
    "https://thanhnien.vn/dien-vien-huu-tin-nghien-ma-tuy-gan-3-nam-moi-ban-ve-nha-su-dung-thuoc-lac-1851517030.htm",
    "https://tuoitre.vn/khoi-to-3-bi-can-trong-vu-ca-si-miu-le-su-dung-ma-tuy-o-cat-ba-20260514230349573.htm",
    "https://tienphong.vn/hanh-trinh-phe-ma-tuy-roi-giet-nguoi-cua-ca-si-chau-viet-cuong-post1095287.tpo",
    "https://vnexpress.net/ca-si-long-nhat-son-ngoc-minh-bi-bat-vi-lien-quan-ma-tuy-5060857.html",
]


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài báo và trả về dict chứa metadata + content.

    Returns:
        {
            "url": str,
            "title": str,
            "date_crawled": str (ISO format),
            "content_markdown": str
        }
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        
        # crawl4ai 0.8.x có thể trả về CrawlResultContainer hoặc CrawlResult
        if hasattr(result, '__getitem__') and len(result) > 0:
            crawl_res = result[0]
        else:
            crawl_res = result
            
        title = "Unknown"
        if crawl_res.metadata and isinstance(crawl_res.metadata, dict):
            title = crawl_res.metadata.get("title", "Unknown")
            
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": str(crawl_res.markdown) if crawl_res.markdown else "",
        }


async def crawl_all():
    """Crawl toàn bộ bài báo trong ARTICLE_URLS."""
    setup_directory()

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        article = await crawl_article(url)

        # Lưu file JSON
        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] Saved: {filepath}")


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("[WARNING] Hay dien ARTICLE_URLS truoc khi chay!")
        print("Go y: tim bai bao tren VnExpress, Tuoi Tre, Thanh Nien, ...")
    else:
        asyncio.run(crawl_all())
