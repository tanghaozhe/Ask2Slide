import logging
import os
from io import BytesIO
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger
from app.db.milvus import milvus_manager
from app.db.minio import async_minio_manager
from app.rag.colbert_service import colbert
from app.rag.convert_file import document_processor

# ARCHITECTURE NOTE:
# This API server provides embedding endpoints that are consumed by the newer async implementation
# in app/rag/process_file.py and app/rag/get_embedding.py.
#
# The core functionality is:
# 1. app/rag/colbert_service.py - Handles direct model inference with the ColBERT model
# 2. app/core/model_server.py (this file) - Exposes the model as HTTP endpoints
# 3. app/rag/get_embedding.py - Provides async HTTP client to communicate with this server
# 4. app/rag/process_file.py - Uses the HTTP client for the full processing pipeline
#
# Both implementations (direct and HTTP-based) are currently used in the system.

app = FastAPI(title="Ask2Slide RAG API Server")
service = colbert  # Single instance loading


@app.on_event("startup")
async def startup_event():
    """Initialize services when the application starts"""
    logger.info("Initializing services on application startup...")

    # Initialize Milvus
    if milvus_manager.init_milvus():
        logger.info("Milvus connection established successfully")
    else:
        logger.warning(
            "Failed to connect to Milvus, some features may not work properly"
        )

    # Initialize MinIO
    try:
        await async_minio_manager.init_minio()
        logger.info("MinIO connection established successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize MinIO: {e}")
        logger.warning("File storage features may not work properly")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down"""
    logger.info("Shutting down services...")

    # Close Milvus connection
    try:
        from pymilvus import connections

        connections.disconnect("default")
        logger.info("Milvus connection closed")
    except Exception as e:
        logger.warning(f"Error closing Milvus connection: {e}")

    # No explicit cleanup needed for MinIO as it uses session-based connections
    logger.info("All services shut down successfully")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class TextRequest(BaseModel):
    queries: list


class SearchRequest(BaseModel):
    query: str
    kb_id: str
    top_k: Optional[int] = 5


class ProcessRequest(BaseModel):
    kb_id: str
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


# Embedding endpoints
@app.post("/embed_text")
async def embed_text(request: TextRequest):
    """Generate embeddings for text queries"""
    return {"embeddings": service.process_query(request.queries)}


@app.post("/embed_image")
async def embed_image(images: List[UploadFile] = File(...)):
    """Generate embeddings for images"""
    pil_images = []
    for image_file in images:
        # Read binary stream and convert to PIL.Image
        content = await image_file.read()
        buffer = BytesIO(content)
        image = Image.open(buffer)
        pil_images.append(image)
        # Important: close file stream to avoid memory leaks
        await image_file.close()
    return {"embeddings": service.process_image(pil_images)}


# Document processing endpoints
@app.post("/process_file")
async def process_file(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
):
    """Process a file and store its chunks in the knowledge base"""
    try:
        content = await file.read()
        doc_id = document_processor.process_file(
            content, file.filename, kb_id, chunk_size, chunk_overlap
        )
        return {"doc_id": doc_id, "filename": file.filename, "status": "processed"}
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process_image")
async def process_image(
    image: UploadFile = File(...),
    kb_id: str = Form(...),
):
    """Process an image and store its embedding in the knowledge base"""
    try:
        content = await image.read()
        doc_id = document_processor.process_image(content, image.filename, kb_id)
        return {"doc_id": doc_id, "filename": image.filename, "status": "processed"}
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoints
@app.post("/search")
async def search(request: SearchRequest):
    """Search for similar documents using the query"""
    try:
        results = service.search(request.query, request.kb_id, request.top_k)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid_search")
async def hybrid_search(request: SearchRequest):
    """
    Search endpoint that returns top-k most similar documents based on vector similarity

    This endpoint uses pure vector similarity search without additional re-ranking:
    - Uses ColBERT vector embeddings to find similar content
    - Returns top-k results based only on vector similarity
    - No additional re-ranking or hybrid logic is applied
    """
    try:
        # Log the search request
        logger.info(
            f"Search request: {request.query} in KB {request.kb_id}, top_k={request.top_k}"
        )

        # Perform simple search using ColBERT service (without hybrid re-ranking)
        results = service.search(request.query, request.kb_id, request.top_k)

        # Enhance results with additional context
        for result in results:
            # If the result is a PDF page, try to get the image URL
            if result.get("metadata", {}).get("source") == "pdf":
                try:
                    # Get the document and chunk info from MongoDB
                    from app.rag.convert_file import chunks_collection, docs_collection

                    if chunks_collection and docs_collection:
                        chunk = chunks_collection.find_one({"_id": result["chunk_id"]})
                        if chunk and "image_path" in chunk:
                            # Add image path to result
                            result["image_path"] = chunk["image_path"]

                        # Get document metadata
                        doc = docs_collection.find_one({"_id": result["doc_id"]})
                        if doc:
                            result["filename"] = doc.get("filename")
                except Exception as e:
                    logger.error(f"Error enhancing result with MongoDB data: {e}")

        logger.info(f"Returning {len(results)} search results")
        return {"results": results}
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Ask2Slide RAG API Server",
    }


if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Start the server
    uvicorn.run(app, host=settings.host, port=settings.port)
