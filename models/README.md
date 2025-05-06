# Models Directory

This directory is used to store and access the Qwen2.5-VL model.

## Using the Model

The LLM server is configured to use the Hugging Face Transformers library to load the Qwen2.5-VL model directly. The model will be downloaded automatically when the Docker container starts.

**First run**: The initial run will automatically download the model files from Hugging Face. This may take some time depending on your internet connection as the model is approximately 14GB.

## Model Cache (Optional)

If you want to pre-download the model files for offline use or to speed up container startup:

```bash
# Install Git LFS if you don't have it
git lfs install

# Clone the model repository to this directory
git clone https://huggingface.co/Qwen/Qwen2.5-VL-7B-instruct ./Qwen2.5-VL-7B-instruct
```

The model will be cached in this directory for faster loading in subsequent runs.

## Model Information

- **Name**: Qwen2.5-VL
- **Size**: 7B parameters
- **Version**: Instruction-tuned
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-7B-instruct
- **Capabilities**: 
  - Multimodal understanding (text + images)
  - Chat completion with instructions
  - Visual reasoning
  - Slide content analysis

## Testing the Model

After starting the services, you can test the model using:

```bash
# Check if the model is loaded
curl http://localhost:8000/health

# Send a simple message once loaded
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```

Note that the first request may take a while to process as the model is being loaded into memory.
