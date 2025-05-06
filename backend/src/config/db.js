const mongoose = require('mongoose');

// MongoDB connection URL using environment variables or default values
const mongoUsername = process.env.MONGO_USERNAME || 'ask2slide_admin';
const mongoPassword = process.env.MONGO_PASSWORD || 's3cur3P@ssw0rd';
const mongoHost = process.env.MONGO_HOST || 'localhost';
const mongoPort = process.env.MONGO_PORT || '27018';
const mongoDatabase = process.env.MONGO_DATABASE || 'ask2slide';

// Debug connection info
console.log(`MongoDB Connection Info:
  - Username: ${mongoUsername}
  - Host: ${mongoHost}
  - Port: ${mongoPort}
  - Database: ${mongoDatabase}
`);

// Encode the password to handle special characters
const encodedPassword = encodeURIComponent(mongoPassword);
const mongoURI = `mongodb://${mongoUsername}:${encodedPassword}@${mongoHost}:${mongoPort}/${mongoDatabase}?authSource=admin`;

// Connect to MongoDB
const connectDB = async () => {
  try {
    await mongoose.connect(mongoURI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
    console.log('MongoDB Connected Successfully');
  } catch (error) {
    console.error('MongoDB Connection Error:', error.message);
    process.exit(1); // Exit with failure
  }
};

module.exports = connectDB;
