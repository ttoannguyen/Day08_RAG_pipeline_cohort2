"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Load environment variables
STUDENT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=STUDENT_DIR / ".env")
load_dotenv(dotenv_path=STUDENT_DIR.parent / ".env")


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
    if not query:
        return []

    # 1. Embed query sử dụng cùng model OpenAI ở Task 4
    client = OpenAI()
    response = client.embeddings.create(
        input=[query],
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # 2. Kết nối tới ChromaDB
    import chromadb
    chroma_path = STUDENT_DIR / "data" / "chroma_db"
    
    # Kiểm tra xem DB đã tồn tại chưa
    if not chroma_path.exists():
        print(f"  [WARNING] ChromaDB folder not found at {chroma_path}. Return empty list.")
        return []
        
    chroma_client = chromadb.PersistentClient(path=str(chroma_path.resolve()))
    
    collection_name = "druglaw_docs"
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception:
        print(f"  [WARNING] Collection '{collection_name}' not found. Return empty list.")
        return []

    # 3. Query vector store
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    formatted_results = []
    if results and 'ids' in results and results['ids'] and results['ids'][0]:
        ids = results['ids'][0]
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results['metadatas'] else [{} for _ in ids]
        distances = results['distances'][0] if results['distances'] else [0.0 for _ in ids]

        for i in range(len(ids)):
            # Vì ta cấu hình space="cosine", distance = 1 - cosine_similarity.
            # Do đó similarity_score = 1.0 - distance.
            similarity_score = 1.0 - distances[i]
            
            formatted_results.append({
                "content": documents[i],
                "score": similarity_score,
                "metadata": metadatas[i] or {}
            })

    # Sắp xếp giảm dần theo score
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    return formatted_results


if __name__ == "__main__":
    # Test thử
    query_str = "hình phạt cho tội tàng trữ ma tuý"
    print(f"Querying semantic search: '{query_str}'")
    results = semantic_search(query_str, top_k=5)
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r['score']:.4f}] (Source: {r['metadata'].get('source')})")
        print(f"   Content: {r['content'][:150]}...\n")
