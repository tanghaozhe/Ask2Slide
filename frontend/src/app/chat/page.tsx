'use client'
import { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatMessages from './components/ChatMessages'
import ChatInput from './components/ChatInput'
import { useChatStore } from '@/store/chatStore'

export default function ChatPage() {
  const { fetchConversations, error, clearError } = useChatStore();
  
  // Fetch conversations on component mount
  useEffect(() => {
    fetchConversations();
    
    // Clean up error state on unmount
    return () => {
      clearError();
    };
  }, [fetchConversations, clearError]);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <ChatMessages />
        <ChatInput />
      </div>
    </div>
  )
}
