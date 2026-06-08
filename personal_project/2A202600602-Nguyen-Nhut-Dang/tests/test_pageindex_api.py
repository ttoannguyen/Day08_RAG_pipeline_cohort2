import os
import sys
import time
from dotenv import load_dotenv
from pathlib import Path
from pageindex import PageIndexClient

# Reconfigure stdout to support UTF-8 on Windows command prompts
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Load environment
STUDENT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=STUDENT_DIR.parent.parent / ".env")

api_key = os.getenv("PAGEINDEX_API_KEY")
print("API Key:", api_key[:5] + "..." if api_key else None)

client = PageIndexClient(api_key=api_key)

# 1. List documents
docs = client.list_documents()
print("Current documents:", docs)

# 2. Submit a small test document
test_file = STUDENT_DIR / "data" / "landing" / "legal" / "nghi-dinh-28-2026.pdf"
print("Submitting:", test_file)
res = client.submit_document(file_path=str(test_file))
print("Submit result:", res)
doc_id = res["doc_id"]

# 3. Wait for document to be ready
print("Waiting for document to be ready...")
for i in range(30):
    ready = client.is_retrieval_ready(doc_id)
    print(f"[{i}] Retrieval ready:", ready)
    if ready:
        break
    time.sleep(2)

# 4. Check get_tree
try:
    tree = client.get_tree(doc_id)
    print("Tree:", list(tree.keys()))
except Exception as e:
    print("Failed to get tree:", e)

# 5. Query
print("Submitting query...")
q_res = client.submit_query(doc_id=doc_id, query="danh mục các chất ma túy")
print("Query submit result:", q_res)
retrieval_id = q_res["retrieval_id"]

print("Waiting for retrieval...")
for i in range(60):
    ret_res = client.get_retrieval(retrieval_id)
    print(f"[{i}] Retrieval status:", ret_res.get("status"))
    if ret_res.get("status") in ["completed", "failed"]:
        import pprint
        pprint.pprint(ret_res)
        break
    time.sleep(2)

# 6. Cleanup
print("Deleting test document...")
del_res = client.delete_document(doc_id)
print("Delete result:", del_res)
