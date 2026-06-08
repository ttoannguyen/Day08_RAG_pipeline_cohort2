"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (Numpy-based LocalVectorStore)
"""

import sys
from pathlib import Path
import json

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# LỰA CHỌN CHUNKING STRATEGY:
# - CHUNK_SIZE = 500: Chọn kích thước này để các điều khoản luật pháp (thường ngắn gọn) 
#   nằm trọn vẹn trong một chunk, tránh bị xé nhỏ hoặc lẫn lộn ngữ nghĩa giữa các điều khoản khác nhau.
# - CHUNK_OVERLAP = 50: Giúp giữ tính liên tục của ngữ cảnh ở rìa các chunk, đảm bảo các câu 
#   hoặc định nghĩa không bị cắt đột ngột.
# - CHUNKING_METHOD = "recursive": Sử dụng bộ tách RecursiveCharacterTextSplitter để tách văn bản
#   theo thứ tự ưu tiên các dấu xuống dòng kép, xuống dòng đơn, và dấu chấm câu để giữ nguyên cấu trúc đoạn.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# LỰA CHỌN EMBEDDING MODEL:
# - EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": Mô hình nhúng đa ngôn ngữ gọn nhẹ (384 chiều), chạy cực nhanh trên CPU mà vẫn hỗ trợ tiếng Việt tốt.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# LỰA CHỌN VECTOR STORE:
# - VECTOR_STORE = "local_numpy": Sử dụng giải pháp lưu trữ vector nội bộ bằng Numpy và file JSON.
#   Lý do: Máy không cài đặt Docker nên không chạy được Weaviate cục bộ. Việc cài đặt ChromaDB hoặc FAISS
#   yêu cầu trình biên dịch C++ (MSVC) vốn không có sẵn trên máy Windows của bạn. local_numpy là giải pháp
#   chạy 100% bằng Python, ổn định, nhanh chóng và không phụ thuộc dịch vụ bên ngoài.
VECTOR_STORE = "local_numpy"


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    documents = []
    # Quét qua thư mục standardized để tìm các file .md
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        # Bỏ qua file lưu trữ vector chính nó nếu lưu cùng thư mục
        if "vector_store" in md_file.name:
            continue
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in str(md_file.parent) else "news"
        documents.append({
            "content": content,
            "metadata": {"source": md_file.name, "type": doc_type}
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            if not chunk_text.strip():
                continue
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "source": doc["metadata"]["source"],
                    "doc_type": doc["metadata"]["type"],
                    "chunk_index": i
                }
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    from sentence_transformers import SentenceTransformer

    print(f"Loading embedding model: {EMBEDDING_MODEL} (se tu dong tai ve neu la lan dau)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    texts = [c["content"] for c in chunks]
    print(f"Generating embeddings for {len(chunks)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn.
    """
    # Import LocalVectorStore từ module helper vừa tạo
    from src.vector_store import LocalVectorStore
    
    store = LocalVectorStore()
    store.clear()  # Xóa sạch index cũ trước khi nạp mới
    store.add_documents(chunks)
    print(f"[OK] Da luu va index xong {len(chunks)} chunks vao vector store tai: {store.filepath}")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n[OK] Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"[OK] Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"[OK] Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("[OK] Indexed to vector store successfully")


if __name__ == "__main__":
    run_pipeline()
