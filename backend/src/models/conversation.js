const mongoose = require('mongoose');

// Message schema
const messageSchema = new mongoose.Schema({
  role: {
    type: String,
    enum: ['system', 'user', 'assistant'],
    required: true
  },
  content: {
    type: String,
    required: true
  },
  created_at: {
    type: Date,
    default: Date.now
  }
});

// Conversation schema
const conversationSchema = new mongoose.Schema({
  user_id: {
    type: String,
    required: true,
    index: true
  },
  title: {
    type: String,
    default: 'New Conversation'
  },
  messages: [messageSchema],
  knowledge_base_id: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'KnowledgeBase',
    index: true
  },
  created_at: {
    type: Date,
    default: Date.now,
    index: true // TTL index will be created on this field
  },
  updated_at: {
    type: Date,
    default: Date.now
  }
});

// Pre-save middleware to update the 'updated_at' field
conversationSchema.pre('save', function(next) {
  this.updated_at = Date.now();
  next();
});

// Create a TTL index to expire conversations after 1 week (604800 seconds)
conversationSchema.index({ created_at: 1 }, { expireAfterSeconds: 604800 });

const Conversation = mongoose.model('Conversation', conversationSchema);

module.exports = Conversation;
