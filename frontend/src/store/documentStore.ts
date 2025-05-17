import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

// RAG API endpoints
const RAG_API_URL = process.env.NEXT_PUBLIC_RAG_API_URL || 'http://localhost:8085';
const RAG_API = {
  PROCESS_FILE: `${RAG_API_URL}/process_file`,
  PROCESS_IMAGE: `${RAG_API_URL}/process_image`,
  SEARCH: `${RAG_API_URL}/search`,
  HYBRID_SEARCH: `${RAG_API_URL}/hybrid_search`,
};

interface Document {
  id: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
  docId?: string; // ID in the RAG system
  kbId?: string;  // Knowledge base ID
}

interface Project {
  id: string;
  name: string;
  documents: Document[];
}

interface DocumentStore {
  projects: Project[];
  selectedProjectId: string | null;
  isProcessing: boolean;
  error: string | null;
  
  // Project management
  addProject: (name: string) => void;
  removeProject: (id: string) => void;
  selectProject: (id: string) => void;
  
  // Document management
  addDocument: (projectId: string, document: Omit<Document, 'id'>) => void;
  removeDocument: (projectId: string, documentId: string) => void;
  
  // RAG operations
  processFile: (projectId: string, file: File) => Promise<string | null>;
  processImage: (projectId: string, file: File) => Promise<string | null>;
  searchDocuments: (query: string, kbId: string, topK?: number) => Promise<any[]>;
  
  // UI state
  setProcessing: (isProcessing: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useDocumentStore = create<DocumentStore>()(
  persist(
    (set, get) => ({
      projects: [
        {
          id: '1',
          name: 'Marketing Campaign',
          documents: [
            { id: '1', name: 'Strategy.pdf', size: '2.4 MB', type: 'PDF', uploadedAt: '2 days ago' },
            { id: '2', name: 'Budget.xlsx', size: '1.1 MB', type: 'Excel', uploadedAt: '1 day ago' }
          ]
        },
        {
          id: '2', 
          name: 'Product Development',
          documents: [
            { id: '1', name: 'Specs.docx', size: '3.2 MB', type: 'Word', uploadedAt: '1 week ago' }
          ]
        }
      ],
      selectedProjectId: null,
      isProcessing: false,
      error: null,
      
      // Project management
      addProject: (name) => set((state) => ({
        projects: [...state.projects, {
          id: Date.now().toString(),
          name,
          documents: []
        }]
      })),
      removeProject: (id) => set((state) => ({
        projects: state.projects.filter(project => project.id !== id)
      })),
      selectProject: (id) => {
        // Save the selected project ID to localStorage for use by the chat store
        localStorage.setItem('selectedProjectId', id);
        set({ selectedProjectId: id });
      },
      
      // Document management
      addDocument: (projectId, document) => set((state) => ({
        projects: state.projects.map(project => 
          project.id === projectId
            ? { ...project, documents: [...project.documents, { ...document, id: Date.now().toString() }] }
            : project
        )
      })),
      removeDocument: (projectId, documentId) => set((state) => ({
        projects: state.projects.map(project =>
          project.id === projectId
            ? { ...project, documents: project.documents.filter(doc => doc.id !== documentId) }
            : project
        )
      })),
      
      // RAG operations
      processFile: async (projectId, file) => {
        set({ isProcessing: true, error: null });
        try {
          // Create form data for the file upload
          const formData = new FormData();
          formData.append('file', file);
          formData.append('kb_id', projectId); // Using project ID as knowledge base ID
          
          // Upload to RAG API
          const response = await axios.post(RAG_API.PROCESS_FILE, formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          });
          
          // Add document to the project with RAG metadata
          const docSize = (file.size / 1024 / 1024).toFixed(2);
          const fileType = file.type.split('/')[1]?.toUpperCase() || 'Unknown';
          
          get().addDocument(projectId, {
            name: file.name,
            size: `${docSize} MB`,
            type: fileType,
            uploadedAt: new Date().toLocaleDateString(),
            docId: response.data.doc_id,
            kbId: projectId
          });
          
          set({ isProcessing: false });
          return response.data.doc_id;
        } catch (error) {
          console.error('Error processing file:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to process file', 
            isProcessing: false 
          });
          return null;
        }
      },
      
      processImage: async (projectId, file) => {
        set({ isProcessing: true, error: null });
        try {
          // Check if file is an image
          if (!file.type.startsWith('image/')) {
            throw new Error('File is not an image');
          }
          
          // Create form data for the image upload
          const formData = new FormData();
          formData.append('image', file);
          formData.append('kb_id', projectId); // Using project ID as knowledge base ID
          
          // Upload to RAG API
          const response = await axios.post(RAG_API.PROCESS_IMAGE, formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          });
          
          // Add image to the project with RAG metadata
          const docSize = (file.size / 1024 / 1024).toFixed(2);
          
          get().addDocument(projectId, {
            name: file.name,
            size: `${docSize} MB`,
            type: 'IMAGE',
            uploadedAt: new Date().toLocaleDateString(),
            docId: response.data.doc_id,
            kbId: projectId
          });
          
          set({ isProcessing: false });
          return response.data.doc_id;
        } catch (error) {
          console.error('Error processing image:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to process image', 
            isProcessing: false 
          });
          return null;
        }
      },
      
      searchDocuments: async (query, kbId, topK = 5) => {
        set({ isProcessing: true, error: null });
        try {
          // Search using the RAG API
          const response = await axios.post(RAG_API.HYBRID_SEARCH, {
            query,
            kb_id: kbId,
            top_k: topK
          });
          
          set({ isProcessing: false });
          return response.data.results || [];
        } catch (error) {
          console.error('Error searching documents:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to search documents', 
            isProcessing: false 
          });
          return [];
        }
      },
      
      // UI state
      setProcessing: (isProcessing) => set({ isProcessing }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null })
    }),
    {
      name: 'document-storage',
    }
  )
);
