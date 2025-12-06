```markdown
# OCR Amount Extraction Pipeline (Google Gemini)

A 4-step OCR pipeline that extracts and classifies amounts from documents using Google Gemini 2.0 Flash.

## Architecture

- **Frontend**: HTML + Vanilla JS
- **Backend**: Node.js (orchestration) + Python (OCR processing)
- **OCR**: Tesseract
- **LLM**: Google Gemini 2.0 Flash (via REST API)

## Installation

### 1. Install Tesseract OCR

**Mac:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 2. Install Node.js Dependencies

```bash
cd backend/node
npm install
```

### 3. Install Python Dependencies

```bash
cd backend/python
pip install -r requirements.txt
```

### 4. Set Up Environment

Create `backend/python/.env`:
```
GEMINI_API_KEY=your_actual_api_key_here
```

Get your API key from: https://aistudio.google.com/app/apikey

## Running the Application

### Terminal 1 - Python Service
```bash
cd backend/python
python ocr_processor.py
```
(Runs on port 5000)

### Terminal 2 - Node.js Server
```bash
cd backend/node
npm start
```
(Runs on port 3000)

### Terminal 3 - Frontend
```bash
cd frontend
python -m http.server 8000
# OR
npx serve
```
(Open http://localhost:8000)

## Pipeline Steps

1. **OCR Layer**: Tesseract extracts text + confidence scores
2. **Normalization**: Fix OCR errors (l→1, O→0) with rules + Gemini verification
3. **Classification**: Gemini classifies amounts using context
4. **Assembly**: Code assembles final JSON with provenance

## Gemini API Integration

The application uses Google Gemini 2.0 Flash Experimental via REST API:
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent`
- Method: POST with API key in header
- Used for: Token normalization verification & amount classification

## Output Format

```json
{
  "currency": "INR",
  "amounts": [
    {
      "type": "total_bill",
      "value": 1200,
      "source": "text: 'Total: INR 1200'"
    }
  ],
  "status": "ok"
}
```

## Features

✅ No LLM hallucinations: Gemini only verifies, never generates amounts  
✅ Provenance tracking: Every amount traces back to source text  
✅ Guardrails: Returns proper error if no amounts found  
✅ Fallback: Works without LLM using rule-based classification  

## Troubleshooting

- **Tesseract not found**: Make sure it's installed and in PATH
- **API Key error**: Check your `.env` file has valid `GEMINI_API_KEY`
- **Port conflicts**: Ensure ports 3000, 5000, and 8000 are available
```