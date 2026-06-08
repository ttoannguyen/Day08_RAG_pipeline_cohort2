"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25

BM25 hoạt động thế nào:
    - Term Frequency (TF): từ xuất hiện nhiều trong document → điểm cao
    - Inverse Document Frequency (IDF): từ hiếm → quan trọng hơn
    - Document length normalization: document dài không bị ưu tiên quá mức
    - Formula: score(q,d) = Σ IDF(qi) * (tf(qi,d) * (k1+1)) / (tf(qi,d) + k1*(1-b+b*|d|/avgdl))
    - k1=1.5 (term saturation), b=0.75 (length normalization)
"""

import sys
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from src.vector_store import LocalVectorStore

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_corpus() -> list[dict]:
    store = LocalVectorStore()
    return store.data

CORPUS = load_corpus()

def tokenize(text: str) -> list[str]:
    return text.lower().split()

def build_bm25_index(corpus: list[dict]):
    """
    Xây dựng BM25 index từ corpus.
    """
    tokenized_corpus = [tokenize(doc["content"]) for doc in corpus]
    return BM25Okapi(tokenized_corpus)

bm25 = None
if CORPUS:
    bm25 = build_bm25_index(CORPUS)

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
    global bm25
    corpus = load_corpus()
    if not corpus:
        return []
        
    # Lazy initialization or update if corpus changed
    if bm25 is None or len(corpus) != len(CORPUS):
        bm25 = build_bm25_index(corpus)
        
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    
    sorted_indices = np.argsort(scores)[::-1]
    
    results = []
    for idx in sorted_indices[:top_k]:
        if scores[idx] > 0:
            results.append({
                "content": corpus[idx]["content"],
                "score": float(scores[idx]),
                "metadata": corpus[idx]["metadata"]
            })
    return results


if __name__ == "__main__":
    # Test
    results = lexical_search("Điều 248 tàng trữ trái phép chất ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
