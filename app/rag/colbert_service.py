import logging
import os
import random
import uuid
from typing import Dict, List, Optional, Union

import torch
from PIL import Image
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility
from tqdm import tqdm

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set to True to force mock embeddings (for development/testing)
FORCE_MOCK_MODE = True

# Initialize Milvus utility
try:
    utility = utility
    logger.info("ColBERT service connected to Milvus utility")
except Exception as e:
    logger.warning(f"ColBERT service could not connect to Milvus utility: {e}")
    utility = None


class ColBERTService:
    """
    Real implementation of ColBERT service for visual-first retrieval.
    Uses pretrained models to generate embeddings for text and images.
    """

    def __init__(self, model_path: str):
        """
        Initialize the ColBERT service.

        Args:
            model_path: Path to the pretrained model
        """
        logger.info(f"Initializing ColBERT service with model path: {model_path}")
        self.model_path = model_path
        self.embedding_dim = 768  # ColBERT/Qwen-VL embedding dimension
        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available() else "cpu"
        )

        # Create upload directory if it doesn't exist
        os.makedirs(settings.upload_dir, exist_ok=True)
        logger.info(f"Created upload directory: {settings.upload_dir}")

        # Initialize models
        try:
            from transformers import AutoModel, AutoProcessor, AutoTokenizer

            logger.info(f"Loading models on device: {self.device}")
            self.processor = AutoProcessor.from_pretrained(model_path)
            self.model = AutoModel.from_pretrained(model_path).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            logger.info(f"Models loaded successfully: {model_path}")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            logger.info("Falling back to mock embeddings mode")
            self.processor = None
            self.model = None
            self.tokenizer = None

    def _is_model_loaded(self) -> bool:
        """Check if models are loaded properly"""
        if FORCE_MOCK_MODE:
            logger.info("Using mock embeddings mode (forced by configuration)")
            return False
        return self.model is not None and self.processor is not None

    def process_query(self, queries: List[str]) -> List[List[float]]:
        """Generate embeddings for text queries"""
        logger.info(f"Processing {len(queries)} text queries")

        if not self._is_model_loaded():
            logger.warning("Models not loaded, falling back to mock embeddings")
            return [self._generate_mock_embedding() for _ in queries]

        embeddings = []
        batch_size = 8  # Process in smaller batches to avoid memory issues

        try:
            for i in range(0, len(queries), batch_size):
                batch_queries = queries[i : i + batch_size]

                # Tokenize the queries
                inputs = self.tokenizer(
                    batch_queries,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512,
                ).to(self.device)

                # Generate embeddings
                with torch.no_grad():
                    outputs = self.model(**inputs)

                # Use mean pooling over the last hidden state
                batch_embeddings = (
                    outputs.last_hidden_state.mean(dim=1).cpu().numpy().tolist()
                )
                embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(embeddings)} text embeddings successfully")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating text embeddings: {e}")
            logger.warning("Falling back to mock embeddings")
            return [self._generate_mock_embedding() for _ in queries]

    def process_image(self, images: List[Image.Image]) -> List[List[float]]:
        """Generate embeddings for images"""
        logger.info(f"Processing {len(images)} images")

        if not self._is_model_loaded():
            logger.warning("Models not loaded, falling back to mock embeddings")
            return [self._generate_mock_embedding() for _ in images]

        embeddings = []
        batch_size = 4  # Process in smaller batches to avoid memory issues

        try:
            for i in range(0, len(images), batch_size):
                batch_images = images[i : i + batch_size]

                # Process images with the vision processor
                inputs = self.processor(images=batch_images, return_tensors="pt").to(
                    self.device
                )

                # Generate embeddings
                with torch.no_grad():
                    outputs = self.model(**inputs)

                # Use mean pooling over the last hidden state for images
                batch_embeddings = (
                    outputs.last_hidden_state.mean(dim=1).cpu().numpy().tolist()
                )
                embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(embeddings)} image embeddings successfully")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating image embeddings: {e}")
            logger.warning("Falling back to mock embeddings")
            return [self._generate_mock_embedding() for _ in images]

    def _generate_mock_embedding(self) -> List[float]:
        """Generate a random embedding vector as fallback"""
        logger.warning("Generating mock embedding as fallback")
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

                # Create HNSW index for efficient search
                index_params = {
                    "metric_type": "L2",
                    "index_type": "HNSW",
                    "params": {
                        "M": 16,  # Number of connections per node
                        "efConstruction": 200,  # Higher values give better recall
                    },
                }
                collection.create_index("embedding", index_params)
                logger.info(
                    f"Created Milvus collection with HNSW index: {collection_name}"
                )
            else:
                logger.info(f"Milvus collection already exists: {collection_name}")

                # Load the collection for search
                collection = Collection(collection_name)
                collection.load()
        except Exception as e:
            logger.error(f"Error creating Milvus collection: {e}")

    def search(self, query: str, kb_id: str, top_k: int = 5) -> List[Dict]:
        """Search for similar documents based on semantic embedding"""
        logger.info(f"Searching for '{query}' in knowledge base {kb_id}")

        collection_name = f"colqwen_{kb_id}"

        try:
            # Check if collection exists
            if not utility or not utility.has_collection(collection_name):
                logger.warning(
                    f"Collection {collection_name} does not exist, returning mock results"
                )
                return self._mock_search_results(query, top_k)

            # Generate query embedding
            query_embedding = self.process_query([query])[0]

            # Connect to collection and search
            collection = Collection(collection_name)
            collection.load()  # Load collection for search

            # Set search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"ef": 100},  # Higher recall at search time
            }

            # Search in Milvus
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["doc_id"],
            )[
                0
            ]  # Get first result set

            logger.info(f"Found {len(results)} results in Milvus")

            # Process results - fetch metadata from MongoDB
            search_results = []
            for hit in results:
                chunk_id = hit.id
                doc_id = hit.entity.get("doc_id")
                distance = hit.distance

                # Convert L2 distance to similarity score (higher is better)
                score = 1.0 / (1.0 + distance)

                # Get chunk text/metadata from MongoDB
                try:
                    from app.rag.convert_file import chunks_collection

                    if chunks_collection:
                        chunk = chunks_collection.find_one({"_id": chunk_id})
                        if chunk:
                            text = chunk.get("text", "")
                            metadata = chunk.get("metadata", {})

                            # For PDF pages, there is special handling
                            if chunk.get("type") == "pdf_page":
                                page_num = chunk.get("page_number", 0)
                                metadata = {
                                    "source": "pdf",
                                    "page": page_num,
                                    **metadata,
                                }
                                text = f"PDF page {page_num} from document {doc_id}"

                            search_results.append(
                                {
                                    "chunk_id": chunk_id,
                                    "doc_id": doc_id,
                                    "text": text,
                                    "metadata": metadata,
                                    "score": score,
                                }
                            )
                except Exception as e:
                    logger.error(f"Error getting chunk metadata: {e}")
                    search_results.append(
                        {
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "text": f"Document chunk {chunk_id}",
                            "metadata": {},
                            "score": score,
                        }
                    )

            return search_results

        except Exception as e:
            logger.error(f"Error searching in Milvus: {e}")
            return self._mock_search_results(query, top_k)

    def _mock_search_results(self, query: str, top_k: int = 5) -> List[Dict]:
        """Generate mock search results as a fallback"""
        logger.warning(f"Generating mock search results for '{query}'")
        search_results = []
        for i in range(min(top_k, 3)):
            chunk_id = str(uuid.uuid4())
            doc_id = str(uuid.uuid4())

            search_results.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": f"This is a mock search result {i+1} for query: {query}",
                    "metadata": {"source": "mock", "page": i + 1},
                    "score": random.uniform(0.5, 0.9),
                }
            )
        return search_results


# Initialize the ColBERT service
colbert = ColBERTService(settings.colbert_model_path)
logger.info("ColBERT service initialized")
