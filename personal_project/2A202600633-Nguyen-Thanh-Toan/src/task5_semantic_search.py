"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""


import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.task4_chunking_indexing import EMBEDDING_MODEL

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    # Bước 1: Embed query bằng cùng model ở Task 4
    model = get_model()
    query_embedding = model.encode(query).tolist()

    # Bước 2: Query vector store (cosine similarity)
    db_dir = Path(__file__).parent.parent / "data" / "chroma"
    client = chromadb.PersistentClient(path=str(db_dir))

    try:
        collection = client.get_collection(name="DrugLawDocs")
    except Exception:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # Bước 3: Return top_k results
    out = []
    if not results or not results['documents'] or len(results['documents'][0]) == 0:
        return out

    documents = results['documents'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]

    for doc, dist, meta in zip(documents, distances, metadatas):
        # ChromaDB distance is L2 or Cosine distance
        # space: cosine -> distance = 1 - cosine_similarity
        # similarity = 1 - distance
        score = 1.0 - dist
        out.append({
            "content": doc,
            "score": score,
            "metadata": {
                "source": meta.get("source"),
                "type": meta.get("type"),
                "chunk_index": meta.get("chunk_index")
            }
        })

    # Đảm bảo được sắp xếp giảm dần theo score
    out = sorted(out, key=lambda x: x["score"], reverse=True)
    return out


if __name__ == "__main__":
    # Test
    results = semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
