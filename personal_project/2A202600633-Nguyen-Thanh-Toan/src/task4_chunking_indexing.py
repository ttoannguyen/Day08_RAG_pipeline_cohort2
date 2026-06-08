"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (Weaviate khuyến cáo)

Chunking options (langchain-text-splitters):
    - RecursiveCharacterTextSplitter: an toàn, phổ biến
    - MarkdownHeaderTextSplitter: tốt cho file có heading
    - SemanticChunker: dùng embedding để tách (nâng cao)

Embedding model options:
    - sentence-transformers/all-MiniLM-L6-v2 (384 dim, nhẹ)
    - BAAI/bge-m3 (1024 dim, multilingual, tốt cho tiếng Việt)
    - OpenAI text-embedding-3-small (1536 dim, API)

Vector store options:
    - Weaviate (khuyến cáo: hỗ trợ hybrid search built-in)
    - ChromaDB (đơn giản, local)
    - FAISS (chỉ dense search)

Cài đặt:
    pip install langchain-text-splitters sentence-transformers weaviate-client
"""

from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# Chọn chunking strategy và giải thích vì sao
CHUNK_SIZE = 500        # Chọn 500 ký tự để cân bằng giữa lượng thông tin ngữ cảnh và độ mịn của kết quả tìm kiếm (khoảng 70-100 từ tiếng Việt)
CHUNK_OVERLAP = 50      # Chọn 50 ký tự (10% của chunk size) để đảm bảo không bị đứt đoạn thông tin giữa các chunk kế tiếp
CHUNKING_METHOD = "recursive"  # Dùng "recursive" (RecursiveCharacterTextSplitter) để ngắt dòng thông minh theo các ký tự phân tách tự nhiên như xuống dòng, dấu câu

# Chọn embedding model và giải thích
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Sử dụng all-MiniLM-L6-v2 vì nó cực kỳ gọn nhẹ (khoảng 90MB), giúp chạy local nhanh, tối ưu hóa tốc độ tải và xử lý tài liệu.
EMBEDDING_DIM = 384

# Chọn vector store
VECTOR_STORE = "chromadb"  # Sử dụng ChromaDB để chạy local dạng file-based (in-process) ổn định, không cần server/docker phụ thuộc


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
        return documents
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in str(md_file.relative_to(STANDARDIZED_DIR)) else "news"
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
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn.
    """
    if VECTOR_STORE == "chromadb":
        import chromadb
        from pathlib import Path

        db_dir = Path(__file__).parent.parent / "data" / "chroma"
        db_dir.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(db_dir))

        # Delete collection if it exists to start fresh
        try:
            client.delete_collection("DrugLawDocs")
        except Exception:
            pass

        collection = client.create_collection(name="DrugLawDocs", metadata={"hnsw:space": "cosine"})

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            # Create a unique ID for each chunk
            chunk_id = f"{chunk['metadata']['source']}_chunk_{chunk['metadata']['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            embeddings.append(chunk["embedding"])
            metadatas.append({
                "source": chunk["metadata"]["source"],
                "type": chunk["metadata"]["type"],
                "chunk_index": chunk["metadata"]["chunk_index"]
            })

        if ids:
            # Batch add documents
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            print(f"  → Indexed {len(ids)} chunks to ChromaDB 'DrugLawDocs'")

    elif VECTOR_STORE == "weaviate":
        import weaviate
        from weaviate.classes.config import Configure, Property, DataType

        client = weaviate.connect_to_local()
        # Tạo collection
        collection = client.collections.create(
            name="DrugLawDocs",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="doc_type", data_type=DataType.TEXT),
            ]
        )

        # Insert chunks
        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                batch.add_object(
                    properties={
                        "content": chunk["content"],
                        "source": chunk["metadata"]["source"],
                        "doc_type": chunk["metadata"]["type"]
                    },
                    vector=chunk["embedding"]
                )
        print(f"  → Indexed {len(chunks)} chunks to Weaviate 'DrugLawDocs'")
    else:
        raise ValueError(f"Unsupported VECTOR_STORE: {VECTOR_STORE}")


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
