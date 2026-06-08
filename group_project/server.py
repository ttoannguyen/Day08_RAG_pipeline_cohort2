import os
import sys
import time
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Configure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Add current directory to path to resolve src imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environmental variables
load_dotenv(dotenv_path=project_root / ".env")
load_dotenv(dotenv_path=project_root.parent / ".env")

# Import modular RAG components
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank, rerank_rrf
from src.task8_pageindex_vectorless import pageindex_search
from src.task10_generation import reorder_for_llm, format_context

app = FastAPI(title="DrugLaw RAG API Server")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: list[ChatMessage] = []
    top_k: int = 5
    score_threshold: float = 0.3
    use_reranking: bool = True
    rerank_method: str = "cross_encoder"
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.3
    system_prompt: str = ""
    max_tokens: int = 65000


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    start_time = time.time()
    
    # 1. Execute Searches
    try:
        dense_results = semantic_search(req.query, top_k=req.top_k * 4)
    except Exception as e:
        print(f"[ERROR] Semantic search failed: {e}")
        dense_results = []
        
    try:
        sparse_results = lexical_search(req.query, top_k=req.top_k * 4)
    except Exception as e:
        print(f"[ERROR] Lexical search failed: {e}")
        sparse_results = []
        
    # 2. RRF Fusion
    merged_results = rerank_rrf([dense_results, sparse_results], top_k=req.top_k * 4)
    for item in merged_results:
        item["source"] = "hybrid"
        
    # 3. Reranking
    if req.use_reranking and merged_results:
        try:
            final_results = rerank(req.query, merged_results, top_k=req.top_k, method=req.rerank_method)
        except Exception as e:
            print(f"[ERROR] Reranking failed: {e}")
            final_results = merged_results[:req.top_k]
    else:
        final_results = merged_results[:req.top_k]
        
    # 4. Fallback Logic
    best_score = final_results[0]["score"] if final_results else 0.0
    fallback_active = False
    fallback_reason = ""
    
    if not final_results or best_score < req.score_threshold:
        fallback_active = True
        fallback_reason = f"Best score ({best_score:.3f}) < threshold ({req.score_threshold})"
        print(f"[INFO] Triggering PageIndex fallback. Reason: {fallback_reason}")
        try:
            final_results = pageindex_search(req.query, top_k=req.top_k)
        except Exception as e:
            print(f"[ERROR] PageIndex fallback failed: {e}")
            
    # 5. Document Reordering
    reordered_chunks = reorder_for_llm(final_results)
    
    elapsed_time_ms = int((time.time() - start_time) * 1000)
    
    # Serialization helper
    def get_url_from_file(filename: str, doc_type: str) -> str:
        if not filename:
            return ""
        safe_name = Path(filename).name
        if doc_type == "news":
            file_path = project_root / "data" / "standardized" / "news" / safe_name
        else:
            file_path = project_root / "data" / "standardized" / "legal" / safe_name
            
        if file_path.exists():
            try:
                import re
                content = file_path.read_text(encoding="utf-8")
                # Find **Source:** or Source: URL
                match = re.search(r'(?i)\*\*Source:\*\*\s*(https?://[^\s\)\*\]]+)', content)
                if match:
                    return match.group(1).strip()
                match_fallback = re.search(r'(?i)Source:\s*(https?://[^\s\)\*\]]+)', content)
                if match_fallback:
                    return match_fallback.group(1).strip()
            except Exception as e:
                print(f"[ERROR] Failed to extract source URL from {filename}: {e}")
        return ""

    def serialize_results(results_list):
        serialized = []
        for r in results_list:
            meta = r.get("metadata", {}).copy()
            if "url" not in meta or not meta["url"]:
                doc_type = meta.get("type", "unknown")
                source_file = meta.get("source", "")
                url = get_url_from_file(source_file, doc_type)
                if url:
                    meta["url"] = url
            serialized.append({
                "content": r.get("content", ""),
                "score": float(r.get("score", 0.0)),
                "metadata": meta,
                "source": r.get("source", "unknown")
            })
        return serialized

    # Construct prompts for LLM and expose in metadata
    context_str = format_context(reordered_chunks)
    default_system_prompt = """Answer the question in Vietnamese.

If the question is a general greeting (e.g., "xin chào", "hello", "hi") or asking about your identity (e.g., "bạn là ai", "tên gì"), reply politely directly as the DrugLaw RAG Assistant.

For all other questions concerning drug laws, legal documents, or celebrity news:
- Only use information from the provided context.
- For every statement of fact or claim, immediately insert a citation in brackets linking to the specific source (e.g., [Luật Phòng chống ma tuý 2021, Điều 3] or [VnExpress, 2024]).
- If the information is not explicitly stated in the provided context, state 'Tôi không thể xác minh thông tin này từ nguồn hiện có' rather than guessing.
- Structure your answer with clear paragraphs."""

    system_prompt_to_use = req.system_prompt.strip() if req.system_prompt and req.system_prompt.strip() else default_system_prompt
    user_message = f"Context:\n{context_str}\n\n---\n\nQuestion: {req.query}"

    # Pre-compiled metadata payload
    metadata = {
        "latency_ms": elapsed_time_ms,
        "fallback_active": fallback_active,
        "fallback_reason": fallback_reason,
        "lexical": serialize_results(sparse_results[:5]),
        "semantic": serialize_results(dense_results[:5]),
        "merged": serialize_results(merged_results[:5]),
        "reranked": serialize_results(final_results),
        "final_chunks": serialize_results(reordered_chunks),
        "constructed_system_prompt": system_prompt_to_use,
        "constructed_user_prompt": user_message
    }

    # Stream generator yielding SSE events
    def event_generator():
        # First send the RAG pipeline metadata
        yield f"data: __METADATA__:{json.dumps(metadata)}\n\n"
        
        from openai import OpenAI
        client = OpenAI()
        
        # Build messages with history
        messages = [{"role": "system", "content": system_prompt_to_use}]
        for msg in req.history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        # Determine max_tokens to send to the API call
        max_tokens_to_send = req.max_tokens
        openai_base_url = os.getenv("OPENAI_BASE_URL", "")
        if "openrouter.ai" not in openai_base_url:
            # Cap standard OpenAI model outputs to avoid 400 Bad Request errors
            if "gpt-4o-mini" in req.llm_model:
                max_tokens_to_send = min(max_tokens_to_send, 16384)
            elif "gpt-4o" in req.llm_model:
                max_tokens_to_send = min(max_tokens_to_send, 4096)

        try:
            response = client.chat.completions.create(
                model=req.llm_model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=max_tokens_to_send,
                stream=True
            )
            for chunk in response:
                token = chunk.choices[0].delta.content
                if token:
                    # Escape newlines to prevent breaking the SSE line-by-line parser
                    escaped_token = token.replace("\n", "\\n")
                    yield f"data: {escaped_token}\n\n"
        except Exception as e:
            print(f"[ERROR] LLM Streaming failed: {e}")
            yield f"data: ❌ [ERROR] Lỗi gọi mô hình Generation: {e}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/document")
def get_document(filename: str):
    safe_name = Path(filename).name
    legal_path = project_root / "data" / "standardized" / "legal" / safe_name
    news_path = project_root / "data" / "standardized" / "news" / safe_name
    
    if legal_path.exists():
        content = legal_path.read_text(encoding="utf-8")
        return {"content": content, "filename": safe_name, "type": "legal"}
    elif news_path.exists():
        content = news_path.read_text(encoding="utf-8")
        return {"content": content, "filename": safe_name, "type": "news"}
    else:
        raise HTTPException(status_code=404, detail="Document not found")


# Mount static directory to serve HTML/CSS/JS frontend
static_dir = project_root / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    # Ensure static directory exists
    static_dir.mkdir(exist_ok=True)
    print("FastAPI serving static files from:", static_dir)
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
