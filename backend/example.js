/**
 * Example script demonstrating how to interact with MongoDB and MinIO
 * 
 * This is a reference implementation and not meant to be used in production.
 * It shows how to:
 * 1. Connect to MongoDB
 * 2. Connect to MinIO
 * 3. Create a knowledge base in MongoDB
 * 4. Upload a file to MinIO
 * 5. Update the knowledge base with the file information
 */

// Required dependencies:
// npm install mongodb minio uuid

const { MongoClient, ObjectId } = require('mongodb');
const Minio = require('minio');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');

// MongoDB configuration
const mongoUrl = 'mongodb://ask2slide_admin:s3cur3P@ssw0rd@localhost:27017/';
const dbName = 'ask2slide';
const collectionName = 'knowledge_bases';

// MinIO configuration
const minioClient = new Minio.Client({
  endPoint: 'localhost',
  port: 9000,
  useSSL: false,
  accessKey: 'ask2slide_minio',
  secretKey: 'm1n10P@ssw0rd'
});
const minioBucket = 'ai-chat';

// Example function to create a knowledge base
async function createKnowledgeBase(username, name) {
  const client = new MongoClient(mongoUrl);
  
  try {
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    
    const knowledgeBaseId = `${username}_${uuidv4()}`;
    
    const knowledgeBase = {
      knowledge_base_id: knowledgeBaseId,
      knowledge_base_name: name,
      username: username,
      files: [],
      used_chat: [],
      created_at: new Date(),
      last_modify_at: new Date(),
      is_delete: false
    };
    
    const result = await collection.insertOne(knowledgeBase);
    console.log(`Created knowledge base with ID: ${result.insertedId}`);
    
    return {
      _id: result.insertedId,
      knowledge_base_id: knowledgeBaseId
    };
  } finally {
    await client.close();
  }
}

// Example function to upload a file to MinIO and update MongoDB
async function uploadFile(knowledgeBaseId, filePath) {
  const client = new MongoClient(mongoUrl);
  
  try {
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    
    // Find the knowledge base
    const knowledgeBase = await collection.findOne({ knowledge_base_id: knowledgeBaseId });
    if (!knowledgeBase) {
      throw new Error(`Knowledge base with ID ${knowledgeBaseId} not found`);
    }
    
    const username = knowledgeBase.username;
    const originalFilename = path.basename(filePath);
    const fileId = `${username}_${uuidv4()}`;
    const fileExtension = path.extname(originalFilename);
    const minioFilename = `${username}_${originalFilename.replace(fileExtension, '')}_${knowledgeBase._id}${fileExtension}`;
    
    // Check if bucket exists, create if it doesn't
    const bucketExists = await minioClient.bucketExists(minioBucket);
    if (!bucketExists) {
      await minioClient.makeBucket(minioBucket);
      console.log(`Created bucket: ${minioBucket}`);
    }
    
    // Upload file to MinIO
    await minioClient.fPutObject(minioBucket, minioFilename, filePath);
    console.log(`Uploaded ${originalFilename} to MinIO as ${minioFilename}`);
    
    // Generate a presigned URL (valid for 7 days)
    const presignedUrl = await minioClient.presignedGetObject(minioBucket, minioFilename, 7 * 24 * 60 * 60);
    
    // Update the knowledge base with the file information
    const fileInfo = {
      file_id: fileId,
      filename: originalFilename,
      minio_filename: minioFilename,
      minio_url: presignedUrl,
      created_at: new Date()
    };
    
    await collection.updateOne(
      { _id: knowledgeBase._id },
      { 
        $push: { files: fileInfo },
        $set: { last_modify_at: new Date() }
      }
    );
    
    console.log(`Updated knowledge base with file information`);
    return fileInfo;
  } finally {
    await client.close();
  }
}

// Example function to retrieve all knowledge bases for a user
async function getKnowledgeBases(username) {
  const client = new MongoClient(mongoUrl);
  
  try {
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    
    const knowledgeBases = await collection.find({ 
      username: username,
      is_delete: false
    }).toArray();
    
    return knowledgeBases;
  } finally {
    await client.close();
  }
}

// Example function to delete a knowledge base (soft delete)
async function deleteKnowledgeBase(knowledgeBaseId) {
  const client = new MongoClient(mongoUrl);
  
  try {
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    
    await collection.updateOne(
      { knowledge_base_id: knowledgeBaseId },
      { 
        $set: { 
          is_delete: true,
          last_modify_at: new Date()
        }
      }
    );
    
    console.log(`Soft deleted knowledge base with ID: ${knowledgeBaseId}`);
  } finally {
    await client.close();
  }
}

// Example usage (commented out)
/*
async function main() {
  try {
    // Create a knowledge base
    const kb = await createKnowledgeBase('thz', 'temp_base_thz');
    
    // Upload a file
    const fileInfo = await uploadFile(kb.knowledge_base_id, '/path/to/your/file.pdf');
    
    // Get all knowledge bases for a user
    const knowledgeBases = await getKnowledgeBases('thz');
    console.log(knowledgeBases);
    
    // Delete a knowledge base
    await deleteKnowledgeBase(kb.knowledge_base_id);
  } catch (error) {
    console.error('Error:', error);
  }
}

main();
*/

module.exports = {
  createKnowledgeBase,
  uploadFile,
  getKnowledgeBases,
  deleteKnowledgeBase
};
