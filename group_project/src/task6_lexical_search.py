"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from .task4_chunking_indexing import load_documents, chunk_documents

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Load environment variables
STUDENT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=STUDENT_DIR / ".env")
load_dotenv(dotenv_path=STUDENT_DIR.parent / ".env")

# Load corpus dynamically
try:
    docs = load_documents()
    CORPUS = chunk_documents(docs)
except Exception as e:
    print(f"Error loading corpus: {e}")
    CORPUS = []

bm25_instance = None


def get_bm25_index():
    """Lazy load BM25 index."""
    global bm25_instance, CORPUS
    if bm25_instance is None:
        if not CORPUS:
            docs = load_documents()
            CORPUS = chunk_documents(docs)
        # Tokenize (lowercase and split)
        tokenized_corpus = [doc["content"].lower().split() for doc in CORPUS]
        bm25_instance = BM25Okapi(tokenized_corpus)
    return bm25_instance


def build_bm25_index(corpus: list[dict]):
    """
    Xây dựng BM25 index từ corpus.

    Args:
        corpus: List of {'content': str, 'metadata': dict}
    """
    tokenized_corpus = [doc["content"].lower().split() for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score
            'metadata': dict
        }
        Sorted by score descending.
    """
    if not query or not CORPUS:
        return []

    # Simple query expansion for Vietnamese drug law terminology
    query_processed = query
    query_lower = query.lower()
    if "hình thức cai nghiện" in query_lower:
        query_processed += " biện pháp cai nghiện"
    elif "biện pháp cai nghiện" in query_lower:
        query_processed += " hình thức cai nghiện"

    if "blhs" in query_lower:
        query_processed += " bộ luật hình sự"
    elif "bộ luật hình sự" in query_lower:
        query_processed += " blhs"

    bm25 = get_bm25_index()
    tokenized_query = query_processed.lower().split()
    scores = bm25.get_scores(tokenized_query)

    import re
    articles = re.findall(r"điều\s+(\d+)", query_processed, re.IGNORECASE)

    # Score and apply article header boosting before sorting to avoid candidate truncation
    scored_items = []
    for idx, score in enumerate(scores):
        content = CORPUS[idx]["content"]
        boosted_score = float(score)
        
        for art in articles:
            if re.search(rf"(?:^|\n|\s|\*\*)[Đđ]iều\s+{art}\.", content):
                boosted_score += 20.0
                break
        
        scored_items.append((idx, boosted_score))

    scored_items.sort(key=lambda x: x[1], reverse=True)
    top_indices = scored_items[:top_k]

    results = []
    for idx, score in top_indices:
        results.append({
            "content": CORPUS[idx]["content"],
            "score": score,
            "metadata": CORPUS[idx]["metadata"]
        })
    return results


if __name__ == "__main__":
    # Test
    query_str = "Điều 248 tàng trữ trái phép chất ma tuý"
    print(f"Querying lexical search (BM25): '{query_str}'")
    results = lexical_search(query_str, top_k=5)
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r['score']:.4f}] (Source: {r['metadata'].get('source')})")
        print(f"   Content: {r['content'][:150]}...\n")
