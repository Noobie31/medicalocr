const express = require('express');
const multer = require('multer');
const cors = require('cors');
const axios = require('axios');
const FormData = require('form-data');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;
const PYTHON_SERVICE_URL = 'http://localhost:5000/process';

// Create uploads directory if it doesn't exist
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = `${Date.now()}-${file.originalname}`;
        cb(null, uniqueName);
    }
});

const upload = multer({ 
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', message: 'Node.js backend is running' });
});

// Main upload endpoint
app.post('/upload', upload.single('image'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No image uploaded' });
        }

        console.log('📥 Image received:', req.file.originalname);
        console.log('📂 Saved to:', req.file.path);

        // Send to Python OCR service
        console.log('🐍 Sending to Python OCR service...');
        
        const formData = new FormData();
        formData.append('image', fs.createReadStream(req.file.path), {
            filename: req.file.originalname,
            contentType: req.file.mimetype
        });

        const pythonResponse = await axios.post(PYTHON_SERVICE_URL, formData, {
            headers: {
                ...formData.getHeaders()
            },
            maxBodyLength: Infinity,
            maxContentLength: Infinity
        });

        console.log('✅ Python processing complete');

        // Clean up uploaded file
        fs.unlinkSync(req.file.path);

        // Return final assembled JSON
        res.json(pythonResponse.data);

    } catch (error) {
        console.error('❌ Error:', error.message);
        
        // Clean up file if it exists
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }

        res.status(500).json({ 
            error: 'Processing failed',
            details: error.response?.data || error.message,
            status: 'error'
        });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 Node.js server running on http://localhost:${PORT}`);
    console.log(`🔗 Make sure Python service is running on port 5000`);
});