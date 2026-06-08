import json
import numpy as np
from pathlib import Path

class LocalVectorStore:
    def __init__(self, filepath="data/standardized/vector_store.json"):
        self.filepath = Path(filepath)
        self.data = []
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[Warning] Failed to load vector store from {self.filepath}: {e}")
                self.data = []
        else:
            self.data = []

    def save(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_documents(self, chunks_with_embeddings: list[dict]):
        self.data.extend(chunks_with_embeddings)
        self.save()

    def clear(self):
        self.data = []
        if self.filepath.exists():
            self.filepath.unlink()

    def similarity_search(self, query_embedding: list[float], top_k: int = 10) -> list[dict]:
        if not self.data:
            return []
        
        # Convert embeddings to numpy array
        embeddings = np.array([item["embedding"] for item in self.data])
        q_emb = np.array(query_embedding)
        
        # Compute cosine similarity
        norm_embeddings = np.linalg.norm(embeddings, axis=1)
        norm_q = np.linalg.norm(q_emb)
        
        if norm_q == 0:
            return []
            
        dot_products = np.dot(embeddings, q_emb)
        similarities = dot_products / (norm_embeddings * norm_q)
        
        # Replace NaNs with 0
        similarities = np.nan_to_num(similarities)
        
        # Sort indices descending
        sorted_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in sorted_indices[:top_k]:
            item = self.data[idx]
            results.append({
                "content": item["content"],
                "score": float(similarities[idx]),
                "metadata": item["metadata"]
            })
        return results
