# Ask2Slide

**Ask2Slide** is a visual RAG (Retrieval-Augmented Generation) system that enables intelligent, dialogue-driven interaction with slide-based content.

Instead of treating documents as plain text, Ask2Slide leverages the power of **Qwen2.5-VL**, a multimodal large language model, to understand and retrieve **Slides** as visually structured artifacts — preserving layout, tables, figures, and semantic intent.

## 🚀 Features

- 🎯 **Visual-first Retrieval**: Retrieve the most relevant slide content based on user queries, powered by visual embeddings rather than token sequences.
- 🧠 **Q&A, Slide Summarization & Suggestion**: Use natural language to ask questions, get summaries, or generate suggestions for building your own presentation.
- 💬 **Conversational Slide Composer**: Ask2Slide not only indexes slides, but also helps organize talking points, narration scripts, and logical flow for a compelling presentation.

## 🧠 Services

Ask2Slide uses several services:

- **MongoDB**: Stores document metadata, chat history, and references to files
- **MinIO**: Stores the actual document files (PDFs, images, etc.)
- **Qwen2.5-VL**: Multimodal large language model for visual reasoning and chat

### Setup

1. Make sure you have Docker and Docker Compose installed
2. Run the initialization script to start the services:

```bash
./init-services.sh
```

This will:
- Start MongoDB and MinIO containers
- Create the necessary MinIO bucket
- Start the Qwen2.5-VL model server
- Configure the services for use with Ask2Slide

Note: The first run will download the Qwen2.5-VL model from Hugging Face, which may take some time.

### Access

- **MongoDB**: Available at `mongodb://localhost:27017`
- **MinIO API**: Available at `http://localhost:9000`
- **MinIO Console**: Available at `http://localhost:9001`
- **LLM API**: Available at `http://localhost:8000`

### Running the Chat Interface

After starting the services:

1. Start the backend API server:
   ```bash
   cd backend
   npm install
   npm run dev
   ```

2. Start the frontend (in a separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. Access the application at: http://localhost:3000

For more details, see the [backend documentation](backend/README.md).
