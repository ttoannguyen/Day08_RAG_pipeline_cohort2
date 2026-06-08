"""
Chạy bài nhóm local — tự load .env từ personal project.

Usage:
    python run_local.py index    # Task 4: chunk + index ChromaDB
    python run_local.py server   # FastAPI chatbot tại http://127.0.0.1:8000
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
DEFAULT_PERSONAL = ROOT.parent / "personal_project" / "2A202500574-Hoang_Kim_Tuan_Anh"
PERSONAL_DIR = Path(os.getenv("PERSONAL_PROJECT_PATH", DEFAULT_PERSONAL))

for env_path in (PERSONAL_DIR / ".env", ROOT / ".env", ROOT.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "server"

    if cmd == "index":
        from src.task4_chunking_indexing import run_pipeline

        run_pipeline()
        return

    if cmd == "server":
        import uvicorn

        print("DrugLaw RAG → http://127.0.0.1:8000")
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
        return

    print(f"Unknown command: {cmd}. Use: index | server")
    sys.exit(1)


if __name__ == "__main__":
    main()
