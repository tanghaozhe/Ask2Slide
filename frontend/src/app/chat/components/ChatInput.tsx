'use client'
import { useState } from 'react';
import { useChatStore } from '@/store/chatStore';

export default function ChatInput() {
  const [input, setInput] = useState('');
  const { sendMessage, currentConversationId, isLoading } = useChatStore();

  const handleSend = async () => {
    if (input.trim() === '' || isLoading) return;
    
    try {
      // Convert null to undefined for type compatibility
      const conversationId = currentConversationId || undefined;
      await sendMessage(input, conversationId);
      setInput('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className="p-4 border-t border-gray-200">
      <div className="flex">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="flex-1 p-2 border rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          className={`p-2 rounded-r-lg text-white ${
            isLoading 
              ? 'bg-blue-300 cursor-not-allowed' 
              : 'bg-blue-500 hover:bg-blue-600'
          }`}
          disabled={isLoading}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
