import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: string;
}

interface Chat {
  id: number;
  title: string;
  time: string;
  messages: Message[];
}

interface ChatStore {
  recentChats: Chat[];
  currentChatId: number | null;
  addChat: (chat: Omit<Chat, 'id'>) => void;
  removeChat: (id: number) => void;
  setCurrentChat: (id: number) => void;
  addMessage: (chatId: number, message: Omit<Message, 'id'>) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
  recentChats: [
    {
      id: 1,
      title: 'Project Discussion',
      time: '2 hours ago',
      messages: [
        { id: 1, content: 'What are the project requirements?', isUser: true, timestamp: '2:30 PM' },
        { id: 2, content: 'The project requires building a chat interface with Next.js and Zustand.', isUser: false, timestamp: '2:32 PM' }
      ]
    },
    {
      id: 2,
      title: 'Meeting Notes',
      time: 'Yesterday',
      messages: [
        { id: 1, content: 'Can you summarize the meeting?', isUser: true, timestamp: '10:00 AM' },
        { id: 2, content: 'We discussed the UI design and agreed on a minimalist approach.', isUser: false, timestamp: '10:02 AM' }
      ]
    },
    {
      id: 3,
      title: 'Document Review',
      time: '2 days ago',
      messages: [
        { id: 1, content: 'Please review the technical specifications', isUser: true, timestamp: '3:15 PM' },
        { id: 2, content: 'I\'ve reviewed the specs and have some suggestions for improvement.', isUser: false, timestamp: '3:20 PM' }
      ]
    },
    {
      id: 4,
      title: 'Brainstorming',
      time: 'Last week',
      messages: [
        { id: 1, content: 'Let\'s brainstorm some feature ideas', isUser: true, timestamp: '11:00 AM' },
        { id: 2, content: 'How about adding message reactions and threading?', isUser: false, timestamp: '11:05 AM' }
      ]
    }
  ],
  currentChatId: null,
  addChat: (chat) => {
    const newChat = {
      ...chat,
      id: Date.now(),
      messages: []
    }
    set((state) => ({
      recentChats: [newChat, ...state.recentChats],
      currentChatId: newChat.id
    }))
    return newChat.id
  },
  removeChat: (id) => set((state) => ({
    recentChats: state.recentChats.filter(chat => chat.id !== id)
  })),
  setCurrentChat: (id) => set({ currentChatId: id }),
  addMessage: (chatId, message) => set((state) => ({
    recentChats: state.recentChats.map(chat => 
      chat.id === chatId 
        ? { ...chat, messages: [...chat.messages, { ...message, id: Date.now() }] }
        : chat
    )
  }))
}),
{
  name: 'chat-storage',
}
));
