#!/usr/bin/env python3
"""
FastAPI server for Qwen model with multimodal RAG capabilities
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional, Union

import httpx
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymilvus import Collection, connections
from transformers import (
    AutoModel,
    AutoModelForCausalLM,
    AutoModelForVision2Seq,
    AutoProcessor,
    AutoTokenizer,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Ask2Slide Multimodal API Server")

# Image processing config
IMAGE_UPLOAD_DIR = Path("./uploads")
IMAGE_UPLOAD_DIR.mkdir(exist_ok=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model config
MODEL_NAME = os.environ.get(
    "MODEL_NAME",
    "Qwen/Qwen2.5-VL-7B-instruct",  # Using official HF model ID
)
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
model = None
tokenizer = None
processor = None

# Initialize Milvus connection
connections.connect("default", host="localhost", port="19530")

# Create collection if it doesn't exist
from pymilvus import CollectionSchema, DataType, FieldSchema, utility

if not utility.has_collection("image_embeddings"):
    # Define schema
    file_id = FieldSchema(
        name="file_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True
    )
    embedding = FieldSchema(
        name="embedding",
        dtype=DataType.FLOAT_VECTOR,
        dim=1024,  # Adjust based on your model's output dimension
    )
    schema = CollectionSchema(
        fields=[file_id, embedding], description="Image embeddings collection"
    )
    image_collection = Collection("image_embeddings", schema)
    # Create index for efficient search
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    image_collection.create_index("embedding", index_params)
else:
    image_collection = Collection("image_embeddings")
    # Load collection for search
    image_collection.load()


class ImageEmbeddingService:
    def __init__(self):
        self.device = DEVICE
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.processor = AutoProcessor.from_pretrained(MODEL_NAME)

    async def embed_images(self, image_paths: list):
        embeddings = []
        for img_path in image_paths:
            inputs = self.processor(images=img_path, return_tensors="pt").to(
                self.device
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
            embeddings.append(outputs.last_hidden_state.mean(dim=1).cpu().numpy())
        return embeddings


image_service = ImageEmbeddingService()


# Pydantic models
class Message(BaseModel):
    role: str
    content: Union[str, List[dict]]


class FileReference(BaseModel):
    id: str
    filename: str
    url: str
    pages: List[int]


class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    top_k: Optional[int] = 3
    file_references: Optional[List[FileReference]] = None


# Initialize model
@app.on_event("startup")
async def load_model():
    global model, tokenizer, processor
    try:
        logger.info(f"Loading {MODEL_NAME} on {DEVICE}...")

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        processor = AutoProcessor.from_pretrained(MODEL_NAME)
        model = AutoModelForVision2Seq.from_pretrained(
            MODEL_NAME, torch_dtype=torch.float16
        ).to(DEVICE)

        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise


# Image upload endpoint
@app.post("/v1/images/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_path = IMAGE_UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Generate embeddings
        embeddings = await image_service.embed_images([str(file_path)])

        # Store in Milvus
        file_id = str(uuid.uuid4())
        entities = [
            [file_id],  # file_id field
            [emb.tolist() for emb in embeddings],  # embedding field
        ]
        image_collection.insert(entities)

        return {"file_id": file_id, "filename": file.filename, "status": "processed"}
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Image search endpoint
@app.post("/v1/images/search")
async def search_images(query: str, top_k: int = 3):
    try:
        # Get text embedding
        query_embedding = await image_service.embed_images([query])

        # Search Milvus
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = image_collection.search(
            data=query_embedding,
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["file_id"],
        )

        return {
            "results": [
                {"file_id": hit.entity.get("file_id"), "score": hit.score}
                for hit in results[0]
            ]
        }
    except Exception as e:
        logger.error(f"Image search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Chat endpoint
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Simplified approach: Convert messages to a single string prompt
        prompt = ""
        for msg in request.messages:
            if isinstance(msg.content, str):
                if msg.role == "system":
                    prompt += f"System: {msg.content}\n\n"
                elif msg.role == "user":
                    prompt += f"User: {msg.content}\n\n"
                elif msg.role == "assistant":
                    prompt += f"Assistant: {msg.content}\n\n"
            else:
                # Handle complex content (just extract text parts)
                text_parts = []
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))

                combined_text = " ".join(text_parts)
                if msg.role == "system":
                    prompt += f"System: {combined_text}\n\n"
                elif msg.role == "user":
                    prompt += f"User: {combined_text}\n\n"
                elif msg.role == "assistant":
                    prompt += f"Assistant: {combined_text}\n\n"

        # Add final prompt for the assistant to respond
        prompt += "Assistant: "

        # Process the text prompt - ensure it's a string
        if not isinstance(prompt, str):
            logger.error(f"Prompt is not a string: {type(prompt)}")
            prompt = str(prompt)

        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

        # Generate response
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_k=request.top_k,
            do_sample=True,
        )

        # Decode response and extract only the new content
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        assistant_response = full_response[len(prompt) :].strip()

        # If empty or just whitespace, return a fallback
        if not assistant_response:
            assistant_response = "I'm not sure how to respond to that."

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [
                {"message": {"role": "assistant", "content": assistant_response}}
            ],
            "file_references": request.file_references or [],
        }
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "ready" if model else "loading",
        "model": MODEL_NAME,
        "device": DEVICE,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
