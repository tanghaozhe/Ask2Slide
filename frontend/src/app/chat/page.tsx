'use client'
import { useState } from 'react'
import Sidebar from './components/Sidebar'
import { useChatStore } from '@/store/chatStore'

export default function ChatPage() {
  const { recentChats, currentChatId, addMessage } = useChatStore()
  const [input, setInput] = useState('')

  const currentChat = recentChats.find(chat => chat.id === currentChatId)
  const messages = currentChat?.messages || []

  const handleSend = () => {
    if (input.trim() && currentChatId) {
      addMessage(currentChatId, {
        content: input,
        isUser: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      })
      setInput('')
      // TODO: Add AI response
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`mb-4 ${msg.isUser ? 'text-right' : 'text-left'}`}>
              <div className={`inline-block max-w-[80%] p-3 rounded-lg ${msg.isUser ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>
                <div>{msg.content}</div>
                <div className={`text-xs mt-1 ${msg.isUser ? 'text-blue-100' : 'text-gray-500'}`}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-gray-200">
          <div className="flex">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              className="flex-1 p-2 border rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Type your message..."
            />
            <button
              onClick={handleSend}
              className="bg-blue-500 text-white p-2 rounded-r-lg hover:bg-blue-600"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
