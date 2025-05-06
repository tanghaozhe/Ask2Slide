const express = require('express');
const router = express.Router();
const Conversation = require('../models/conversation');
const llmClient = require('../config/llm');

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
        messages: []
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
      updated_at: conversation.updated_at
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
