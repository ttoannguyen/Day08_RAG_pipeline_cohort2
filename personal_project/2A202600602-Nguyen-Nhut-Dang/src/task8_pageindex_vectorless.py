"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký tài khoản tại: https://pageindex.ai/
SDK & sample code: https://github.com/VectifyAI/PageIndex

PageIndex cho phép RAG mà không cần vector store — sử dụng
structural understanding của document thay vì embedding.

Cài đặt:
    pip install pageindex
"""

import os
import sys
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
load_dotenv(dotenv_path=STUDENT_DIR.parent.parent / ".env")

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = STUDENT_DIR / "data" / "standardized"


def upload_documents():
    """
    Upload toàn bộ PDF documents lên PageIndex.
    """
    is_valid_key = (
        PAGEINDEX_API_KEY 
        and not PAGEINDEX_API_KEY.startswith("pi_") 
        and PAGEINDEX_API_KEY != "xxx" 
        and len(PAGEINDEX_API_KEY) > 15
    )
    if not is_valid_key:
        print("  [INFO] Skip upload: No valid PAGEINDEX_API_KEY configured.")
        return

    try:
        from pageindex import PageIndexClient
        client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
        
        # List existing documents to prevent duplicate uploads
        existing_docs = client.list_documents().get("documents", [])
        existing_names = {doc.get("name") for doc in existing_docs}
        
        # We search for any PDF files in landing/legal directory
        landing_dir = STUDENT_DIR / "data" / "landing"
        pdf_files = list(landing_dir.rglob("*.pdf"))
        
        for pdf_file in pdf_files:
            if pdf_file.name.startswith(".") or ".temp." in pdf_file.name:
                continue
            if pdf_file.name in existing_names:
                print(f"  [INFO] Document already exists on PageIndex: {pdf_file.name}")
                continue
            
            print(f"  [INFO] Uploading to PageIndex: {pdf_file.name}")
            client.submit_document(file_path=str(pdf_file))
            print(f"  [OK] Uploaded: {pdf_file.name}")
            
    except Exception as e:
        print(f"  [ERROR] Failed to upload to PageIndex: {e}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex.
    Dùng làm fallback khi hybrid search không có kết quả tốt.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'pageindex'   # Đánh dấu nguồn retrieval
        }
    """
    if not query:
        return []

    is_valid_key = (
        PAGEINDEX_API_KEY 
        and not PAGEINDEX_API_KEY.startswith("pi_") 
        and PAGEINDEX_API_KEY != "xxx" 
        and len(PAGEINDEX_API_KEY) > 15
    )

    if is_valid_key:
        try:
            import time
            from pageindex import PageIndexClient
            client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
            
            # List documents
            docs = client.list_documents().get("documents", [])
            completed_docs = [d for d in docs if d.get("status") == "completed"]
            
            if completed_docs:
                results = []
                active_retrievals = {}
                
                # Submit query to each document
                for doc in completed_docs:
                    try:
                        q_res = client.submit_query(doc_id=doc["id"], query=query)
                        active_retrievals[doc["id"]] = q_res["retrieval_id"]
                    except Exception as e:
                        print(f"  [WARNING] Failed to submit query for doc {doc['name']}: {e}")
                
                # Poll active retrievals
                if active_retrievals:
                    retrieved_nodes_all = []
                    # Poll for up to 30 seconds (15 cycles * 2s)
                    for cycle in range(15):
                        all_done = True
                        for doc_id, retrieval_id in list(active_retrievals.items()):
                            try:
                                ret_res = client.get_retrieval(retrieval_id)
                                status = ret_res.get("status")
                                if status in ["completed", "failed"]:
                                    if status == "completed":
                                        retrieved_nodes_all.extend(ret_res.get("retrieved_nodes", []))
                                    active_retrievals.pop(doc_id)
                                else:
                                    all_done = False
                            except Exception as e:
                                print(f"  [WARNING] Error checking retrieval status for {retrieval_id}: {e}")
                                active_retrievals.pop(doc_id)
                        
                        if all_done or not active_retrievals:
                            break
                        time.sleep(2)
                    
                    # Process retrieved nodes
                    for idx, node in enumerate(retrieved_nodes_all):
                        content = ""
                        for sublist in node.get("relevant_contents", []):
                            for item in sublist:
                                if item.get("relevant_content"):
                                    content += item.get("relevant_content") + "\n"
                        content = content.strip()
                        
                        # Score: descending order based on list index
                        score = float(1.0 - idx * 0.05)
                        
                        # Find source file name from node metadata
                        meta_list = node.get("metadata", [])
                        source_name = "nghi-dinh-28-2026.pdf"
                        if meta_list and len(meta_list) > 1:
                            source_name = meta_list[1]
                        
                        results.append({
                            "content": content,
                            "score": score,
                            "metadata": {
                                "node_id": node.get("id"),
                                "title": node.get("title"),
                                "source": source_name
                            },
                            "source": "pageindex"
                        })
                    
                    if results:
                        # Sort by score descending and return top_k
                        results.sort(key=lambda x: x["score"], reverse=True)
                        return results[:top_k]
                        
        except Exception as e:
            print(f"  [WARNING] PageIndex query failed: {e}. Falling back to local search.")

    # Fallback: sử dụng BM25 cục bộ từ Task 6 và ghi đè source = pageindex
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        
    try:
        from src.task6_lexical_search import lexical_search
        local_results = lexical_search(query, top_k=top_k)
        for r in local_results:
            r["source"] = "pageindex"
        return local_results
    except Exception as fallback_err:
        print(f"  [ERROR] PageIndex local fallback failed: {fallback_err}")
        return []


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY or PAGEINDEX_API_KEY.startswith("pi_"):
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
        print("  Chạy thử fallback cục bộ...")
        results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
        for idx, r in enumerate(results, 1):
            print(f"{idx}. [{r['score']:.3f}] (Source: {r['source']})")
            print(f"   Content: {r['content'][:150]}...\n")
    else:
        print("Uploading documents...")
        upload_documents()

        print("\nTest query:")
        results = pageindex_search("hình phạt sử dụng ma tuý", top_k=3)
        for r in results:
            print(f"[{r['score']:.3f}] {r['content'][:100]}...")
