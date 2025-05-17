'use client'
import { useState, useEffect } from 'react'
import Sidebar from '../chat/components/Sidebar'
import { useDocumentStore } from '@/store/documentStore'

export default function LibraryPage() {
  const {
    projects,
    selectedProjectId,
    isProcessing,
    error,
    addProject,
    removeProject,
    selectProject,
    removeDocument,
    processFile,
    processImage,
    clearError
  } = useDocumentStore()
  
  const [newProjectName, setNewProjectName] = useState('')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [selectedUploadProject, setSelectedUploadProject] = useState('')
  const [uploadType, setUploadType] = useState<'file' | 'image'>('file')

  const handleAddProject = () => {
    if (newProjectName.trim()) {
      addProject(newProjectName)
      setNewProjectName('')
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && selectedUploadProject) {
      try {
        // Process each file
        for (const file of Array.from(e.target.files)) {
          if (uploadType === 'image' && !file.type.startsWith('image/')) {
            alert('Please select image files only for image upload');
            continue;
          }
          
          // Process the file through the RAG system
          if (uploadType === 'image') {
            await processImage(selectedUploadProject, file);
          } else {
            await processFile(selectedUploadProject, file);
          }
        }
        
        // Close the modal when done
        setShowUploadModal(false);
      } catch (err) {
        console.error('Upload error:', err);
      }
    }
  }
  
  // Clear any errors when component unmounts
  useEffect(() => {
    return () => {
      clearError();
    };
  }, [clearError]);

  const selectedProject = projects.find(p => p.id === selectedProjectId)
  
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold mb-6">Document Library</h1>
          
          <div className="bg-white p-6 rounded-lg shadow mb-6">
            <h2 className="text-lg font-semibold mb-4">Projects</h2>
            <div className="flex mb-4">
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="New project name"
                className="flex-1 p-2 border rounded-l-lg"
              />
              <button
                onClick={handleAddProject}
                className="bg-blue-500 text-white px-4 rounded-r-lg hover:bg-blue-600"
              >
                Add
              </button>
            </div>
            
            <div className="space-y-2">
              {projects.map(project => (
                <div 
                  key={project.id}
                  className={`flex justify-between items-center p-3 rounded-lg cursor-pointer ${
                    selectedProjectId === project.id ? 'bg-blue-100' : 'hover:bg-gray-100'
                  }`}
                  onClick={() => selectProject(project.id)}
                >
                  <span className="font-medium">{project.name}</span>
                  <div className="flex space-x-2">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedUploadProject(project.id)
                        setShowUploadModal(true)
                      }}
                      className="text-sm bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
                    >
                      Upload
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        removeProject(project.id)
                      }}
                      className="text-sm bg-red-100 hover:bg-red-200 px-2 py-1 rounded text-red-600"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedProject && (
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Documents in {selectedProject.name}</h2>
              {selectedProject.documents.length === 0 ? (
                <p className="text-gray-500">No documents in this project</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {selectedProject.documents.map(doc => (
                        <tr key={doc.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.name}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.type}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.size}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.uploadedAt}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <button 
                              onClick={() => removeDocument(selectedProject.id, doc.id)}
                              className="text-red-500 hover:text-red-700"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {showUploadModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
                <h3 className="text-lg font-semibold mb-4">Upload to {projects.find(p => p.id === selectedUploadProject)?.name}</h3>
                <label className="flex flex-col items-center px-4 py-6 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 cursor-pointer hover:bg-gray-100">
                  <input 
                    type="file" 
                    className="hidden" 
                    multiple 
                    onChange={handleUpload}
                  />
                  <div className="flex flex-col items-center">
                    <svg className="w-8 h-8 mb-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                    </svg>
                    <span className="text-sm text-gray-500">
                      {isProcessing ? 'Processing...' : 'Select files to upload'}
                    </span>
                  </div>
                </label>
                <div className="mt-4 flex justify-end">
                  <button 
                    onClick={() => setShowUploadModal(false)}
                    className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
