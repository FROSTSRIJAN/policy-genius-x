# PolicyGenius X - Insurance Assistant

🚀 **GenAI-Powered Insurance Clause & Claim Evaluator for HackRx 6.0**

## Features

- ✅ **HackRx 6.0 Compliant API** - `/hackrx/run` endpoint
- 🤖 **AI-Powered Analysis** - Google Gemini integration
- 🔍 **Vector Search** - FAISS-based document similarity
- 🌐 **Multilingual Support** - English, Hindi, Marathi, Tamil
- 🎤 **Text-to-Speech** - gTTS audio responses
- 🎨 **Modern UI** - Glassmorphism design
- 🔒 **Secure Authentication** - Bearer token protection
- ⚡ **Fast Performance** - Sub-30 second response times

## Quick Deploy

### 1. GitHub Setup
```bash
git clone https://github.com/YourUsername/PolicyGenius-X.git
cd PolicyGenius-X
```

### 2. Vercel Deployment
1. Go to [vercel.com](https://vercel.com)
2. Import this repository
3. Set environment variable: `GEMINI_API_KEY`
4. Deploy!

Your API will be available at: `https://your-app.vercel.app/hackrx/run`

## API Usage

### Endpoint
```
POST /hackrx/run
Authorization: Bearer your-token
Content-Type: application/json
```

### Request Format
```json
{
  "documents": "https://example.com/policy.pdf",
  "questions": [
    "Does this policy cover hospitalization?",
    "What are the exclusions?"
  ]
}
```

### Response Format
```json
{
  "answers": [
    "Yes, hospitalization is covered...",
    "Exclusions include..."
  ],
  "processing_time": 2.45,
  "source_chunks": [...]
}
```

## Local Development

### Setup
```bash
pip install -r requirements.txt
```

### Environment Variables
```bash
GEMINI_API_KEY=your_gemini_api_key
PORT=8000
```

### Run API Server
```bash
python main.py
```

### Run Streamlit UI
```bash
streamlit run app.py --server.port 8507
```

## Architecture

- **Backend**: FastAPI with async processing
- **AI**: Google Gemini for intelligent responses  
- **Search**: FAISS vector similarity search
- **Frontend**: Streamlit with multilingual support
- **Deployment**: Vercel serverless functions

## Competition Compliance

✅ **HackRx 6.0 Requirements Met:**
- `/hackrx/run` POST endpoint
- Bearer token authentication
- JSON request/response format
- Sub-30 second processing
- HTTPS deployment ready
- Proper error handling

## Team

**PolicyGenius X** - Advanced Insurance Assistant
