import logging
from typing import Any, Dict, List, Optional, Union

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


class MilvusManager:
    """
    Manager for Milvus vector database operations.
    This class provides methods for creating collections, inserting vectors,
    searching, and other common Milvus operations.
    """

    def __init__(self):
        """Initialize the Milvus manager with configuration from settings."""
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.connected = False

    def init_milvus(self) -> bool:
        """
        Initialize connection to Milvus.
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            connections.connect("default", host=self.host, port=self.port)
            self.connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Milvus: {e}")
            self.connected = False
            return False

    def create_collection(
        self, collection_name: str, dim: int = 768, partition_key: str = None
    ) -> Optional[Collection]:
        """
        Create a collection if it doesn't exist.

        Args:
            collection_name: Name of the collection to create
            dim: Dimension of the vectors to store
            partition_key: Optional field name to use as partition key

        Returns:
            Collection object if created successfully, None otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot create collection")
            return None

        try:
            # Check if collection already exists
            if utility.has_collection(collection_name):
                logger.info(f"Collection '{collection_name}' already exists")
                return Collection(collection_name)

            # Define schema
            fields = []

            # Primary key field
            fields.append(
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=100,
                    is_primary=True,
                )
            )

            # Optional partition key
            if partition_key:
                fields.append(
                    FieldSchema(
                        name=partition_key,
                        dtype=DataType.VARCHAR,
                        max_length=100,
                    )
                )

            # Document ID field (for reference)
            fields.append(
                FieldSchema(
                    name="doc_id",
                    dtype=DataType.VARCHAR,
                    max_length=100,
                )
            )

            # Vector field
            fields.append(
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dim,
                )
            )

            # Create schema
            schema = CollectionSchema(
                fields=fields,
                description=f"Collection for {collection_name}",
            )

            # Create collection
            collection = Collection(collection_name, schema)

            # Create index for vector field
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            collection.create_index("embedding", index_params)

            logger.info(f"Created collection '{collection_name}' with dimension {dim}")
            return collection

        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {e}")
            return None

    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Get a collection by name.

        Args:
            collection_name: Name of the collection to get

        Returns:
            Collection object if exists, None otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot get collection")
            return None

        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' does not exist")
                return None

            collection = Collection(collection_name)
            collection.load()
            return collection
        except Exception as e:
            logger.error(f"Error getting collection '{collection_name}': {e}")
            return None

    def insert_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        doc_ids: Optional[List[str]] = None,
        partition_key: Optional[str] = None,
        partition_values: Optional[List[str]] = None,
    ) -> bool:
        """
        Insert vectors into a collection.

        Args:
            collection_name: Name of the collection to insert into
            ids: List of IDs for the vectors
            vectors: List of vector embeddings
            doc_ids: Optional list of document IDs
            partition_key: Optional partition key name
            partition_values: Optional list of partition values

        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot insert vectors")
            return False

        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found, creating it")
                collection = self.create_collection(
                    collection_name,
                    dim=len(vectors[0]) if vectors else 768,
                    partition_key=partition_key,
                )
                if not collection:
                    return False

            # Prepare data for insertion
            data = {"id": ids, "embedding": vectors}

            # Add document IDs if provided
            if doc_ids:
                if len(doc_ids) != len(ids):
                    logger.warning(
                        "Length of doc_ids doesn't match length of ids, using default values"
                    )
                    doc_ids = [f"doc_{i}" for i in range(len(ids))]
                data["doc_id"] = doc_ids
            else:
                data["doc_id"] = [f"doc_{i}" for i in range(len(ids))]

            # Add partition values if provided
            if partition_key and partition_values:
                if len(partition_values) != len(ids):
                    logger.warning(
                        f"Length of partition_values doesn't match length of ids, using default values"
                    )
                    partition_values = ["default" for _ in range(len(ids))]
                data[partition_key] = partition_values

            # Insert data
            collection.insert(data)
            logger.info(
                f"Inserted {len(ids)} vectors into collection '{collection_name}'"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error inserting vectors into collection '{collection_name}': {e}"
            )
            return False

    def search(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        top_k: int = 5,
        partition_key: Optional[str] = None,
        partition_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection to search in
            query_vectors: List of query vectors
            top_k: Number of results to return
            partition_key: Optional partition key to search in
            partition_value: Optional partition value to search in

        Returns:
            List of search results
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot search")
            return []

        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found")
                return []

            # Set up search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }

            # Set up partition if provided
            if partition_key and partition_value:
                expr = f"{partition_key} == '{partition_value}'"
            else:
                expr = None

            # Perform search
            results = collection.search(
                data=query_vectors,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["doc_id"],
            )

            # Format results
            formatted_results = []
            for hits in results:
                hits_list = []
                for hit in hits:
                    hits_list.append(
                        {
                            "id": hit.id,
                            "distance": hit.distance,
                            "doc_id": hit.entity.get("doc_id"),
                        }
                    )
                formatted_results.append(hits_list)

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching in collection '{collection_name}': {e}")
            return []

    def delete_entities(self, collection_name: str, ids: List[str]) -> bool:
        """
        Delete entities by ID.

        Args:
            collection_name: Name of the collection to delete from
            ids: List of IDs to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot delete entities")
            return False

        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found")
                return False

            # Delete entities
            expr = f"id in {ids}"
            collection.delete(expr)
            logger.info(
                f"Deleted {len(ids)} entities from collection '{collection_name}'"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error deleting entities from collection '{collection_name}': {e}"
            )
            return False

    def drop_collection(self, collection_name: str) -> bool:
        """
        Drop a collection.

        Args:
            collection_name: Name of the collection to drop

        Returns:
            bool: True if drop was successful, False otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot drop collection")
            return False

        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' does not exist")
                return True

            utility.drop_collection(collection_name)
            logger.info(f"Dropped collection '{collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Error dropping collection '{collection_name}': {e}")
            return False

    def validate_collection_existence(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection to check

        Returns:
            bool: True if collection exists, False otherwise
        """
        if not self.connected and not self.init_milvus():
            logger.error(
                "Not connected to Milvus, cannot validate collection existence"
            )
            return False

        try:
            exists = utility.has_collection(collection_name)
            return exists
        except Exception as e:
            logger.error(
                f"Error checking if collection '{collection_name}' exists: {e}"
            )
            return False

    def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot list collections")
            return []

        try:
            collections = utility.list_collections()
            return collections
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for a collection.

        Args:
            collection_name: Name of the collection to get stats for

        Returns:
            Dictionary of collection statistics
        """
        if not self.connected and not self.init_milvus():
            logger.error("Not connected to Milvus, cannot get collection stats")
            return {}

        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.warning(f"Collection '{collection_name}' not found")
                return {}

            stats = collection.get_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting stats for collection '{collection_name}': {e}")
            return {}


# Create a singleton instance
milvus_manager = MilvusManager()
