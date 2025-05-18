'use client'
import { Message, useChatStore, Conversation } from '@/store/chatStore';
import { useEffect } from 'react';

export default function ChatMessages() {
  const { conversations, currentConversationId, fetchConversation, isLoading, error } = useChatStore();
  
  // Get the current conversation
  const currentConversation = conversations.find(conv => 
    conv._id === currentConversationId
  );
  
  // Fetch conversation messages when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      fetchConversation(currentConversationId);
    }
  }, [currentConversationId, fetchConversation]);
  
  // If no conversation is selected, show a placeholder
  if (!currentConversation) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 text-gray-400">
        {isLoading ? (
          <div>Loading conversation...</div>
        ) : (
          <div className="text-center">
            <p className="text-xl mb-2">No conversation selected</p>
            <p>Start a new chat or select an existing one</p>
          </div>
        )}
      </div>
    );
  }
  
  // Ensure messages array exists, otherwise use an empty array
  const messages = Array.isArray(currentConversation.messages) 
    ? currentConversation.messages 
    : [];
  
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((msg, index) => {
        // Determine if the message is from the user
        const isUser = msg.role === 'user';
        
        return (
          <div key={index} className={`mb-4 ${isUser ? 'text-right' : 'text-left'}`}>
            <div className={`inline-block max-w-[80%] p-3 rounded-lg ${
              isUser ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}>
              <div>{msg.content}</div>
              <div className={`text-xs mt-1 ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
                {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : 'Just now'}
                {/* Show RAG indicator if this message has context from documents */}
                {!isUser && msg.context && msg.context.used && (
                  <span className="ml-2 px-1 bg-green-100 text-green-800 rounded">
                    RAG ({msg.context.count} docs)
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
      
      {isLoading && (
        <div className="text-center py-2 text-gray-500">
          <div className="animate-pulse">AI is thinking...</div>
        </div>
      )}
      
      {error && (
        <div className="text-center py-2 text-red-500">
          Error: {error}
        </div>
      )}
    </div>
  );
}
