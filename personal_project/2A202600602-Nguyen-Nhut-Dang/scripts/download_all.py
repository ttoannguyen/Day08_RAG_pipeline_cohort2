import os
import re
import json
import base64
import datetime
import requests
from pathlib import Path
import urllib.parse
import sys
import html

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Setup paths inside 2A202600602-Nguyen-Nhut-Dang
STUDENT_DIR = Path(__file__).parent.parent
LEGAL_DIR = STUDENT_DIR / "data" / "landing" / "legal"
NEWS_DIR = STUDENT_DIR / "data" / "landing" / "news"

def setup_dirs():
    LEGAL_DIR.mkdir(parents=True, exist_ok=True)
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created directories: {LEGAL_DIR}, {NEWS_DIR}")

# ----------------- Task 1: Legal Documents Downloader -----------------

def download_via_classic_url(item_id, output_path):
    """
    Tải file từ trang ASP.NET truyền thống của vbpl.vn sử dụng ItemID
    """
    url = f"https://vbpl.vn/TW/Pages/vbpq-van-ban-goc.aspx?ItemID={item_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  [Classic] Failed to fetch page for ItemID {item_id}: {r.status_code}")
        return False
        
    # Search for DownloadHandler links
    matches = re.findall(r'href=[\"\'](/Shared/Handlers/DownloadHandler\.ashx\?[^\'\"]+)[\"\']', r.text)
    if matches:
        download_path = matches[0].replace("&amp;", "&")
        download_url = f"https://vbpl.vn{download_path}"
        print(f"  [Classic] Found direct download link: {download_url}")
        
        file_r = requests.get(download_url, headers=headers)
        if file_r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(file_r.content)
            print(f"  ✓ [Classic] Downloaded and saved to {output_path}")
            return True
    
    print(f"  [Classic] No direct download link found in classic page for ItemID {item_id}")
    return False

def download_via_nextjs_action(item_id, default_filename, output_path):
    """
    Tải file sử dụng Next.js Server Action của vbpl.vn
    """
    detail_url = f"https://vbpl.vn/van-ban/chi-tiet/van-ban--{item_id}?tabs=tai-ve"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Resolving canonical URL dynamically to make the Next.js Server Action request succeed
    action_url = detail_url
    try:
        r = requests.get(detail_url, headers=headers, timeout=15)
        if r.status_code == 200:
            match = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"', r.text)
            if match:
                canonical = match.group(1)
                if "tabs=tai-ve" not in canonical:
                    if "?" in canonical:
                        canonical = canonical.split("?")[0] + "?tabs=tai-ve"
                    else:
                        canonical += "?tabs=tai-ve"
                action_url = canonical
                print(f"  [Next.js] Resolved canonical URL: {action_url}")
    except Exception as e:
        print(f"  [Next.js] Warning: Failed to resolve canonical URL: {e}")

    object_name = default_filename
    action_headers = {
        "Accept": "text/x-component",
        "Next-Action": "bad13391811d5f14d7670e66189def56c08ceb1f",
        "Content-Type": "text/plain;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    payload = [{
        "bucketName": "vbpl",
        "folderName": str(item_id),
        "objectName": object_name,
        "preview": None
    }]
    
    print(f"  [Next.js] Sending POST Server Action for {object_name} (folder: {item_id})...")
    post_r = requests.post(action_url, headers=action_headers, data=json.dumps(payload))
    if post_r.status_code != 200:
        print(f"  [Next.js] POST request failed with status {post_r.status_code}")
        return False
        
    text = post_r.text
    marker = "2:T"
    idx = text.find(marker)
    if idx == -1:
        print(f"  [Next.js] Base64 marker not found in Server Action response.")
        return False
        
    sub_text = text[idx + len(marker):]
    comma_idx = sub_text.find(",")
    if comma_idx == -1:
        print(f"  [Next.js] Comma separator not found in Server Action response.")
        return False
        
    hex_len = sub_text[:comma_idx]
    try:
        base64_len = int(hex_len, 16)
    except ValueError:
        print(f"  [Next.js] Failed to parse hex length: {hex_len}")
        return False
        
    base64_str = sub_text[comma_idx + 1:][:base64_len]
    try:
        file_bytes = base64.b64decode(base64_str)
    except Exception as e:
        print(f"  [Next.js] Failed to decode base64: {e}")
        return False
        
    if len(file_bytes) < 1000:
        print(f"  [Next.js] Decoded file is too small ({len(file_bytes)} bytes), probably an error message.")
        return False
        
    with open(output_path, "wb") as f:
        f.write(file_bytes)
    print(f"  ✓ [Next.js] Downloaded and saved to {output_path} ({len(file_bytes)} bytes)")
    return True

def download_legal_docs():
    docs_to_download = [
        {
            "name": "Luật Phòng, chống ma tuý 2021",
            "item_id": 152501,
            "default_filename": "73_2021_QH14 (2).doc",
            "output_name": "luat-phong-chong-ma-tuy-2021.doc"
        },
        {
            "name": "Nghị định 105/2021/NĐ-CP",
            "item_id": 154992,
            "default_filename": "105.2021.NĐ.CP.doc",
            "output_name": "nghi-dinh-105-2021.doc"
        },
        {
            "name": "Bộ luật Hình sự 2015",
            "item_id": 96122,
            "default_filename": "100.2015.QH13.doc",
            "output_name": "bo-luat-hinh-su-2015.doc"
        },
        {
            "name": "Nghị định 28/2026/NĐ-CP",
            "direct_url": "https://congbaocdn.chinhphu.vn/180507251028987904/2026/2/4/28signed-1770197502883408446461.pdf",
            "output_name": "nghi-dinh-28-2026.pdf"
        }
    ]
    
    for doc in docs_to_download:
        name = doc["name"]
        out_name = doc["output_name"]
        out_path = LEGAL_DIR / out_name
        
        print(f"\n--- Downloading: {name} ---")
        
        success = False
        if "direct_url" in doc:
            print(f"  Downloading directly from: {doc['direct_url']}")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                r = requests.get(doc["direct_url"], headers=headers, timeout=30)
                if r.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    print(f"  ✓ Downloaded and saved to {out_path} ({len(r.content)} bytes)")
                    success = True
                else:
                    print(f"  ❌ Failed to download directly: HTTP {r.status_code}")
            except Exception as e:
                print(f"  ❌ Direct download raised exception: {e}")
        else:
            item_id = doc["item_id"]
            default_fn = doc["default_filename"]
            try:
                success = download_via_nextjs_action(item_id, default_fn, out_path)
            except Exception as e:
                print(f"  Next.js Action method raised exception: {e}")
                
            if not success:
                print(f"  Falling back to classic download URL method...")
                try:
                    success = download_via_classic_url(item_id, out_path)
                except Exception as e:
                    print(f"  Classic method raised exception: {e}")
                    
        if not success:
            print(f"❌ FAILED to download: {name}. Stopping process.")
            return False
            
    print("\n✓ Task 1: All legal documents downloaded successfully.")
    return True

# ----------------- Task 2: News Crawler -----------------

def crawl_news_article(url, index):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    print(f"  Crawling URL: {url}")
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  ❌ Failed to fetch: {r.status_code}")
        return None
        
    r.encoding = 'utf-8'
    html_content = r.text
    
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
    title = "Unknown Title"
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        title = html.unescape(title)
        
    # Extract sapo from <h2> tag (Dân Trí articles typically store the lead/intro in a single h2 tag)
    sapo_match = re.search(r'<h2[^>]*>(.*?)</h2>', html_content, re.DOTALL)
    sapo_text = ""
    if sapo_match:
        sapo_text = re.sub(r'<[^>]+>', '', sapo_match.group(1)).strip()
        sapo_text = html.unescape(sapo_text)
        
    p_matches = re.findall(r'<p[^>]*>(.*?)</p>', html_content, re.DOTALL)
    content_parts = []
    
    if sapo_text:
        content_parts.append(sapo_text)
        
    for p in p_matches:
        p_text = re.sub(r'<[^>]+>', '', p).strip()
        p_text = html.unescape(p_text)
        if len(p_text) > 40 and not any(kw in p_text for kw in ["Chia sẻ", "Tags:", "Đọc thêm", "Liên hệ", "Email"]):
            content_parts.append(p_text)
            
    content = "\n\n".join(content_parts)
    if len(content) < 200:
        print("  ⚠️ Warning: Content extracted is very short.")
        
    metadata = {
        "url": url,
        "title": title,
        "crawl_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "content": content
    }
    return metadata

def crawl_news_docs():
    urls = [
        "https://dantri.com.vn/phap-luat/truy-to-ca-si-chi-dan-nguoi-mau-an-tay-20260402122649916.htm",
        "https://dantri.com.vn/phap-luat/dien-vien-hai-huu-tin-khai-su-dung-ma-tuy-do-to-mo-20230428133813927.htm",
        "https://dantri.com.vn/phap-luat/ca-si-chu-bin-bi-tam-giu-vi-lien-quan-den-ma-tuy-20240606183158183.htm",
        "https://dantri.com.vn/phap-luat/nu-dien-vien-dong-hoai-that-cho-co-the-doi-mat-hinh-phat-nao-20230424092227771.htm",
        "https://dantri.com.vn/phap-luat/nam-nguoi-mau-bi-bat-trong-duong-day-ma-tuy-o-khu-ma-lang-20240625231501020.htm"
    ]
    
    print("\n--- Starting Task 2: Crawl News Articles ---")
    
    for i, url in enumerate(urls, 1):
        filename = f"news_article_{i}.json"
        out_path = NEWS_DIR / filename
        
        print(f"\n[{i}/5] Processing {filename}...")
        try:
            data = crawl_news_article(url, i)
            if data is None or len(data["content"]) < 100:
                print(f"❌ Failed to extract content for: {url}")
                return False
                
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print(f"  ✓ Saved to {out_path} ({len(data['content'])} chars)")
        except Exception as e:
            print(f"❌ Exception occurred during crawl: {e}")
            return False
            
    print("\n✓ Task 2: All news articles crawled successfully.")
    return True

# ----------------- Main Execution -----------------

if __name__ == "__main__":
    setup_dirs()
    
    # Run Task 1
    t1_success = download_legal_docs()
    if not t1_success:
        print("\n❌ Task 1 failed. Aborting.")
        exit(1)
        
    # Run Task 2
    t2_success = crawl_news_docs()
    if not t2_success:
        print("\n❌ Task 2 failed. Aborting.")
        exit(1)
        
    print("\n🎉 ALL DOWNLOADS COMPLETED SUCCESSFULLY!")
