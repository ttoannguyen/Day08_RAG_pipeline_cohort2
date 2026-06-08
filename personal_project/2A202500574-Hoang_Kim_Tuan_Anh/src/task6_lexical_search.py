"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25 trên corpus chunks (cùng chunking Task 4).

Cài đặt:
    pip install rank-bm25
"""

from rank_bm25 import BM25Okapi

from src.task4_chunking_indexing import chunk_documents, load_documents

CORPUS: list[dict] = []

_bm25_index: BM25Okapi | None = None


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _load_corpus() -> list[dict]:
    global CORPUS
    if not CORPUS:
        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """
    Xây dựng BM25 index từ corpus.

    Args:
        corpus: List of {'content': str, 'metadata': dict}
    """
    tokenized_corpus = [_tokenize(doc["content"]) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def _get_bm25_index() -> tuple[BM25Okapi, list[dict]]:
    global _bm25_index
    corpus = _load_corpus()
    if _bm25_index is None:
        _bm25_index = build_bm25_index(corpus)
    return _bm25_index, corpus


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {'content': str, 'score': float, 'metadata': dict}
        Sorted by score descending.
    """
    if not query.strip() or top_k <= 0:
        return []

    bm25, corpus = _get_bm25_index()
    scores = bm25.get_scores(_tokenize(query))

    ranked_indices = sorted(
        range(len(scores)), key=lambda idx: scores[idx], reverse=True
    )

    results: list[dict] = []
    for idx in ranked_indices:
        score = float(scores[idx])
        if score <= 0:
            break
        doc = corpus[idx]
        results.append(
            {
                "content": doc["content"],
                "score": score,
                "metadata": {
                    "source": doc["metadata"].get("source", ""),
                    "doc_type": doc["metadata"].get("type", ""),
                    "chunk_index": doc["metadata"].get("chunk_index", 0),
                },
            }
        )
        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    results = lexical_search("Điều 248 tàng trữ trái phép chất ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
