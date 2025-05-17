import logging
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pymongo
from PIL import Image
from pymilvus import Collection, connections
from tqdm import tqdm

from app.core.config import settings
from app.rag.colbert_service import colbert, logger

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
    docs_collection = mongo_db["documents"]
    chunks_collection = mongo_db["document_chunks"]
    logger.info("Document processor connected to MongoDB")
except Exception as e:
    logger.warning(f"Document processor could not connect to MongoDB: {e}")
    mongo_client = None
    mongo_db = None
    docs_collection = None
    chunks_collection = None

# Initialize Milvus connection
try:
    connections.connect("default", host=settings.milvus_host, port=settings.milvus_port)
    logger.info("Document processor connected to Milvus")
except Exception as e:
    logger.warning(f"Document processor could not connect to Milvus: {e}")


class DocumentProcessor:
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

    def process_file(
        self,
        file_content: bytes,
        filename: str,
        kb_id: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> str:
        """Process a file and store its chunks in MongoDB and Milvus"""
        # Generate a unique document ID
        doc_id = str(uuid.uuid4())
        logger.info(f"Processing file: {filename} (ID: {doc_id})")

        # Save file to disk
        file_path = self.upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"Saved file to: {file_path}")

        # Extract text and metadata based on file type
        text, metadata = self._extract_text_and_metadata(file_path, filename)
        logger.info(f"Extracted metadata: {metadata}")

        # Store document metadata
        if docs_collection:
            try:
                docs_collection.insert_one(
                    {
                        "_id": doc_id,
                        "filename": filename,
                        "kb_id": kb_id,
                        "metadata": metadata,
                        "file_path": str(file_path),
                    }
                )
                logger.info(f"Stored document metadata in MongoDB")
            except Exception as e:
                logger.error(f"Error storing document metadata: {e}")
        else:
            logger.warning("MongoDB not available, skipping document metadata storage")

        # Split text into chunks
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap
        chunks = self._split_text(text, chunk_size, chunk_overlap)
        logger.info(f"Split text into {len(chunks)} chunks")

        # Process chunks
        self._process_chunks(chunks, doc_id, kb_id)

        return doc_id

    def process_image(
        self,
        image: Union[bytes, Path, str],
        filename: str,
        kb_id: str,
    ) -> str:
        """Process an image and store its embedding in Milvus"""
        # Generate a unique document ID
        doc_id = str(uuid.uuid4())
        logger.info(f"Processing image: {filename} (ID: {doc_id})")

        # Convert to PIL Image if needed
        if isinstance(image, bytes):
            pil_image = Image.open(BytesIO(image))
            # Save image to disk
            file_path = self.upload_dir / filename
            pil_image.save(file_path)
            logger.info(f"Saved image from bytes to: {file_path}")
        elif isinstance(image, (str, Path)):
            file_path = Path(image)
            pil_image = Image.open(file_path)
            logger.info(f"Opened image from path: {file_path}")
        else:
            pil_image = image
            file_path = self.upload_dir / filename
            pil_image.save(file_path)
            logger.info(f"Saved image object to: {file_path}")

        # Extract metadata
        metadata = {
            "width": pil_image.width,
            "height": pil_image.height,
            "format": pil_image.format,
            "mode": pil_image.mode,
        }
        logger.info(f"Image metadata: {metadata}")

        # Store document metadata
        if docs_collection:
            try:
                docs_collection.insert_one(
                    {
                        "_id": doc_id,
                        "filename": filename,
                        "kb_id": kb_id,
                        "type": "image",
                        "metadata": metadata,
                        "file_path": str(file_path),
                    }
                )
                logger.info(f"Stored image metadata in MongoDB")
            except Exception as e:
                logger.error(f"Error storing image metadata: {e}")
        else:
            logger.warning("MongoDB not available, skipping image metadata storage")

        # Generate embedding
        try:
            embeddings = colbert.process_image([pil_image])
            logger.info(
                f"Generated image embedding with dimension: {len(embeddings[0])}"
            )

            # Ensure Milvus collection exists
            colbert.create_kb_collection(kb_id)

            # Store embedding in Milvus
            try:
                collection_name = f"colqwen_{kb_id}"
                collection = Collection(collection_name)

                # Insert embedding
                chunk_id = str(uuid.uuid4())
                entities = [
                    [chunk_id],  # chunk_id
                    [doc_id],  # doc_id
                    embeddings,  # embedding
                ]
                collection.insert(entities)
                logger.info(f"Stored image embedding in Milvus")

                # Store chunk metadata in MongoDB
                if chunks_collection:
                    try:
                        chunks_collection.insert_one(
                            {
                                "_id": chunk_id,
                                "doc_id": doc_id,
                                "kb_id": kb_id,
                                "type": "image",
                                "metadata": metadata,
                            }
                        )
                        logger.info(f"Stored chunk metadata in MongoDB")
                    except Exception as e:
                        logger.error(f"Error storing chunk metadata: {e}")
                else:
                    logger.warning(
                        "MongoDB not available, skipping chunk metadata storage"
                    )
            except Exception as e:
                logger.error(f"Error storing embedding in Milvus: {e}")
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}")

        return doc_id

    def _extract_text_and_metadata(
        self, file_path: Path, filename: str
    ) -> Tuple[str, Dict]:
        """Extract text and metadata from a file based on its extension"""
        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return self._extract_from_pdf(file_path)
        elif extension in [".docx", ".doc"]:
            return self._extract_from_docx(file_path)
        elif extension in [".txt", ".md", ".py", ".js", ".html", ".css"]:
            return self._extract_from_text(file_path)
        elif extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
            # For images, we don't extract text but return empty text and image metadata
            img = Image.open(file_path)
            metadata = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
            }
            return "", metadata
        else:
            # For unsupported files, return empty text and basic metadata
            return "", {"filename": filename, "extension": extension}

    def _extract_from_pdf(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from a PDF file"""
        try:
            # This is a placeholder - in a real implementation, you would use a library like PyPDF2 or pdfplumber
            # For now, we'll just return a placeholder
            return f"Text extracted from PDF: {file_path.name}", {
                "type": "pdf",
                "pages": 1,
            }
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return "", {"error": str(e)}

    def _extract_from_docx(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from a DOCX file"""
        try:
            # This is a placeholder - in a real implementation, you would use a library like python-docx
            # For now, we'll just return a placeholder
            return f"Text extracted from DOCX: {file_path.name}", {
                "type": "docx",
                "pages": 1,
            }
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return "", {"error": str(e)}

    def _extract_from_text(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract text from a plain text file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return text, {"type": "text", "extension": file_path.suffix}
        except Exception as e:
            logger.error(f"Error extracting text from text file: {e}")
            return "", {"error": str(e)}

    def _split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text into chunks of specified size with overlap"""
        if not text:
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            start += chunk_size - chunk_overlap

        return chunks

    def _process_chunks(self, chunks: List[str], doc_id: str, kb_id: str) -> None:
        """Process text chunks and store them in MongoDB and Milvus"""
        if not chunks:
            logger.info("No chunks to process")
            return

        logger.info(f"Processing {len(chunks)} chunks for document {doc_id}")

        try:
            # Generate embeddings for all chunks
            embeddings = colbert.process_query(chunks)
            logger.info(f"Generated embeddings for {len(chunks)} chunks")

            # Ensure Milvus collection exists
            colbert.create_kb_collection(kb_id)

            try:
                # Get collection
                collection_name = f"colqwen_{kb_id}"
                collection = Collection(collection_name)

                # Process chunks
                chunk_ids = []
                doc_ids = []

                # Store chunks in MongoDB and prepare for Milvus
                for i, chunk in enumerate(chunks):
                    chunk_id = str(uuid.uuid4())
                    chunk_ids.append(chunk_id)
                    doc_ids.append(doc_id)

                    # Store in MongoDB
                    if chunks_collection:
                        try:
                            chunks_collection.insert_one(
                                {
                                    "_id": chunk_id,
                                    "doc_id": doc_id,
                                    "kb_id": kb_id,
                                    "text": chunk,
                                    "chunk_index": i,
                                    "type": "text",
                                }
                            )
                        except Exception as e:
                            logger.error(f"Error storing chunk in MongoDB: {e}")
                    else:
                        logger.warning("MongoDB not available, skipping chunk storage")

                # Store embeddings in Milvus
                try:
                    entities = [
                        chunk_ids,  # chunk_id
                        doc_ids,  # doc_id
                        embeddings,  # embedding
                    ]
                    collection.insert(entities)
                    logger.info(f"Stored {len(chunk_ids)} embeddings in Milvus")
                except Exception as e:
                    logger.error(f"Error storing embeddings in Milvus: {e}")
            except Exception as e:
                logger.error(f"Error with Milvus collection: {e}")
        except Exception as e:
            logger.error(f"Error processing chunks: {e}")


# Initialize the document processor
document_processor = DocumentProcessor()
