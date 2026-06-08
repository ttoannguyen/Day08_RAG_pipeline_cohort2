"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.
"""

from typing import Optional


import os
import requests
import numpy as np

def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số lượng kết quả sau rerank

    Returns:
        List of top_k candidates, re-scored và sorted by rerank_score descending.
    """
    if not candidates:
        return []

    jina_key = os.getenv("JINA_API_KEY", "")
    if not jina_key or jina_key.startswith("jina_xxx") or "xxx" in jina_key:
        # Local model fallback using SentenceTransformer similarity
        print("  [Rerank Warning] JINA_API_KEY is placeholder. Falling back to local SentenceTransformer.")
        from src.task5_semantic_search import get_model
        try:
            model = get_model()
            query_emb = model.encode(query)
            
            scored_candidates = []
            for cand in candidates:
                cand_emb = model.encode(cand["content"])
                norm_q = np.linalg.norm(query_emb)
                norm_c = np.linalg.norm(cand_emb)
                sim = float(np.dot(query_emb, cand_emb) / (norm_q * norm_c)) if norm_q > 0 and norm_c > 0 else 0.0
                
                c_copy = cand.copy()
                c_copy["score"] = sim
                scored_candidates.append(c_copy)
                
            scored_candidates = sorted(scored_candidates, key=lambda x: x["score"], reverse=True)
            return scored_candidates[:top_k]
        except Exception as e:
            print(f"  [Rerank Error] Fallback failed: {e}. Returning original sorted candidates.")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_k]

    # Jina Reranker API
    try:
        response = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={"Authorization": f"Bearer {jina_key}"},
            json={
                "model": "jina-reranker-v2-base-multilingual",
                "query": query,
                "documents": [c["content"] for c in candidates],
                "top_n": top_k
            },
            timeout=10
        )
        if response.status_code == 200:
            reranked = response.json()["results"]
            return [
                {**candidates[r["index"]], "score": r["relevance_score"]}
                for r in reranked
            ]
        else:
            raise ValueError(f"Jina API error: status code {response.status_code}")
    except Exception as e:
        print(f"  [Rerank Error] Jina API request failed: {e}. Falling back to local SentenceTransformer.")
        from src.task5_semantic_search import get_model
        model = get_model()
        query_emb = model.encode(query)
        scored_candidates = []
        for cand in candidates:
            cand_emb = model.encode(cand["content"])
            norm_q = np.linalg.norm(query_emb)
            norm_c = np.linalg.norm(cand_emb)
            sim = float(np.dot(query_emb, cand_emb) / (norm_q * norm_c)) if norm_q > 0 and norm_c > 0 else 0.0
            
            c_copy = cand.copy()
            c_copy["score"] = sim
            scored_candidates.append(c_copy)
            
        scored_candidates = sorted(scored_candidates, key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.

    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

    Args:
        query_embedding: Vector embedding của query
        candidates: List of {'content': str, 'score': float, 'embedding': list, 'metadata': dict}
        top_k: Số lượng kết quả
        lambda_param: Trade-off giữa relevance (1.0) và diversity (0.0)

    Returns:
        List of top_k candidates selected by MMR.
    """
    def cosine_sim(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b) 
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    selected = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = None
        best_score = float('-inf')

        for idx in remaining:
            cand_emb = candidates[idx].get("embedding")
            if cand_emb is None:
                from src.task5_semantic_search import get_model
                model = get_model()
                cand_emb = model.encode(candidates[idx]["content"]).tolist()
                candidates[idx]["embedding"] = cand_emb

            relevance = cosine_sim(query_embedding, cand_emb)

            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sel_emb = candidates[sel_idx].get("embedding")
                sim = cosine_sim(cand_emb, sel_emb)
                max_sim_to_selected = max(max_sim_to_selected, sim)

            mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    return [candidates[i] for i in selected]


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số lượng kết quả cuối cùng
        k: Smoothing constant (default=60, từ paper Cormack et al. 2009)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    rrf_scores = {}  # content -> score
    content_map = {}  # content -> full dict

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank)
            content_map[key] = item

    # Sort by RRF score
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content, score in sorted_items[:top_k]:
        item = content_map[content].copy()
        item["score"] = score
        results.append(item)

    return results


# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",  # "cross_encoder" | "mmr" | "rrf"
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query: Câu truy vấn
        candidates: Danh sách candidates từ retrieval
        top_k: Số lượng kết quả sau rerank
        method: Phương pháp reranking

    Returns:
        List of top_k reranked candidates.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        from src.task5_semantic_search import get_model
        model = get_model()
        query_embedding = model.encode(query).tolist()
        return rerank_mmr(query_embedding, candidates, top_k)
    elif method == "rrf":
        # RRF expects multiple ranked lists. If a single list is passed, wrap it.
        return rerank_rrf([candidates], top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    # Test with dummy data
    dummy_candidates = [
        {"content": "Điều 248: Tội tàng trữ trái phép chất ma tuý", "score": 0.8, "metadata": {}},
        {"content": "Nghệ sĩ X bị bắt vì sử dụng ma tuý", "score": 0.7, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm cho tội tàng trữ", "score": 0.6, "metadata": {}},
    ]
    results = rerank("hình phạt tàng trữ ma tuý", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
