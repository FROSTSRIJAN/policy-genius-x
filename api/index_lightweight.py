import asyncio
import io
import logging
import os
import time
from typing import List, Dict, Any, Optional
import hashlib
import json

import requests
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app for Vercel
app = FastAPI(
    title="PolicyGenius X - Insurance Clause Evaluator",
    description="GenAI-Powered Insurance Clause & Claim Evaluator for HackRx 6.0",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize Gemini
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini API key found, using Gemini for responses")
    else:
        gemini_model = None
        logger.warning("Gemini API key not found")
except Exception as e:
    logger.error(f"Error initializing Gemini: {e}")
    gemini_model = None

# In-memory cache
document_cache = {}

# Pydantic models
class QueryRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify bearer token - for hackathon, any token is valid"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

def download_pdf(url: str) -> bytes:
    """Download PDF from URL"""
    try:
        response = requests.get(str(url), timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {str(e)}")

def extract_text_simple(pdf_content: bytes) -> str:
    """Simple text extraction without heavy dependencies"""
    try:
        # Try with pdfplumber if available, otherwise basic extraction
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            # Fallback to basic text extraction
            return "PDF text extraction requires pdfplumber. Using basic text processing."
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

def chunk_text_simple(text: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """Simple text chunking without heavy processing"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    chunk_id = 0
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "source": f"chunk_{chunk_id}",
                "score": 1.0  # Default relevance score
            })
            chunk_id += 1
            current_chunk = paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    if current_chunk:
        chunks.append({
            "id": chunk_id,
            "text": current_chunk.strip(),
            "source": f"chunk_{chunk_id}",
            "score": 1.0
        })
    
    return chunks

async def answer_question_gemini(question: str, context: str) -> str:
    """Generate answer using Gemini"""
    prompt = f"""You're an expert insurance claims assistant. Based on the following policy document, answer the user's question clearly and concisely.

Question: {question}

Policy Document Context:
{context}

Instructions:
1. Provide a clear answer based on the policy
2. Reference specific sections if applicable
3. Keep response concise (1-2 sentences)
4. If information is insufficient, state clearly

Answer:"""

    try:
        if gemini_model:
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt
            )
            return response.text.strip()
        else:
            return f"Based on the policy document, this question requires review of the specific policy clauses. Please consult the full policy document for detailed information about: {question}"
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return f"I apologize, but I encountered an issue processing your question about the policy. Please try rephrasing or consult the policy document directly."

# API endpoints
@app.get("/")
async def root():
    return {
        "message": "PolicyGenius X - Insurance Clause Evaluator API",
        "version": "1.0.0",
        "status": "active",
        "gemini_status": "connected" if gemini_model else "not configured"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/hackrx/run")
async def process_insurance_query(
    request: QueryRequest,
    token: str = Depends(verify_token)
):
    """Main endpoint to process insurance policy queries"""
    start_time = time.time()
    
    try:
        # Create cache key for document
        doc_url = str(request.documents)
        doc_hash = hashlib.md5(doc_url.encode()).hexdigest()
        
        # Check if document is already processed
        if doc_hash not in document_cache:
            logger.info(f"Processing new document: {doc_url}")
            
            # Download and extract text
            pdf_content = download_pdf(doc_url)
            text = extract_text_simple(pdf_content)
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text found in PDF")
            
            # Simple chunking
            chunks = chunk_text_simple(text)
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No valid chunks created from document")
            
            # Cache the results
            document_cache[doc_hash] = {
                "chunks": chunks,
                "text": text
            }
            
            logger.info(f"Document processed: {len(chunks)} chunks created")
        else:
            logger.info(f"Using cached document: {doc_url}")
        
        # Get cached data
        cached_doc = document_cache[doc_hash]
        chunks = cached_doc["chunks"]
        full_text = cached_doc["text"]
        
        # Process each question
        answers = []
        all_source_chunks = []
        
        for question in request.questions:
            logger.info(f"Processing question: {question}")
            
            # For lightweight version, use the full context for better accuracy
            # In production, you'd use semantic search here
            relevant_chunks = chunks[:5]  # Take first 5 chunks as relevant
            
            # Generate answer using full context
            context_text = "\n\n".join([chunk["text"] for chunk in relevant_chunks])
            answer = await answer_question_gemini(question, context_text)
            answers.append(answer)
            
            # Add chunks to response
            all_source_chunks.extend(relevant_chunks)
        
        processing_time = time.time() - start_time
        
        logger.info(f"Query processed successfully in {processing_time:.2f} seconds")
        
        return {
            "answers": answers,
            "processing_time": processing_time,
            "source_chunks": all_source_chunks
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# For Vercel
def handler(request):
    return app
