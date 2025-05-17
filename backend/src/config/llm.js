const axios = require('axios');

// LLM Server configuration
const LLM_HOST = process.env.LLM_HOST || 'localhost';
const LLM_PORT = process.env.LLM_PORT || '8080';
const LLM_API_URL = `http://${LLM_HOST}:${LLM_PORT}/v1`;  // Local Python server uses /v1 prefix for OpenAI API

// Client for making requests to the LLM service
class LLMClient {
  constructor() {
    this.client = axios.create({
      baseURL: LLM_API_URL,
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 120000 // 120 seconds timeout for LLM requests (may need longer for large contexts)
    });
  }

  /**
   * Send a chat completion request to the LLM server
   * @param {Array} messages Array of message objects with role and content
   * @param {Object} options Additional options for the LLM
   * @returns {Promise} Promise resolving to the LLM response
   */
  async chatCompletion(messages, options = {}) {
    try {
      // Check if LLM server is ready before making the request
      const isReady = await this.isModelReady();
      if (!isReady) {
        console.log('LLM model is still loading. Using fallback response.');
        // Return a fallback response while the model is loading
        return {
          id: `fallback-${Date.now()}`,
          object: 'chat.completion',
          created: Math.floor(Date.now() / 1000),
          model: options.model || 'Qwen/Qwen2.5-VL-7B-instruct',  // The model we configured
          choices: [
            {
              index: 0,
              message: {
                role: 'assistant',
                content: 'I am still initializing. Please try again in a few minutes while the model loads.'
              },
              finish_reason: 'stop'
            }
          ],
          usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
        };
      }

      // Proceed with the normal request if the model is ready
      const response = await this.client.post('/chat/completions', {
        messages,
        model: options.model || 'Qwen/Qwen2.5-VL-7B-instruct',
        max_tokens: options.max_tokens || 1024,
        temperature: options.temperature || 0.7,
        top_p: options.top_p || 0.9,
        stream: options.stream || false
      });

      return response.data;
    } catch (error) {
      console.error('LLM Chat Completion Error:', error.message);
      if (error.response) {
        console.error('Response data:', error.response.data);
      }
      
      // Return a graceful fallback response instead of throwing
      return {
        id: `error-${Date.now()}`,
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model: options.model || 'Qwen/Qwen2.5-VL-7B-instruct',
        choices: [
          {
            index: 0,
            message: {
              role: 'assistant',
              content: 'Sorry, I encountered an error processing your request. The AI service might be temporarily unavailable.'
            },
            finish_reason: 'stop'
          }
        ],
        usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
      };
    }
  }

  /**
   * Get embeddings for text from the LLM server
   * @param {String} text Text to generate embeddings for
   * @returns {Promise} Promise resolving to the embeddings
   */
  async getEmbeddings(text) {
    try {
      const response = await this.client.post('/embeddings', {
        input: text,
        model: 'Qwen/Qwen2.5-VL-7B-instruct'
      });

      return response.data;
    } catch (error) {
      console.error('LLM Embeddings Error:', error.message);
      throw new Error('Failed to get embeddings from LLM service');
    }
  }

  /**
   * Check if the LLM model is fully loaded and ready
   * @returns {Promise<boolean>} Promise resolving to true if the model is ready
   */
  async isModelReady() {
    try {
      // Remove /v1 prefix for health endpoint
      const response = await axios.get(`http://${LLM_HOST}:${LLM_PORT}/health`);
      // Check if the status is "ready", not just if the request succeeded
      return response.data && response.data.status === 'ready';
    } catch (error) {
      console.log('LLM Model not ready yet:', error.message);
      return false;
    }
  }

  /**
   * Health check for the LLM service
   * @returns {Promise<boolean>} Promise resolving to true if healthy
   */
  async healthCheck() {
    try {
      // Remove /v1 prefix for health endpoint
      const response = await axios.get(`http://${LLM_HOST}:${LLM_PORT}/health`);
      return response.status === 200;
    } catch (error) {
      console.error('LLM Health Check Failed:', error.message);
      return false;
    }
  }
}

// Create and export a singleton instance
const llmClient = new LLMClient();
module.exports = llmClient;
