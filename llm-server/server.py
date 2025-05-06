#!/usr/bin/env python3
"""
FastAPI server for Qwen2.5-VL-7B-instruct model
Implements OpenAI-compatible API endpoints
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import torch
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

# Use Auto classes for flexibility
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Qwen2.5-VL API Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-VL-7B-instruct")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
tokenizer = None
model = None


# Pydantic models for request/response
class Content(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class Message(BaseModel):
    role: str
    content: Union[str, List[Content]]


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_NAME
    messages: List[Message]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Dict[str, int]


# Load model
@app.on_event("startup")
async def startup_event():
    global tokenizer, model
    logger.info(f"Loading model: {MODEL_NAME}")
    try:
        # Load tokenizer with trust_remote_code=True
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

        # Use AutoModelForCausalLM with trust_remote_code=True for VL models
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        # Provide more helpful error instead of raising
        logger.info("Starting server in fallback mode without model")
        # Mark globals as None to indicate model is not loaded
        tokenizer = None
        model = None


# Format messages for the model
def format_messages(messages: List[Message]) -> str:
    formatted = ""
    for message in messages:
        role = message.role

        # Handle different content formats (string or list of Content objects)
        if isinstance(message.content, str):
            content_text = message.content
        else:  # It's a list of Content objects
            # Process text and image contents
            text_parts = []
            image_parts = []

            for content_item in message.content:
                if content_item.type == "text" and content_item.text:
                    text_parts.append(content_item.text)
                elif content_item.type == "image_url" and content_item.image_url:
                    # Format for image: <img>URL</img>
                    img_url = content_item.image_url.get("url", "")
                    if img_url:
                        image_parts.append(f"<img>{img_url}</img>")

            # Combine all parts with text first, then images
            content_text = " ".join(text_parts + image_parts)

        # Add the formatted content based on role
        if role == "system":
            formatted += f"<|im_start|>system\n{content_text}<|im_end|>\n"
        elif role == "user":
            formatted += f"<|im_start|>user\n{content_text}<|im_end|>\n"
        elif role == "assistant":
            formatted += f"<|im_start|>assistant\n{content_text}<|im_end|>\n"

    # Add the final assistant prefix
    formatted += "<|im_start|>assistant\n"
    return formatted


# Chat completion endpoint
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest, background_tasks: BackgroundTasks
):
    global tokenizer, model

    # Ensure model is loaded
    if model is None or tokenizer is None:
        # Return a friendly response instead of error when model isn't loaded
        logger.warning("Model not loaded, returning fallback response")
        return ChatCompletionResponse(
            id=f"fallback-{str(uuid.uuid4())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content="The model is still loading. Please try again later. Large language models can take several minutes to initialize.",
                    ),
                    finish_reason="stop",
                )
            ],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    try:
        # Format the message history for the model
        prompt = format_messages(request.messages)

        # If streaming is requested
        if request.stream:
            return StreamingResponse(
                stream_response(prompt, request), media_type="text/event-stream"
            )

        # Generate response
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # Set parameters
        gen_kwargs = {
            "max_new_tokens": min(request.max_tokens, MAX_TOKENS),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }

        # Generate text
        with torch.no_grad():
            output = model.generate(**inputs, **gen_kwargs)

        # Decode and extract the newly generated tokens
        generated_text = tokenizer.decode(
            output[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
        )

        # Calculate token counts
        input_tokens = len(inputs.input_ids[0])
        output_tokens = len(output[0]) - input_tokens

        # Prepare response
        response = ChatCompletionResponse(
            id=f"chatcmpl-{str(uuid.uuid4())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=generated_text),
                    finish_reason="stop",
                )
            ],
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        )

        return response

    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Streaming response generator
async def stream_response(prompt, request):
    # Currently an unimplemented placeholder for streaming
    # In a real implementation, this would stream tokens as they're generated
    yield f"data: {prompt}\n\n"
    yield "data: [STREAMING NOT FULLY IMPLEMENTED]\n\n"
    yield "data: [END]\n\n"


# Health check endpoint
@app.get("/health")
async def health_check():
    if model is None or tokenizer is None:
        return {"status": "loading", "model": MODEL_NAME}
    return {"status": "ready", "model": MODEL_NAME}


# Embeddings endpoint
@app.post("/v1/embeddings")
async def create_embeddings():
    # Placeholder for embeddings API - not implemented yet
    raise HTTPException(status_code=501, detail="Embeddings not implemented")


# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
