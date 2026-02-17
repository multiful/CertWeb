import numpy as np
from app.database import SessionLocal
from app.models import Qualification
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_dummy_embeddings():
    """Populates the database with dummy 1536-dim vectors for RAG testing."""
    db = SessionLocal()
    try:
        quals = db.query(Qualification).filter(Qualification.embedding == None).all()
        logger.info(f"Found {len(quals)} qualifications needing embeddings.")
        
        for i, q in enumerate(quals):
            # In a real app, you would use:
            # embedding = openai_client.embeddings.create(input=text, model="text-embedding-3-small").data[0].embedding
            
            # For now, generate a semi-deterministic dummy vector based on ID
            # to allow testing similarity
            np.random.seed(q.qual_id)
            dummy_vector = np.random.normal(0, 1, 1536).tolist()
            
            q.embedding = dummy_vector
            
            if (i + 1) % 100 == 0:
                db.commit()
                logger.info(f"Processed {i + 1} qualifications...")
        
        db.commit()
        logger.info("Dummy embedding population complete.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_dummy_embeddings()
