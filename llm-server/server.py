#!/usr/bin/env python3
"""
FastAPI server for Qwen model running locally with MPS
"""

import logging
import os
import time
import uuid
from typing import List, Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoModelForVision2Seq, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Qwen Local API Server")

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
    "/Users/tangh56/Documents/Project/Ask2Slide/models/Qwen/Qwen2.5-VL-7B-instruct",
)
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
model = None
tokenizer = None


# Pydantic models
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


# Initialize model
@app.on_event("startup")
async def load_model():
    global model, tokenizer
    try:
        logger.info(f"Loading {MODEL_NAME} on {DEVICE}...")

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForVision2Seq.from_pretrained(
            MODEL_NAME, torch_dtype=torch.float16
        ).to(DEVICE)

        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise


# Chat endpoint
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Format messages for Qwen
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Generate response
        inputs = tokenizer.apply_chat_template(messages, return_tensors="pt").to(DEVICE)

        outputs = model.generate(
            inputs,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            do_sample=True,
        )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [{"message": {"role": "assistant", "content": response}}],
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
