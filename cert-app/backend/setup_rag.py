from app.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_rag_infrastructure():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Enable pgvector extension
            logger.info("Checking for pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled.")

            # 2. Add embedding column to qualification table
            logger.info("Adding embedding column to qualification table...")
            # Using 1536 dimensions as it's standard for OpenAI text-embedding-3-small
            # You can change this if you use another model
            try:
                conn.execute(text("ALTER TABLE qualification ADD COLUMN embedding vector(1536)"))
                logger.info("Embedding column added.")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info("Embedding column already exists.")
                else:
                    raise e
            
            # 3. Create index for fast retrieval
            logger.info("Creating HNSW index for embeddings...")
            try:
                # ivfflat or hnsw are common. HNSW is generally better for performance.
                conn.execute(text("CREATE INDEX ON qualification USING hnsw (embedding vector_cosine_ops)"))
                logger.info("HNSW index created.")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info("Index already exists.")
                else:
                    logger.warning(f"Could not create HNSW index: {e}. Falling back or ignoring...")

            trans.commit()
            logger.info("RAG infrastructure setup complete.")
        except Exception as e:
            trans.rollback()
            logger.error(f"Failed to setup RAG infrastructure: {e}")
            raise e

if __name__ == "__main__":
    setup_rag_infrastructure()
