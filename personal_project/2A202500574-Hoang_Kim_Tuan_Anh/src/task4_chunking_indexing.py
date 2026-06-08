"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (Weaviate khuyến cáo)

Cài đặt:
    pip install langchain-text-splitters openai chromadb weaviate-client python-dotenv
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = PROJECT_DIR / "data" / "standardized"
CHROMA_DIR = PROJECT_DIR / "data" / "chroma_db"

# =============================================================================
# CONFIGURATION
# =============================================================================

# RecursiveCharacterTextSplitter: an toàn với văn bản pháp luật OCR (đoạn dài,
# ít heading). 500 ký tự ≈ 1–2 điều/khoản — đủ ngữ cảnh cho retrieval.
CHUNK_SIZE = 500
# Overlap 50 ký tự (~10%) giữ mạch ý giữa các chunk liền kề.
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# OpenAI text-embedding-3-small: API ổn định, hỗ trợ tiếng Việt, dim 1536.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBED_BATCH_SIZE = 100

# ChromaDB local mặc định (không cần Docker). Đổi "weaviate" nếu có Weaviate Cloud.
VECTOR_STORE = "chromadb"
COLLECTION_NAME = "DrugLawDocs"

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Thiếu OPENAI_API_KEY. Copy .env.example → .env và điền API key."
            )
        from openai import OpenAI

        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _embed_texts_openai(texts: list[str], show_progress: bool = True) -> list[list[float]]:
    client = _get_openai_client()
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        if show_progress:
            end = min(start + EMBED_BATCH_SIZE, len(texts))
            print(f"  Embedding {end}/{len(texts)}...")

        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        ordered = sorted(response.data, key=lambda item: item.index)
        all_embeddings.extend(item.embedding for item in ordered)

    return all_embeddings


def _embed_texts_local(texts: list[str], show_progress: bool = True) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("BAAI/bge-m3")
    embeddings = model.encode(
        texts, show_progress_bar=show_progress, normalize_embeddings=True
    )
    return [emb.tolist() for emb in embeddings]


def embed_texts(texts: list[str], show_progress: bool = True) -> list[list[float]]:
    """Embed text: OpenAI API nếu có key, không thì fallback BGE-M3 local."""
    if not texts:
        return []

    if os.getenv("OPENAI_API_KEY"):
        return _embed_texts_openai(texts, show_progress)

    print("  (fallback) Không có OPENAI_API_KEY → dùng BAAI/bge-m3 local")
    return _embed_texts_local(texts, show_progress)


def embed_query(query: str) -> list[float]:
    """Embed một câu query (Task 5 semantic search)."""
    return embed_texts([query], show_progress=False)[0]


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        doc_type = "legal" if "legal" in md_file.parts else "news"
        documents.append(
            {
                "content": content,
                "metadata": {"source": md_file.name, "type": doc_type},
            }
        )
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
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            text = chunk_text.strip()
            if not text:
                continue
            chunks.append(
                {
                    "content": text,
                    "metadata": {**doc["metadata"], "chunk_index": i},
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    if not chunks:
        return chunks

    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
    return chunks


def _index_weaviate(chunks: list[dict]) -> None:
    import weaviate
    from weaviate.classes.config import Configure, Property, DataType

    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")

    if url and api_key:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key),
        )
    else:
        client = weaviate.connect_to_local()

    try:
        if client.collections.exists(COLLECTION_NAME):
            client.collections.delete(COLLECTION_NAME)

        collection = client.collections.create(
            name=COLLECTION_NAME,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="doc_type", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
            ],
        )

        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                meta = chunk["metadata"]
                batch.add_object(
                    properties={
                        "content": chunk["content"],
                        "source": meta.get("source", ""),
                        "doc_type": meta.get("type", ""),
                        "chunk_index": meta.get("chunk_index", 0),
                    },
                    vector=chunk["embedding"],
                )
    finally:
        client.close()


def _index_chromadb(chunks: list[dict]) -> None:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu chromadb. Chạy: pip install chromadb"
        ) from exc

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.add(
            ids=[f"chunk_{start + i}" for i in range(len(batch))],
            documents=[c["content"] for c in batch],
            embeddings=[c["embedding"] for c in batch],
            metadatas=[
                {
                    "source": c["metadata"].get("source", ""),
                    "type": c["metadata"].get("type", ""),
                    "chunk_index": c["metadata"].get("chunk_index", 0),
                }
                for c in batch
            ],
        )


def index_to_vectorstore(chunks: list[dict]):
    """Lưu chunks vào vector store đã chọn (Weaviate hoặc ChromaDB fallback)."""
    if not chunks:
        print("  (skip) Không có chunk để index")
        return

    if VECTOR_STORE == "weaviate":
        try:
            _index_weaviate(chunks)
            print(f"  Indexed {len(chunks)} chunks → Weaviate ({COLLECTION_NAME})")
            return
        except Exception as exc:
            print(f"  Weaviate không khả dụng ({exc}), dùng ChromaDB local...")

    _index_chromadb(chunks)
    print(f"  Indexed {len(chunks)} chunks → ChromaDB ({CHROMA_DIR})")


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
