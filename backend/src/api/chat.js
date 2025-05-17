const express = require('express');
const router = express.Router();
const Conversation = require('../models/conversation');
const llmClient = require('../config/llm');
const axios = require('axios');

// RAG API configuration
const RAG_HOST = process.env.RAG_HOST || 'localhost';
const RAG_PORT = process.env.RAG_PORT || '8085';
const RAG_API_URL = `http://${RAG_HOST}:${RAG_PORT}`;

/**
 * GET /api/chat/conversations
 * Get all conversations for a user
 */
router.get('/conversations', async (req, res) => {
  try {
    // In a real application, you would get the user ID from authentication
    const userId = req.query.user_id || 'default_user';
    
    const conversations = await Conversation.find({ 
      user_id: userId,
      // Don't include the full messages array in the list
    }).select('_id title knowledge_base_id created_at updated_at')
      .sort({ updated_at: -1 });
    
    res.json(conversations);
  } catch (error) {
    console.error('Error fetching conversations:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
});

/**
 * GET /api/chat/conversation/:id
 * Get a specific conversation with its messages
 */
router.get('/conversation/:id', async (req, res) => {
  try {
    const conversation = await Conversation.findById(req.params.id);
    
    if (!conversation) {
      return res.status(404).json({ message: 'Conversation not found' });
    }
    
    res.json(conversation);
  } catch (error) {
    console.error('Error fetching conversation:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
});

/**
 * POST /api/chat/conversation
 * Create a new conversation
 */
router.post('/conversation', async (req, res) => {
  try {
    // In a real application, you would get the user ID from authentication
    const userId = req.body.user_id || 'default_user';
    
    const newConversation = new Conversation({
      user_id: userId,
      title: req.body.title || 'New Conversation',
      knowledge_base_id: req.body.knowledge_base_id || null,
      messages: []
    });
    
    await newConversation.save();
    res.status(201).json(newConversation);
  } catch (error) {
    console.error('Error creating conversation:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
});

/**
 * Retrieve relevant documents from the RAG system
 * @param {string} query - The user's query
 * @param {string} kbId - Knowledge base ID
 * @returns {Promise<Array>} - Array of relevant document chunks
 */
async function retrieveRelevantDocuments(query, kbId) {
  try {
    if (!kbId) {
      console.log('No knowledge base ID provided, skipping RAG retrieval');
      return [];
    }
    
    // Call the RAG API to search for relevant documents
    const response = await axios.post(`${RAG_API_URL}/hybrid_search`, {
      query,
      kb_id: kbId,
      top_k: 3 // Retrieve top 3 most relevant chunks
    });
    
    return response.data.results || [];
  } catch (error) {
    console.error('Error retrieving documents from RAG:', error);
    return []; // Return empty array on error
  }
}

/**
 * Format retrieved documents as context for the LLM
 * @param {Array} documents - Retrieved document chunks
 * @returns {string} - Formatted context string
 */
function formatRetrievedContext(documents) {
  if (!documents || documents.length === 0) {
    return '';
  }
  
  let context = 'Here are some relevant documents that might help answer the query:\n\n';
  
  documents.forEach((doc, index) => {
    context += `Document ${index + 1}:\n${doc.text}\n\n`;
  });
  
  context += 'Please use this information to help answer the user\'s question.\n';
  
  return context;
}

/**
 * POST /api/chat/message
 * Send a message and get a response from the LLM
 */
router.post('/message', async (req, res) => {
  try {
    const { conversation_id, message, user_id = 'default_user' } = req.body;
    
    if (!message) {
      return res.status(400).json({ message: 'Message content is required' });
    }
    
    let conversation;
    
    // Find or create a conversation
    if (conversation_id) {
      conversation = await Conversation.findById(conversation_id);
      if (!conversation) {
        return res.status(404).json({ message: 'Conversation not found' });
      }
    } else {
      // Create a new conversation with the first message
      conversation = new Conversation({
        user_id,
        title: message.substring(0, 30) + (message.length > 30 ? '...' : ''),
        messages: [],
        knowledge_base_id: req.body.knowledge_base_id || null
      });
    }
    
    // Add the user message to the conversation
    conversation.messages.push({
      role: 'user',
      content: message
    });
    
    // Get the complete history for context
    const messageHistory = conversation.messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));
    
    // If the conversation has a knowledge base ID, retrieve relevant documents
    let relevantDocuments = [];
    if (conversation.knowledge_base_id) {
      relevantDocuments = await retrieveRelevantDocuments(message, conversation.knowledge_base_id);
      
      // If we have relevant documents, add them as system message context
      if (relevantDocuments.length > 0) {
        const context = formatRetrievedContext(relevantDocuments);
        
        // Add a system message with the context
        messageHistory.unshift({
          role: 'system',
          content: context
        });
      }
    }
    
    // Send the message history to the LLM
    const llmResponse = await llmClient.chatCompletion(messageHistory);
    
    // Extract the assistant's response
    const assistantResponse = llmResponse.choices[0].message.content;
    
    // Add the assistant's response to the conversation
    conversation.messages.push({
      role: 'assistant',
      content: assistantResponse
    });
    
    // Update the conversation's updated_at timestamp
    conversation.updated_at = Date.now();
    
    // Save the updated conversation
    await conversation.save();
    
    // Return the updated conversation with the LLM response
    res.json({
      conversation_id: conversation._id,
      message: assistantResponse,
      updated_at: conversation.updated_at,
      context: relevantDocuments.length > 0 ? {
        used: true,
        count: relevantDocuments.length
      } : { used: false }
    });
  } catch (error) {
    console.error('Error processing message:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
});

/**
 * DELETE /api/chat/conversation/:id
 * Delete a conversation
 */
router.delete('/conversation/:id', async (req, res) => {
  try {
    const result = await Conversation.findByIdAndDelete(req.params.id);
    
    if (!result) {
      return res.status(404).json({ message: 'Conversation not found' });
    }
    
    res.json({ message: 'Conversation deleted successfully' });
  } catch (error) {
    console.error('Error deleting conversation:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
});

module.exports = router;
