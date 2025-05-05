import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Document {
  id: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
}

interface Project {
  id: string;
  name: string;
  documents: Document[];
}

interface DocumentStore {
  projects: Project[];
  selectedProjectId: string | null;
  addProject: (name: string) => void;
  removeProject: (id: string) => void;
  selectProject: (id: string) => void;
  addDocument: (projectId: string, document: Omit<Document, 'id'>) => void;
  removeDocument: (projectId: string, documentId: string) => void;
}

export const useDocumentStore = create<DocumentStore>()(
  persist(
    (set) => ({
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
      selectProject: (id) => set({ selectedProjectId: id }),
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
      }))
    }),
    {
      name: 'document-storage',
    }
  )
);
