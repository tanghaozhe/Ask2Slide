# Ask2Slide Backend

This directory contains the backend implementation for Ask2Slide.

## Services Configuration

The project uses the following services:
- **MongoDB**: For storing document metadata and chat conversations
- **MinIO**: For storing the actual document files
- **LLM Server**: For handling chat completions with Qwen2.5-VL

These services are configured in the `docker-compose.yml` file at the project root.

## Getting Started

### 1. Model Setup

The LLM server is configured to use the Qwen2.5-VL-7B-instruct model directly from Hugging Face. The model will be automatically downloaded when you first start the container.

You don't need to manually download anything, but if you prefer to have the model available offline:

```bash
# Install Git LFS if you don't have it
git lfs install

# Clone the repository to the models directory
git clone https://huggingface.co/Qwen/Qwen2.5-VL-7B-instruct ./models/Qwen2.5-VL-7B-instruct

# Update the docker-compose.yml environment to use local path
# MODEL_NAME=/models/Qwen2.5-VL-7B-instruct
```

### 2. Start the Services

Run the initialization script to start all services:

```bash
./init-services.sh
```

Or manually start with docker-compose:

```bash
docker-compose up -d
```

### 3. Start the Backend API Server

Install the dependencies and start the server:

```bash
cd backend
npm install
npm run dev
```

The API server will be available at http://localhost:3001

## Service Details

### MongoDB Configuration

- **Connection URL**: `mongodb://ask2slide_admin:s3cur3P@ssw0rd@localhost:27017/`
- **Database**: `ask2slide`
- **Collections**: 
  - `knowledge_bases`: For document metadata
  - `conversations`: For chat history (with TTL of 1 week)

#### Knowledge Base Schema

```javascript
{
  "_id": ObjectId,                // MongoDB generated ID
  "knowledge_base_id": String,    // Custom ID for the knowledge base
  "knowledge_base_name": String,  // Name of the knowledge base
  "username": String,             // Owner of the knowledge base
  "files": [                      // Array of files in the knowledge base
    {
      "file_id": String,          // Custom ID for the file
      "filename": String,         // Original filename
      "minio_filename": String,   // Filename in MinIO
      "minio_url": String,        // URL to access the file in MinIO
      "created_at": Date          // When the file was added
    }
  ],
  "used_chat": [],                // Array of chat IDs that used this knowledge base
  "created_at": Date,             // When the knowledge base was created
  "last_modify_at": Date,         // When the knowledge base was last modified
  "is_delete": Boolean            // Soft delete flag
}
```

#### Conversation Schema

```javascript
{
  "_id": ObjectId,                // MongoDB generated ID
  "user_id": String,              // User identifier
  "title": String,                // Conversation title
  "messages": [                   // Array of messages
    {
      "role": String,             // 'user', 'assistant', or 'system'
      "content": String,          // Message content
      "created_at": Date          // Message timestamp
    }
  ],
  "knowledge_base_id": ObjectId,  // Reference to knowledge base (optional)
  "created_at": Date,             // Conversation creation time (with TTL index)
  "updated_at": Date              // Last update time
}
```

### MinIO Configuration

- **Console URL**: `http://localhost:9001`
- **API URL**: `http://localhost:9000`
- **Access Key**: `ask2slide_minio`
- **Secret Key**: `m1n10P@ssw0rd`
- **Bucket**: `ai-chat`

#### File Naming Convention

Files in MinIO follow this naming convention:
```
{username}_{original_filename}_{mongodb_id}.{extension}
```

For example:
```
thz_Designing Machine Learning Systems_6816dcf438b26df8d2eaf707.pdf
```

### LLM Server Configuration

- **API URL**: `http://localhost:8000`
- **Model**: Qwen2.5-VL-7B-instruct
- **Endpoint**: `/v1/chat/completions` - OpenAI-compatible API
- **Implementation**: Custom FastAPI server with Hugging Face Transformers

The LLM server is configured to use the PyTorch image with Transformers library to load and serve the Qwen2.5-VL model. This approach:

1. Uses publicly available Docker images to avoid authentication issues
2. Automatically downloads the model from Hugging Face on first run
3. Provides a compatible API interface matching the OpenAI format
4. Can be adapted to use other models by changing the MODEL_NAME environment variable

## API Endpoints

The backend provides the following RESTful API endpoints:

### Chat API

- `GET /api/chat/conversations` - Get all conversations for a user
- `GET /api/chat/conversation/:id` - Get a specific conversation with messages
- `POST /api/chat/conversation` - Create a new conversation
- `POST /api/chat/message` - Send a message and get AI response
- `DELETE /api/chat/conversation/:id` - Delete a conversation

### Document API (Future Implementation)

- `POST /api/documents/upload` - Upload a document file
- `GET /api/documents/list` - List all documents
- `GET /api/documents/:id` - Get document details
- `DELETE /api/documents/:id` - Delete a document

## Example Usage

See the `example.js` file in this directory for code examples demonstrating how to:

1. Create knowledge bases
2. Upload files to MinIO and store metadata in MongoDB
3. Retrieve document information
4. Delete documents and knowledge bases
