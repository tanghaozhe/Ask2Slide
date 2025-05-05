'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useChatStore } from '@/store/chatStore'

export default function Sidebar() {
  const router = useRouter()
  const { recentChats, currentChatId, setCurrentChat, addChat } = useChatStore()
  return (
    <div className="w-64 bg-white border-r border-gray-200 p-4">
      <h2 className="text-xl font-bold mb-4">Chat Sessions</h2>
      <nav>
        <ul className="space-y-2">
          <li>
            <Link 
              href="/chat" 
              className="block p-2 rounded hover:bg-gray-100 font-bold"
              onClick={() => {
                const newChatId = Date.now()
                addChat({
                  title: `Chat ${new Date().toLocaleString()}`,
                  time: 'Just now',
                  messages: []
                })
                setCurrentChat(newChatId)
              }}
            >
              New Chat
            </Link>
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
          {recentChats.map(chat => (
            <li 
              key={chat.id} 
              className={`text-sm p-2 rounded cursor-pointer ${
                chat.id === currentChatId 
                  ? 'bg-blue-100 text-blue-800' 
                  : 'hover:bg-gray-100'
              }`}
              onClick={() => {
                setCurrentChat(chat.id)
                router.push('/chat')
              }}
            >
              <div className="font-medium">{chat.title}</div>
              <div className={`text-xs ${
                chat.id === currentChatId ? 'text-blue-600' : 'text-gray-500'
              }`}>
                {chat.time}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
