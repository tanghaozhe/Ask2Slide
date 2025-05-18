#!/usr/bin/env python3
"""
Script to run the RAG server
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

from app.core.config import settings
from app.core.logging import logger
from app.core.model_server import app
from app.db.milvus import milvus_manager
from app.db.minio import async_minio_manager


async def init_services():
    """Initialize all required services before starting the server"""
    # Initialize Milvus
    logger.info("Initializing Milvus connection...")
    if milvus_manager.init_milvus():
        logger.info("Milvus connection established successfully")
    else:
        logger.warning(
            "Failed to connect to Milvus, some features may not work properly"
        )

    # Initialize MinIO
    logger.info("Initializing MinIO connection...")
    try:
        await async_minio_manager.init_minio()
        logger.info("MinIO connection established successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize MinIO: {e}")
        logger.warning("File storage features may not work properly")


if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Initialize services
    logger.info("Initializing services...")
    asyncio.run(init_services())

    logger.info(f"Starting RAG server on http://{settings.host}:{settings.port}")
    logger.info(
        f"API documentation available at http://{settings.host}:{settings.port}/docs"
    )

    # Start the server
    uvicorn.run(app, host=settings.host, port=settings.port)
