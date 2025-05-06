import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

// API endpoints
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
const API = {
  GET_CONVERSATIONS: `${API_URL}/api/chat/conversations`,
  GET_CONVERSATION: `${API_URL}/api/chat/conversation`,
  CREATE_CONVERSATION: `${API_URL}/api/chat/conversation`,
  SEND_MESSAGE: `${API_URL}/api/chat/message`,
  DELETE_CONVERSATION: `${API_URL}/api/chat/conversation`
};

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

export interface Conversation {
  _id: string;
  title: string;
  user_id: string;
  messages: Message[];
  knowledge_base_id?: string;
  created_at: string;
  updated_at: string;
}

interface ChatStore {
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  error: string | null;
  
  // API actions
  fetchConversations: (userId?: string) => Promise<void>;
  fetchConversation: (id: string) => Promise<Conversation | null>;
  createConversation: (title?: string) => Promise<string | null>;
  sendMessage: (message: string, conversationId?: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  
  // Local actions
  setCurrentConversation: (id: string | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,
      error: null,
      
      fetchConversations: async (userId = 'default_user') => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.get(`${API.GET_CONVERSATIONS}?user_id=${userId}`);
          set({ conversations: response.data, isLoading: false });
        } catch (error) {
          console.error('Error fetching conversations:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to fetch conversations', 
            isLoading: false 
          });
        }
      },
      
      fetchConversation: async (id) => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.get(`${API.GET_CONVERSATION}/${id}`);
          
          // Update the conversation in the store
          set((state) => ({
            conversations: state.conversations.map(conv => 
              conv._id === id ? response.data : conv
            ),
            isLoading: false
          }));
          
          return response.data;
        } catch (error) {
          console.error('Error fetching conversation:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to fetch conversation', 
            isLoading: false 
          });
          return null;
        }
      },
      
      createConversation: async (title = 'New Conversation') => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post(API.CREATE_CONVERSATION, {
            title,
            user_id: 'default_user' // In a real app, get from authentication
          });
          
          // Add the new conversation to the store
          set((state) => ({
            conversations: [response.data, ...state.conversations],
            currentConversationId: response.data._id,
            isLoading: false
          }));
          
          return response.data._id;
        } catch (error) {
          console.error('Error creating conversation:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to create conversation', 
            isLoading: false 
          });
          return null;
        }
      },
      
      sendMessage: async (message, conversationId) => {
        const currentId = conversationId || get().currentConversationId;
        
        if (!message.trim()) {
          set({ error: 'Message cannot be empty' });
          return;
        }
        
        set({ isLoading: true, error: null });
        
        try {
          // Optimistically update UI
          const tempId = Date.now().toString();
          
          // If we have an existing conversation
          if (currentId) {
            set((state) => ({
              conversations: state.conversations.map(conv => 
                conv._id === currentId 
                  ? { 
                      ...conv,
                      messages: [...conv.messages, { role: 'user', content: message }],
                      updated_at: new Date().toISOString()
                    }
                  : conv
              ),
            }));
          } else {
            // Create a temporary conversation locally until we get response
            const tempConversation: Conversation = {
              _id: tempId,
              title: message.substring(0, 30) + (message.length > 30 ? '...' : ''),
              user_id: 'default_user',
              messages: [{ role: 'user', content: message }],
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            };
            
            set((state) => ({
              conversations: [tempConversation, ...state.conversations],
              currentConversationId: tempId
            }));
          }
          
          // Send to API
          const response = await axios.post(API.SEND_MESSAGE, {
            conversation_id: currentId,
            message: message,
            user_id: 'default_user' // In a real app, get from authentication
          });
          
          // Update with actual response
          if (currentId) {
            // Existing conversation - add assistant response
            set((state) => ({
              conversations: state.conversations.map(conv => 
                conv._id === currentId 
                  ? { 
                      ...conv,
                      messages: [...conv.messages, { 
                        role: 'assistant', 
                        content: response.data.message 
                      }],
                      updated_at: response.data.updated_at
                    }
                  : conv
              ),
              isLoading: false
            }));
          } else {
            // New conversation - update from temporary ID to real ID
            const realId = response.data.conversation_id;
            
            set((state) => ({
              conversations: state.conversations.map(conv => 
                conv._id === tempId 
                  ? { 
                      ...conv,
                      _id: realId,
                      messages: [...conv.messages, { 
                        role: 'assistant', 
                        content: response.data.message 
                      }],
                      updated_at: response.data.updated_at
                    }
                  : conv
              ),
              currentConversationId: realId,
              isLoading: false
            }));
          }
        } catch (error) {
          console.error('Error sending message:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to send message', 
            isLoading: false 
          });
        }
      },
      
      deleteConversation: async (id) => {
        set({ isLoading: true, error: null });
        try {
          await axios.delete(`${API.DELETE_CONVERSATION}/${id}`);
          
          // Remove the conversation from the store
          set((state) => ({
            conversations: state.conversations.filter(conv => conv._id !== id),
            currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
            isLoading: false
          }));
        } catch (error) {
          console.error('Error deleting conversation:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to delete conversation', 
            isLoading: false 
          });
        }
      },
      
      setCurrentConversation: (id) => set({ currentConversationId: id }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null })
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId
      })
    }
  )
);
