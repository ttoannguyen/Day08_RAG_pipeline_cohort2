"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (ChromaDB)

Cài đặt:
    pip install langchain-text-splitters sentence-transformers chromadb openai python-dotenv
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Load environment variables from student directory .env or parent directory .env
STUDENT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=STUDENT_DIR / ".env")
load_dotenv(dotenv_path=STUDENT_DIR.parent / ".env")
load_dotenv(dotenv_path=STUDENT_DIR.parent.parent / ".env")

STANDARDIZED_DIR = STUDENT_DIR / "data" / "standardized"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# Chọn chunking strategy và giải thích vì sao
CHUNK_SIZE = 500        # Kích thước chunk 500 ký tự là độ dài vừa phải để giữ trọn vẹn ngữ nghĩa câu và đoạn văn ngắn mà không làm loãng thông tin.
CHUNK_OVERLAP = 50      # Trùng lặp 50 ký tự giữa các chunk liền kề giúp bảo toàn ngữ cảnh liên kết tại điểm cắt ranh giới.
CHUNKING_METHOD = "recursive"  # Dùng recursive splitter vì nó phân tách thông minh theo thứ tự ưu tiên đoạn (\n\n), dòng (\n), câu (. ) và từ.

# Chọn embedding model và giải thích
EMBEDDING_MODEL = "text-embedding-3-small"  # Sử dụng model API của OpenAI để xử lý nhanh chóng, không tốn tài nguyên chạy offline và độ chính xác cao.
EMBEDDING_DIM = 1536

# Chọn vector store
VECTOR_STORE = "chromadb"  # Chọn ChromaDB vì nhẹ nhàng, hoạt động local in-memory/persistent trên Windows dễ dàng mà không cần Docker.


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
    if not STANDARDIZED_DIR.exists():
        print(f"Thư mục không tồn tại: {STANDARDIZED_DIR}")
        return documents

    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        # Bỏ qua các file ẩn/tạm
        if md_file.name.startswith(".") or ".temp." in md_file.name:
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            doc_type = "legal" if "legal" in str(md_file.as_posix()) else "news"
            documents.append({
                "content": content,
                "metadata": {"source": md_file.name, "type": doc_type}
            })
        except Exception as e:
            print(f"Error reading {md_file.name}: {e}")

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
            chunks.append({
                "content": chunk_text,
                "metadata": {**doc["metadata"], "chunk_index": i}
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    if not chunks:
        return []

    client = OpenAI()
    texts = [c["content"] for c in chunks]
    
    # Gửi batch lên OpenAI để tăng tốc độ nhúng
    batch_size = 100
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        response = client.embeddings.create(
            input=batch_texts,
            model=EMBEDDING_MODEL
        )
        embeddings.extend([data.embedding for data in response.data])

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
        
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn.
    """
    import chromadb
    chroma_path = STUDENT_DIR / "data" / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_path.resolve()))
    
    collection_name = "druglaw_docs"
    
    # Xóa collection cũ nếu tồn tại để reset database
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
        
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    documents = [c["content"] for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    # Lưu batch vào ChromaDB
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size]
        )
    print(f"  [OK] Saved {len(chunks)} chunks to ChromaDB at {chroma_path}")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("✓ Indexed to vector store")


if __name__ == "__main__":
    run_pipeline()
