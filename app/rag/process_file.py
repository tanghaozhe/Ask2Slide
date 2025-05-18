import asyncio
import copy
import uuid

import numpy as np

from app.core.logging import logger
from app.db.milvus import milvus_client
from app.db.minio import async_minio_manager
from app.db.mongo import get_mongo
from app.rag.convert_file import convert_file_to_images, save_image_to_minio
from app.rag.get_embedding import get_embeddings_from_httpx

# Note: This implementation utilizes the API server defined in app/core/model_server.py,
# which uses app/rag/colbert_service.py to provide embedding endpoints.
# The API server needs to be running at localhost:8005 for this implementation to work.


def sort_and_filter(data, min_score=None, max_score=None):
    """
    Sort and filter search results by score
    """
    # Filter by score
    if min_score is not None:
        data = [item for item in data if item["score"] >= min_score]
    if max_score is not None:
        data = [item for item in data if item["score"] <= max_score]
    # Sort by score (descending)
    sorted_data = sorted(data, key=lambda x: x["score"], reverse=True)
    return sorted_data


async def update_task_progress(redis, task_id, status, message):
    """
    Update the processing task status in Redis
    """
    await redis.hset(f"task:{task_id}", mapping={"status": status, "message": message})


async def handle_processing_error(redis, task_id, error_msg):
    """
    Handle errors during file processing
    """
    await redis.hset(
        f"task:{task_id}", mapping={"status": "failed", "message": error_msg}
    )


async def process_file(redis, task_id, username, knowledge_db_id, file_meta):
    """
    Process a file (PDF) through the full RAG pipeline:
    1. Download from MinIO
    2. Convert to images
    3. Save images to MinIO
    4. Generate embeddings
    5. Insert to Milvus
    """
    try:
        # Get file content from MinIO
        file_content = await async_minio_manager.get_file_from_minio(
            file_meta["minio_filename"]
        )

        # Convert file to images
        images_buffer = await convert_file_to_images(file_content)

        # Save images and generate embeddings
        image_ids = []
        for i, image_buffer in enumerate(images_buffer):
            # Save image to MinIO
            minio_imagename, image_url = await save_image_to_minio(
                username, file_meta["original_filename"], image_buffer
            )

            # Save image metadata to MongoDB
            image_id = f"{username}_{uuid.uuid4()}"
            db = await get_mongo()
            await db.add_images(
                file_id=file_meta["file_id"],
                images_id=image_id,
                minio_filename=minio_imagename,
                minio_url=image_url,
                page_number=i + 1,
            )
            image_ids.append(image_id)
        logger.info(
            f"task:{task_id}: save images of {file_meta['original_filename']} to minio and mongodb"
        )

        # Generate embeddings from images
        embeddings = await generate_embeddings(
            images_buffer, file_meta["original_filename"]
        )
        logger.info(
            f"task:{task_id}: {file_meta['original_filename']} generate_embeddings!"
        )

        # Insert embeddings to Milvus
        collection_name = f"colqwen{knowledge_db_id.replace('-', '_')}"
        await insert_to_milvus(
            collection_name, embeddings, image_ids, file_meta["file_id"]
        )
        logger.info(
            f"task:{task_id}: images of {file_meta['original_filename']} insert to milvus {collection_name}!"
        )

        # Update task progress
        await redis.hincrby(f"task:{task_id}", "processed", 1)
        current = int(await redis.hget(f"task:{task_id}", "processed"))
        total = int(await redis.hget(f"task:{task_id}", "total"))
        logger.info(f"task:{task_id} files processed + 1!")

        # Check if all files are processed
        if current == total:
            await redis.hset(f"task:{task_id}", "status", "completed")
            await redis.hset(
                f"task:{task_id}", "message", "All files processed successfully"
            )
            logger.info(f"task:{task_id} All files processed successfully")

    except Exception as e:
        await handle_processing_error(
            redis, task_id, f"File processing failed: {str(e)}"
        )
        raise


async def generate_embeddings(images_buffer, filename):
    """
    Generate embeddings from image buffers using the LLM service
    """
    # Prepare images for the HTTP request
    images_request = [
        ("images", (f"{filename}_{i}.png", img, "image/png"))
        for i, img in enumerate(images_buffer)
    ]
    return await get_embeddings_from_httpx(images_request, endpoint="embed_image")


async def insert_to_milvus(collection_name, embeddings, image_ids, file_id):
    """
    Insert embeddings to Milvus collection
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: [
            milvus_client.insert(
                {
                    "colqwen_vecs": emb,
                    "page_number": i,
                    "image_id": image_ids[i],
                    "file_id": file_id,
                },
                collection_name,
            )
            for i, emb in enumerate(embeddings)
        ],
    )


async def replace_image_content(messages):
    """
    Replace image URLs with base64 encoded image content in chat messages
    """
    # Create deep copy to ensure original data is unchanged
    new_messages = copy.deepcopy(messages)

    # Iterate through each message
    for message in new_messages:
        if "content" not in message:
            continue

        # Iterate through each content item
        for item in message["content"]:
            if isinstance(item, dict):
                # Check if the type is image_url
                if item.get("type") == "image_url":
                    image_base64 = (
                        await async_minio_manager.download_image_and_convert_to_base64(
                            item["image_url"]
                        )
                    )
                    item["image_url"] = {"url": f"data:image/png;base64,{image_base64}"}

    return new_messages
