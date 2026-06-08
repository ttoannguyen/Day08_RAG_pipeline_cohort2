"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký: https://pageindex.ai/
SDK: https://github.com/VectifyAI/PageIndex

PageIndex nhận PDF (không phải .md). Upload từ data/landing/legal/.
"""

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from pageindex import PageIndexAPIError, PageIndexClient

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PROJECT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = PROJECT_DIR / "data" / "standardized"
LANDING_LEGAL_DIR = PROJECT_DIR / "data" / "landing" / "legal"
REGISTRY_PATH = PROJECT_DIR / "data" / "pageindex_registry.json"

POLL_INTERVAL_SEC = 10
MAX_WAIT_SEC = 600
# PDF quá lớn (vd. Bộ luật 277 trang) có thể bị PageIndex trả LimitReached
SKIP_UPLOAD_FILES = {"bo-luat-hinh-su-2015-chuong-ma-tuy.pdf"}

# Fallback miễn phí khi PageIndex cloud hết credit / không dùng được
USE_LOCAL_FALLBACK = os.getenv("PAGEINDEX_USE_LOCAL", "true").lower() in (
    "1",
    "true",
    "yes",
)

_local_sections: list[dict] | None = None
_local_bm25 = None


def _get_client() -> PageIndexClient | None:
    if not PAGEINDEX_API_KEY or PAGEINDEX_API_KEY in ("pi_xxx", "YOUR_PAGEINDEX_API_KEY"):
        return None
    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"documents": {}}


def _save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _wait_document_ready(client: PageIndexClient, doc_id: str) -> bool:
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        meta = client.get_document(doc_id)
        status = meta.get("status", "")
        if status == "completed":
            return True
        if status == "failed":
            return False
        time.sleep(POLL_INTERVAL_SEC)
    return False


def upload_documents() -> dict:
    """
    Upload PDF documents từ data/landing/legal/ lên PageIndex.
    """
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "Thiếu PAGEINDEX_API_KEY. Đăng ký tại https://pageindex.ai/ và thêm vào .env"
        )

    registry = _load_registry()
    uploaded = 0

    for pdf_path in sorted(LANDING_LEGAL_DIR.glob("*.pdf")):
        if pdf_path.name in SKIP_UPLOAD_FILES:
            print(f"  Skip (file quá lớn cho free tier): {pdf_path.name}")
            continue

        entry = registry["documents"].get(pdf_path.name)
        if entry and entry.get("status") == "completed":
            print(f"  Skip (đã upload): {pdf_path.name}")
            continue

        print(f"  Uploading: {pdf_path.name}")
        try:
            result = client.submit_document(str(pdf_path))
        except PageIndexAPIError as exc:
            print(f"  Skip {pdf_path.name}: {exc}")
            continue
        doc_id = result["doc_id"]
        registry["documents"][pdf_path.name] = {
            "doc_id": doc_id,
            "status": "processing",
        }
        _save_registry(registry)

        print(f"    doc_id={doc_id}, đang xử lý...")
        if _wait_document_ready(client, doc_id):
            registry["documents"][pdf_path.name]["status"] = "completed"
            _save_registry(registry)
            print(f"  ✓ Ready: {pdf_path.name}")
            uploaded += 1
        else:
            print(f"  ⚠ Timeout/failed: {pdf_path.name}")

    return registry


def _parse_retrieval_json(text: str) -> list[dict]:
    if not text.strip():
        return []

    fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return [{"page": None, "content": text.strip()}]


def _split_markdown_sections(content: str, source_name: str) -> list[dict]:
    """Tách markdown theo heading / Điều — mô phỏng vectorless structural retrieval."""
    pattern = r"(?=\n#{1,3}\s|\nĐiều\s+\d+|\nCHƯƠNG\s+[IVXLC\d]+|\nChương\s+\d+)"
    parts = re.split(pattern, content, flags=re.IGNORECASE)
    sections: list[dict] = []
    for i, part in enumerate(parts):
        text = part.strip()
        if len(text) < 80:
            continue
        sections.append(
            {
                "content": text,
                "metadata": {
                    "source": source_name,
                    "section_index": i,
                    "mode": "local_structure",
                },
            }
        )
    if not sections and content.strip():
        sections.append(
            {
                "content": content.strip()[:2000],
                "metadata": {
                    "source": source_name,
                    "section_index": 0,
                    "mode": "local_structure",
                },
            }
        )
    return sections


def _build_local_sections() -> list[dict]:
    global _local_sections
    if _local_sections is not None:
        return _local_sections

    sections: list[dict] = []
    if STANDARDIZED_DIR.exists():
        for md_path in sorted(STANDARDIZED_DIR.rglob("*.md")):
            content = md_path.read_text(encoding="utf-8")
            sections.extend(_split_markdown_sections(content, md_path.name))

    _local_sections = sections
    return sections


def _get_local_bm25():
    global _local_bm25
    if _local_bm25 is None:
        from rank_bm25 import BM25Okapi

        corpus = _build_local_sections()
        tokenized = [doc["content"].lower().split() for doc in corpus]
        _local_bm25 = BM25Okapi(tokenized) if tokenized else None
    return _local_bm25


def _search_local_structure(query: str, top_k: int) -> list[dict]:
    """
    Fallback FREE: BM25 trên các section markdown (không embedding, không API).
    """
    bm25 = _get_local_bm25()
    corpus = _build_local_sections()
    if not bm25 or not corpus:
        return []

    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results: list[dict] = []
    for idx in ranked:
        score = float(scores[idx])
        if score <= 0:
            break
        doc = corpus[idx]
        results.append(
            {
                "content": doc["content"],
                "score": score,
                "metadata": doc["metadata"],
                "source": "pageindex",
            }
        )
        if len(results) >= top_k:
            break
    return results


def _search_one_document(
    client: PageIndexClient, doc_id: str, filename: str, query: str
) -> list[dict]:
    if not client.is_retrieval_ready(doc_id):
        return []

    retrieval_prompt = f"""
Your job is to retrieve the raw relevant content from the document based on the user's query.

Query: {query}

Return in JSON format:
```json
[
  {{"page": <number>, "content": "<relevant text>"}}
]
```
"""

    try:
        full_response = ""
        stream = client.chat_completions(
            messages=[{"role": "user", "content": retrieval_prompt}],
            doc_id=doc_id,
            stream=True,
        )
        for chunk in stream:
            full_response += chunk
    except PageIndexAPIError as exc:
        print(f"  PageIndex search lỗi ({filename}): {exc}")
        return []

    items = _parse_retrieval_json(full_response)
    results: list[dict] = []
    for rank, item in enumerate(items):
        content = (item.get("content") or "").strip()
        if not content:
            continue
        results.append(
            {
                "content": content,
                "score": max(0.1, 1.0 - rank * 0.05),
                "metadata": {
                    "source": filename,
                    "page": item.get("page"),
                    "doc_id": doc_id,
                },
                "source": "pageindex",
            }
        )
    return results


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval: PageIndex cloud (nếu có credit) → fallback local FREE.
    """
    if not query.strip() or top_k <= 0:
        return []

    merged: list[dict] = []
    client = _get_client()
    registry = _load_registry()
    documents = registry.get("documents", {})

    if client and documents:
        for filename, info in documents.items():
            doc_id = info.get("doc_id")
            if not doc_id:
                continue
            merged.extend(_search_one_document(client, doc_id, filename, query))
        merged.sort(key=lambda item: item["score"], reverse=True)
        if merged:
            return merged[:top_k]

    if USE_LOCAL_FALLBACK:
        print("  (fallback) Dùng local structure search — miễn phí, không cần credit")
        return _search_local_structure(query, top_k)

    return []


if __name__ == "__main__":
    has_key = PAGEINDEX_API_KEY and PAGEINDEX_API_KEY not in (
        "pi_xxx",
        "YOUR_PAGEINDEX_API_KEY",
    )
    if has_key:
        print("Uploading documents (PageIndex cloud)...")
        try:
            upload_documents()
        except Exception as exc:
            print(f"  Upload skip: {exc}")
    else:
        print("Không có PAGEINDEX_API_KEY — chỉ dùng local fallback (FREE)")

    print("\nTest query:")
    results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
    for r in results:
        mode = r.get("metadata", {}).get("mode", "cloud")
        print(f"[{r['score']:.3f}] ({mode}) {r['content'][:100]}...")
