const express = require('express');
const { MongoClient } = require('mongodb');
const helmet = require('helmet');
const app = express();
const port = 3000;

// MongoDB connection URI (update with your MongoDB URI)
const uri = 'mongodb://localhost:27017';
const client = new MongoClient(uri);
const dbName = 'template_db';
let db;

// Connect to MongoDB before the server starts
client.connect()
  .then(() => {
    db = client.db(dbName);
    console.log('MongoDB connected');
  })
  .catch((err) => {
    console.error('MongoDB connection error:', err);
  });

app.use(helmet());

// Custom Content Security Policy (CSP)
app.use(helmet.contentSecurityPolicy({
    directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "localhost:3000"],
        imgSrc: ["'self'", "localhost:3000"],
        connectSrc: ["'self'", "localhost:3000"],
        styleSrc: ["'self'", "https://fonts.googleapis.com"],
        fontSrc: ["'self'", "https://fonts.gstatic.com"],
    }
}));

app.use(express.json());

// Route for saving template data
app.post('/api/templates', async (req, res) => {
    const { templateName, keyValuePairs } = req.body;

    // Validate input
    if (!templateName || !keyValuePairs || keyValuePairs.length === 0) {
        return res.status(400).send('Template name and key-value pairs are required.');
    }

    try {
        const templatesCollection = db.collection('templates');

        // Insert the new template data into the database
        const result = await templatesCollection.insertOne({
            templateName,
            keyValuePairs,
            createdAt: new Date()
        });

        res.status(201).send({ message: 'Template saved successfully', id: result.insertedId });
    } catch (error) {
        console.error('Error saving template:', error);
        res.status(500).send('Error saving template');
    }
});

// Start the server
app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});