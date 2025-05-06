'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useChatStore } from '@/store/chatStore'
import { useState } from 'react'

export default function Sidebar() {
  const router = useRouter()
  const { 
    conversations, 
    currentConversationId, 
    setCurrentConversation, 
    createConversation,
    deleteConversation,
    isLoading
  } = useChatStore()
  
  const [isCreating, setIsCreating] = useState(false);
  
  const handleNewChat = async () => {
    setIsCreating(true);
    try {
      const newChatId = await createConversation(`Chat ${new Date().toLocaleString()}`);
      if (newChatId) {
        setCurrentConversation(newChatId);
        router.push('/chat');
      }
    } catch (error) {
      console.error('Failed to create new chat:', error);
    } finally {
      setIsCreating(false);
    }
  };
  
  const handleSelectChat = (id: string) => {
    setCurrentConversation(id);
    router.push('/chat');
  };
  
  const handleDeleteChat = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(id);
    }
  };
  
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    
    // If it's today, show the time
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // If it's in the last week, show the day name
    const oneWeekAgo = new Date(now);
    oneWeekAgo.setDate(now.getDate() - 7);
    if (date > oneWeekAgo) {
      return date.toLocaleDateString([], { weekday: 'long' });
    }
    
    // Otherwise show the date
    return date.toLocaleDateString();
  };
  
  return (
    <div className="w-64 bg-white border-r border-gray-200 p-4">
      <h2 className="text-xl font-bold mb-4">Chat Sessions</h2>
      <nav>
        <ul className="space-y-2">
          <li>
            <button
              className="w-full text-left p-2 rounded hover:bg-gray-100 font-bold"
              onClick={handleNewChat}
              disabled={isCreating || isLoading}
            >
              {isCreating ? 'Creating...' : 'New Chat'}
            </button>
          </li>
          <li>
            <Link href="/library" className="block p-2 rounded hover:bg-gray-100 font-bold">
              Document Library
            </Link>
          </li>
        </ul>
      </nav>
      <div className="mt-8">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          Recent Chats
        </h3>
        <ul className="mt-2 space-y-1">
          {isLoading && conversations.length === 0 ? (
            <li className="text-sm p-2 text-gray-500">Loading conversations...</li>
          ) : conversations.length === 0 ? (
            <li className="text-sm p-2 text-gray-500">No recent conversations</li>
          ) : (
            conversations.map(conv => (
              <li 
                key={conv._id} 
                className={`text-sm p-2 rounded cursor-pointer group ${
                  conv._id === currentConversationId 
                    ? 'bg-blue-100 text-blue-800' 
                    : 'hover:bg-gray-100'
                }`}
                onClick={() => handleSelectChat(conv._id)}
              >
                <div className="font-medium flex justify-between items-center">
                  <span className="truncate">{conv.title}</span>
                  <button 
                    className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => handleDeleteChat(e, conv._id)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
                <div className={`text-xs ${
                  conv._id === currentConversationId ? 'text-blue-600' : 'text-gray-500'
                }`}>
                  {formatDate(conv.updated_at)}
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
