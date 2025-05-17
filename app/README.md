# Ask2Slide RAG System

This directory contains the implementation of the Retrieval-Augmented Generation (RAG) system for Ask2Slide.

## Architecture Overview

The RAG system combines:

- A retriever component (ColBERT-based)
- A generator component (Qwen2.5-VL model)
- Knowledge base storage (MongoDB + Milvus)
- File processing pipeline

## Core Components

### Document Processing (`app/rag/convert_file.py`)

- Handles PDF, DOCX, and other file formats
- Extracts text and metadata
- Splits documents into chunks (1024 tokens by default)
- Generates embeddings for each chunk using ColBERT
- Stores processed data in MongoDB and Milvus

### Retrieval Service (`app/rag/colbert_service.py`)

- Uses ColBERT for dense passage retrieval
- Implements efficient similarity search via Milvus
- Supports hybrid retrieval combining dense and sparse approaches

### API Server (`app/core/model_server.py`)

- Provides RESTful API endpoints for:
  - Text and image embedding generation
  - Document processing and storage
  - Similarity search
  - Health checks

## Getting Started

### Prerequisites

- MongoDB running on localhost:27017
- Milvus running on localhost:19530
- Python 3.10+
- Poetry for dependency management

### Installation

```bash
# Install dependencies
poetry install

# Run the server
python app/run_rag_server.py
```

### API Endpoints

- `/embed_text`: Generate embeddings for text queries
- `/embed_image`: Generate embeddings for images
- `/process_file`: Process a file and store its chunks
- `/process_image`: Process an image and store its embedding
- `/search`: Search for similar documents
- `/hybrid_search`: Hybrid search combining dense and sparse retrieval
- `/health`: Health check endpoint

## Usage Examples

### Process a File

```bash
curl -X POST \
  http://localhost:8005/process_file \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/document.pdf' \
  -F 'kb_id=my_knowledge_base'
```

### Search for Similar Documents

```bash
curl -X POST \
  http://localhost:8005/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is the main topic of the presentation?",
    "kb_id": "my_knowledge_base",
    "top_k": 5
  }'
```

## Configuration

Configuration settings are defined in `app/core/config.py` and can be overridden using environment variables.
