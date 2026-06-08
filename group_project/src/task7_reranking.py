"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.
"""

import os
import sys
import math
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Load environment variables
STUDENT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=STUDENT_DIR / ".env")
load_dotenv(dotenv_path=STUDENT_DIR.parent / ".env")


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

    # Simple query expansion for Vietnamese drug law terminology
    query_processed = query
    query_lower = query.lower()
    if "hình thức cai nghiện" in query_lower:
        query_processed += " biện pháp cai nghiện"
    elif "biện pháp cai nghiện" in query_lower:
        query_processed += " hình thức cai nghiện"

    if "blhs" in query_lower:
        query_processed += " bộ luật hình sự"
    elif "bộ luật hình sự" in query_lower:
        query_processed += " blhs"

    jina_api_key = os.getenv("JINA_API_KEY")

    # Kiểm tra xem Jina API Key có hợp lệ không (không phải placeholder jina_xxx)
    if jina_api_key and not jina_api_key.startswith("jina_") and jina_api_key != "xxx" and len(jina_api_key) > 15:
        import requests
        try:
            print("  [INFO] Using Jina Reranker API...")
            response = requests.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {jina_api_key}"},
                json={
                    "model": "jina-reranker-v2-base-multilingual",
                    "query": query_processed,
                    "documents": [c["content"] for c in candidates],
                    "top_n": len(candidates)
                },
                timeout=15
            )
            if response.status_code == 200:
                reranked = response.json()["results"]
                res_list = []
                import re
                articles = re.findall(r"điều\s+(\d+)", query_processed, re.IGNORECASE)
                for r in reranked:
                    cand = candidates[r["index"]].copy()
                    score = float(r["relevance_score"])
                    for art in articles:
                        if re.search(rf"(?:^|\n|\s|\*\*)[Đđ]iều\s+{art}\.", cand["content"]):
                            score += 0.25
                            break
                    cand["score"] = score
                    res_list.append(cand)
                res_list.sort(key=lambda x: x["score"], reverse=True)
                return res_list[:top_k]
            else:
                print(f"  [WARNING] Jina Reranker API returned status {response.status_code}. Falling back to OpenAI Embeddings.")
        except Exception as e:
            print(f"  [WARNING] Jina Reranker API failed: {e}. Falling back to OpenAI Embeddings.")

    # Fallback: Rerank sử dụng OpenAI Embeddings để tính cosine similarity
    print("  [INFO] Reranking using OpenAI Embeddings...")
    from openai import OpenAI
    
    client = OpenAI()
    try:
        # Nhúng query
        q_emb = client.embeddings.create(input=[query_processed], model="text-embedding-3-small").data[0].embedding
        
        # Nhúng các tài liệu ứng viên
        texts = [c["content"] for c in candidates]
        res = client.embeddings.create(input=texts, model="text-embedding-3-small")
        c_embs = [d.embedding for d in res.data]
        
        def cosine_sim(a, b):
            mag_a = math.sqrt(sum(x * x for x in a))
            mag_b = math.sqrt(sum(x * x for x in b))
            if mag_a == 0.0 or mag_b == 0.0:
                return 0.0
            return sum(x * y for x, y in zip(a, b)) / (mag_a * mag_b)
            
        results = []
        import re
        articles = re.findall(r"điều\s+(\d+)", query_processed, re.IGNORECASE)
        for cand, emb in zip(candidates, c_embs):
            score = cosine_sim(q_emb, emb)
            for art in articles:
                if re.search(rf"(?:^|\n|\s|\*\*)[Đđ]iều\s+{art}\.", cand["content"]):
                    score += 0.25
                    break
            cand_copy = cand.copy()
            cand_copy["score"] = float(score)
            results.append(cand_copy)
            
        # Sắp xếp theo score giảm dần
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    except Exception as e:
        print(f"  [ERROR] Fallback OpenAI reranking failed: {e}")
        # Trả về các candidates ban đầu đã được sort theo score gốc
        sorted_candidates = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)
        return sorted_candidates[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
    query: str = ""
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
    if not candidates:
        return []

    # Điền embedding nếu bị thiếu
    missing_emb = False
    for c in candidates:
        if "embedding" not in c or c["embedding"] is None:
            missing_emb = True
            break

    if missing_emb:
        from openai import OpenAI
        client = OpenAI()
        texts = [c["content"] for c in candidates]
        res = client.embeddings.create(input=texts, model="text-embedding-3-small")
        for c, d in zip(candidates, res.data):
            c["embedding"] = d.embedding

    def cosine_sim(a, b):
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (mag_a * mag_b)

    selected = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = None
        best_score = float('-inf')

        import re
        articles = re.findall(r"điều\s+(\d+)", query, re.IGNORECASE)

        for idx in remaining:
            # Relevance to query
            relevance = cosine_sim(query_embedding, candidates[idx]["embedding"])

            # Boost if chunk contains the definition of the article in the query
            for art in articles:
                if re.search(rf"(?:^|\n|\s|\*\*)[Đđ]iều\s+{art}\.", candidates[idx]["content"]):
                    relevance += 0.25
                    break

            # Max similarity to already selected
            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sim = cosine_sim(candidates[idx]["embedding"], candidates[sel_idx]["embedding"])
                max_sim_to_selected = max(max_sim_to_selected, sim)

            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)
        else:
            break

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
        k: Smoothing constant (default=60)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    rrf_scores = {}  # content -> score
    content_map = {}  # content -> full dict

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in content_map:
                content_map[key] = item

    # Sort by RRF score
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content, score in sorted_items[:top_k]:
        item = content_map[content].copy()
        item["score"] = score
        results.append(item)

    return results


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
        from openai import OpenAI
        client = OpenAI()
        query_embedding = client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        ).data[0].embedding
        return rerank_mmr(query_embedding, candidates, top_k, query=query)
    elif method == "rrf":
        # Nếu chỉ có 1 danh sách, xem nó là list of 1 list
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
    print("Testing rerank...")
    results = rerank("hình phạt tàng trữ ma tuý", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
