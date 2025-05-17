#!/usr/bin/env python3
"""
Script to run the RAG server
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

from app.core.config import settings
from app.core.model_server import app

if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)

    print(f"Starting RAG server on http://{settings.host}:{settings.port}")
    print(f"API documentation available at http://{settings.host}:{settings.port}/docs")

    # Start the server
    uvicorn.run(app, host=settings.host, port=settings.port)
