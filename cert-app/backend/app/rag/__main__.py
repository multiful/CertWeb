"""CLI: python -m app.rag eval | index."""
import sys
from app.rag.eval.__main__ import main as eval_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        sys.argv = ["eval"] + sys.argv[2:]
        eval_main()
    elif len(sys.argv) > 1 and sys.argv[1] == "index":
        from app.database import SessionLocal
        from app.rag.index.builder import build_bm25_from_db
        db = SessionLocal()
        try:
            path = build_bm25_from_db(db)
            print(f"BM25 index built: {path}")
        finally:
            db.close()
    elif len(sys.argv) > 1 and sys.argv[1] == "reindex-vectors":
        from app.rag.index.reindex_cert_vectors import main as reindex_main

        sys.argv = ["reindex-vectors"] + sys.argv[2:]
        reindex_main()
    else:
        print("Usage: python -m app.rag eval --golden path/to/golden.jsonl [--output out.csv] [--rerank path]")
        print("       python -m app.rag index   # Build BM25 index from certificates_vectors")
        print("       python -m app.rag reindex-vectors [--limit N] [--batch-size N] [--chunk-profile baseline|exp_small|exp_medium|exp_large] [--dry-run] [--debug]")
        sys.exit(1)
