from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Model paths
    colbert_model_path: str = "Qwen/Qwen2.5-VL-7B-instruct"

    # MongoDB settings
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "ask2slide"

    # Milvus settings
    milvus_host: str = "localhost"
    milvus_port: str = "19530"

    # Document processing
    chunk_size: int = 1024
    chunk_overlap: int = 200

    # File storage
    upload_dir: str = "./uploads"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8085  # Changed from 8005 to avoid potential conflicts

    model_config = {"env_file": ".env"}


settings = Settings()
