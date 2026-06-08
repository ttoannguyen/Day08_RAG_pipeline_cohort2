"""
Task 7 — Reranking Module.

Cross-encoder: Jina Reranker API (nếu có JINA_API_KEY), fallback overlap local.
Cũng hỗ trợ MMR và RRF.
"""

import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _overlap_score(query: str, content: str) -> float:
    """Fallback reranker: tỷ lệ từ query xuất hiện trong document."""
    q_tokens = query.lower().split()
    if not q_tokens:
        return 0.0
    content_lower = content.lower()
    hits = sum(1 for token in q_tokens if token in content_lower)
    return hits / len(q_tokens)


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder (Jina API) hoặc overlap fallback.
    """
    if not candidates or top_k <= 0:
        return []

    top_k = min(top_k, len(candidates))
    api_key = os.getenv("JINA_API_KEY")

    if api_key and api_key != "jina_xxx":
        try:
            response = requests.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "jina-reranker-v2-base-multilingual",
                    "query": query,
                    "documents": [c["content"] for c in candidates],
                    "top_n": top_k,
                },
                timeout=30,
            )
            response.raise_for_status()
            reranked = response.json().get("results", [])
            results: list[dict] = []
            for item in reranked:
                idx = item["index"]
                out = {**candidates[idx], "score": float(item["relevance_score"])}
                results.append(out)
            return results
        except Exception:
            pass

    scored = []
    for candidate in candidates:
        out = {**candidate, "score": _overlap_score(query, candidate["content"])}
        scored.append(out)

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.
    """
    if not candidates or top_k <= 0:
        return []

    top_k = min(top_k, len(candidates))
    selected: list[int] = []
    remaining = list(range(len(candidates)))

    for _ in range(top_k):
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            emb = candidates[idx].get("embedding")
            if emb:
                relevance = _cosine_similarity(query_embedding, emb)
            else:
                relevance = candidates[idx].get("score", 0.0)

            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sel_emb = candidates[sel_idx].get("embedding")
                if emb and sel_emb:
                    sim = _cosine_similarity(emb, sel_emb)
                    max_sim_to_selected = max(max_sim_to_selected, sim)

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is None:
            break
        selected.append(best_idx)
        remaining.remove(best_idx)

    results = []
    for idx in selected:
        out = {**candidates[idx], "score": float(candidates[idx].get("score", 0.0))}
        results.append(out)
    return results


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.
    """
    if not ranked_lists or top_k <= 0:
        return []

    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            content_map[key] = item

    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results: list[dict] = []
    for content, score in sorted_items[:top_k]:
        item = {**content_map[content], "score": score}
        results.append(item)
    return results


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",
    query_embedding: Optional[list[float]] = None,
    ranked_lists: Optional[list[list[dict]]] = None,
) -> list[dict]:
    """
    Unified reranking interface.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "mmr":
        if query_embedding is None:
            from src.task4_chunking_indexing import embed_query

            query_embedding = embed_query(query)
        return rerank_mmr(query_embedding, candidates, top_k)
    if method == "rrf":
        if not ranked_lists:
            raise ValueError("RRF requires ranked_lists")
        return rerank_rrf(ranked_lists, top_k)
    raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    dummy_candidates = [
        {"content": "Điều 248: Tội tàng trữ trái phép chất ma tuý", "score": 0.8, "metadata": {}},
        {"content": "Nghệ sĩ X bị bắt vì sử dụng ma tuý", "score": 0.7, "metadata": {}},
        {"content": "Hình phạt tù từ 2-7 năm cho tội tàng trữ", "score": 0.6, "metadata": {}},
    ]
    results = rerank("hình phạt tàng trữ ma tuý", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
