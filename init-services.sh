#!/bin/bash

# Initialize services for Ask2Slide
echo "Initializing services for Ask2Slide..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Pull images first to avoid connection timeout issues during service start
echo "Pulling Docker images..."
docker pull mongo:6.0
docker pull quay.io/minio/minio:RELEASE.2023-07-21T21-12-44Z
docker pull pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Start MongoDB service
echo "Starting MongoDB service..."
docker-compose up -d mongodb
echo "MongoDB started."

# Start MinIO service
echo "Starting MinIO service..."
docker-compose up -d minio
echo "MinIO started."

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 15

# Check if MinIO is running
if ! docker ps | grep ask2slide-minio > /dev/null; then
    echo "Warning: MinIO container is not running. Will try to create bucket later."
else
    echo "Creating MinIO bucket..."
    docker exec ask2slide-minio wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc 2>/dev/null || true
    docker exec ask2slide-minio chmod +x /usr/bin/mc 2>/dev/null || true
    docker exec ask2slide-minio mc alias set myminio http://localhost:9010 ask2slide_minio m1n10P@ssw0rd || echo "Failed to set MinIO alias, but continuing..."
    docker exec ask2slide-minio mc mb myminio/ai-chat || echo "Failed to create MinIO bucket, but continuing..."
    echo "Setting bucket policy..."
    docker exec ask2slide-minio mc policy set download myminio/ai-chat || echo "Failed to set bucket policy, but continuing..."
fi

# Download Qwen2.5-VL model if not present
echo "Checking for Qwen2.5-VL model directory..."
MODEL_DIR="./models/Qwen/Qwen2.5-VL-7B-instruct"

if [ -d "$MODEL_DIR" ]; then
    echo "Model directory exists, skipping download."
else
    echo "Model directory not found. Downloading Qwen2.5-VL model (this may take 30+ minutes)..."
    mkdir -p "$MODEL_DIR"
    echo "----------------------------------------"
    if docker run --rm -it \
        -v "$(pwd)/models:/models" \
        -e HF_HUB_ENABLE_HF_TRANSFER=0 \
        -e HF_HUB_DISABLE_PROGRESS_BARS=0 \
        -e PYTHONWARNINGS="ignore::UserWarning" \
        pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime \
        bash -c "pip install -q huggingface-hub[hf_xet] && \
                  huggingface-cli download Qwen/Qwen2.5-VL-7B-instruct \
                  --local-dir /models/Qwen/Qwen2.5-VL-7B-instruct \
                  --force-download"; then
        chmod -R 755 "$MODEL_DIR"
        echo "Model download completed successfully."
    else
        echo "Download failed. Cleaning up..."
        rm -rf "$MODEL_DIR"
        echo "Please try again."
        exit 1
    fi
fi

# Note: The LLM server is now run directly with Python, not through Docker

echo ""
echo "Initialization complete!"
echo ""
echo "Services:"
echo " - MongoDB: mongodb://localhost:27018"
echo " - MinIO API: http://localhost:9010"
echo " - MinIO Console: http://localhost:9011"
echo " - LLM Server: http://localhost:8080 (run manually with 'python llm-server/server.py')"
echo ""
echo "MinIO Console Access:"
echo " - URL: http://localhost:9011"
echo " - Username: ask2slide_minio"
echo " - Password: m1n10P@ssw0rd"
echo ""
echo "API Test Commands:"
echo " - Test LLM: curl http://localhost:8080/health"
echo " - Full test (after model loads): curl http://localhost:8080/v1/chat/completions -H \"Content-Type: application/json\" -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo " - Test Backend (after starting it): curl http://localhost:3001/health"
echo ""
echo "To stop all services, run: docker-compose down"
echo ""
echo "Note: The LLM server may take some time to fully initialize as it downloads and loads the model."
