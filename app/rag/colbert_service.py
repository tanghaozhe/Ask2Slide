import logging
import os
import random
import uuid
from typing import Dict, List, Optional, Union

import numpy as np
import pymongo
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MongoDB connection
try:
    mongo_client = pymongo.MongoClient(
        settings.mongodb_uri, serverSelectionTimeoutMS=2000
    )
    mongo_client.server_info()  # Will raise an exception if cannot connect
    mongo_db = mongo_client[settings.mongodb_db]
    chunks_collection = mongo_db["document_chunks"]
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.warning(f"Could not connect to MongoDB: {e}")
    mongo_client = None
    mongo_db = None
    chunks_collection = None

# Initialize Milvus connection
try:
    connections.connect("default", host=settings.milvus_host, port=settings.milvus_port)
    logger.info("Connected to Milvus")
except Exception as e:
    logger.warning(f"Could not connect to Milvus: {e}")


class MockColBERTService:
    """
    Mock implementation of ColBERT service for demonstration purposes.
    This is a placeholder until the actual colpali_engine package is properly installed.
    """

    def __init__(self, model_path):
        logger.info(f"Initializing mock ColBERT service with model path: {model_path}")
        self.model_path = model_path
        self.embedding_dim = 768  # Standard embedding dimension

        # Create upload directory if it doesn't exist
        os.makedirs(settings.upload_dir, exist_ok=True)
        logger.info(f"Created upload directory: {settings.upload_dir}")

    def process_query(self, queries: list) -> List[List[float]]:
        """Generate mock embeddings for text queries"""
        logger.info(f"Processing {len(queries)} queries")
        return [self._generate_mock_embedding() for _ in queries]

    def process_image(self, images: List) -> List[List[float]]:
        """Generate mock embeddings for images"""
        logger.info(f"Processing {len(images)} images")
        return [self._generate_mock_embedding() for _ in images]

    def _generate_mock_embedding(self) -> List[float]:
        """Generate a random embedding vector"""
        return [random.uniform(-1, 1) for _ in range(self.embedding_dim)]

    def create_kb_collection(self, kb_id: str, dim: int = 768) -> None:
        """Create a Milvus collection for a knowledge base if it doesn't exist"""
        if not utility:
            logger.warning("Milvus not connected, skipping collection creation")
            return

        collection_name = f"colqwen_{kb_id}"

        try:
            if not utility.has_collection(collection_name):
                # Define schema
                chunk_id = FieldSchema(
                    name="chunk_id",
                    dtype=DataType.VARCHAR,
                    max_length=64,
                    is_primary=True,
                )
                doc_id = FieldSchema(
                    name="doc_id", dtype=DataType.VARCHAR, max_length=64
                )
                embedding = FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dim,
                )
                schema = CollectionSchema(
                    fields=[chunk_id, doc_id, embedding],
                    description=f"ColBERT embeddings for knowledge base {kb_id}",
                )

                # Create collection
                collection = Collection(collection_name, schema)

                # Create index for efficient search
                index_params = {
                    "metric_type": "L2",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128},
                }
                collection.create_index("embedding", index_params)
                logger.info(f"Created Milvus collection: {collection_name}")
            else:
                logger.info(f"Milvus collection already exists: {collection_name}")
        except Exception as e:
            logger.error(f"Error creating Milvus collection: {e}")

    def search(self, query: str, kb_id: str, top_k: int = 5) -> List[Dict]:
        """Mock search for similar documents"""
        logger.info(f"Searching for '{query}' in knowledge base {kb_id}")

        # Generate mock search results
        search_results = []
        for i in range(min(top_k, 3)):  # Limit to 3 mock results
            chunk_id = str(uuid.uuid4())
            doc_id = str(uuid.uuid4())

            search_results.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": f"This is a mock search result {i+1} for query: {query}",
                    "metadata": {"source": "mock", "page": i + 1},
                    "score": random.uniform(0.5, 0.9),  # Random similarity score
                }
            )

        return search_results

    def hybrid_search(self, query: str, kb_id: str, top_k: int = 5) -> List[Dict]:
        """Mock hybrid search combining dense and sparse retrieval"""
        logger.info(f"Performing hybrid search for '{query}' in knowledge base {kb_id}")

        # Just use the regular search for the mock implementation
        results = self.search(query, kb_id, top_k=top_k)

        # Sort by score (ascending for L2 distance)
        results = sorted(results, key=lambda x: x["score"])

        return results


# Initialize the ColBERT service
colbert = MockColBERTService(settings.colbert_model_path)
logger.info("ColBERT service initialized")
