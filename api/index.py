import asyncio
import io
import logging
import os
import time
from typing import List, Dict, Any, Optional
import hashlib
import json
from dotenv import load_dotenv

import faiss
import numpy as np
import pdfplumber
import requests
from fastapi import FastAPI, HTTPException, Depends, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

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

# Initialize models and services
try:
    # Use Gemini for chat completion
    gemini_api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD6flvCwlzWqO_gJVktXLugK13IhIbOTME")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini API key found, using Gemini for responses")
    else:
        gemini_model = None
        logger.warning("Gemini API key not found")
    
    # Initialize embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
except Exception as e:
    logger.error(f"Error initializing models: {e}")
    gemini_model = None
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# In-memory cache for document processing
document_cache = {}
vector_store_cache = {}

# Pydantic models
class QueryRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class SimpleQueryRequest(BaseModel):
    query: str
    document_url: Optional[str] = "https://raw.githubusercontent.com/example/insurance-docs/main/policy.pdf"

# Authentication function
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify bearer token - for hackathon, any token is valid"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Utility functions
def download_pdf(url: str) -> bytes:
    """Download PDF from URL"""
    try:
        response = requests.get(str(url), timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {str(e)}")

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """Split text into semantic chunks"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    chunk_id = 0
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "source": f"chunk_{chunk_id}"
            })
            chunk_id += 1
            
            words = current_chunk.split()
            overlap_text = " ".join(words[-overlap//10:]) if len(words) > overlap//10 else ""
            current_chunk = overlap_text + " " + paragraph if overlap_text else paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    if current_chunk:
        chunks.append({
            "id": chunk_id,
            "text": current_chunk.strip(),
            "source": f"chunk_{chunk_id}"
        })
    
    return chunks

async def get_embeddings(texts: List[str]) -> np.ndarray:
    """Generate embeddings for texts"""
    try:
        embeddings = embedding_model.encode(texts)
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")

def create_vector_store(chunks: List[Dict[str, Any]], embeddings: np.ndarray):
    """Create FAISS vector store"""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    return index, chunks

async def retrieve_relevant_chunks(query: str, index, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve most relevant chunks for a query"""
    query_embedding = await get_embeddings([query])
    faiss.normalize_L2(query_embedding)
    
    scores, indices = index.search(query_embedding, top_k)
    
    relevant_chunks = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:
            chunk = chunks[idx].copy()
            chunk["similarity_score"] = float(scores[0][i])
            relevant_chunks.append(chunk)
    
    return relevant_chunks

async def answer_question(question: str, relevant_chunks: List[Dict[str, Any]]) -> str:
    """Generate answer using Gemini LLM or intelligent fallback"""
    context = "\n\n".join([f"Clause {chunk['id']}: {chunk['text']}" for chunk in relevant_chunks])
    
    prompt = f"""You're an expert insurance claims assistant. Based on the following policy clauses, answer the user's question in clear terms and justify your answer using the source clauses.

Question: {question}

Relevant Policy Clauses:
{context}

Instructions:
1. Provide a clear yes/no answer if applicable
2. Reference specific clause numbers/sections
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
            return f"Based on the policy clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}, this information requires review of the specific policy sections."
    
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return f"Based on the available policy clauses, please review the relevant sections for detailed information."

# API endpoints
@app.get("/")
async def root():
    return {
        "message": "PolicyGenius X - Insurance Clause Evaluator API",
        "version": "1.0.0",
        "status": "healthy",
        "ai_model": "Gemini 1.5 Flash" if gemini_model else "Fallback Mode"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/hackrx/run")
async def process_insurance_query(
    request: QueryRequest,
    token: str = Depends(verify_token)
):
    """Main HackRx endpoint to process insurance policy queries"""
    start_time = time.time()
    
    try:
        doc_url = str(request.documents)
        doc_hash = hashlib.md5(doc_url.encode()).hexdigest()
        
        # Process document if not cached
        if doc_hash not in document_cache:
            logger.info(f"Processing new document: {doc_url}")
            
            pdf_content = download_pdf(doc_url)
            text = extract_text_from_pdf(pdf_content)
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text found in PDF")
            
            chunks = chunk_text(text)
            if not chunks:
                raise HTTPException(status_code=400, detail="No valid chunks created from document")
            
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await get_embeddings(chunk_texts)
            
            index, processed_chunks = create_vector_store(chunks, embeddings)
            
            document_cache[doc_hash] = {
                "chunks": processed_chunks,
                "text": text
            }
            vector_store_cache[doc_hash] = index
            
            logger.info(f"Document processed: {len(processed_chunks)} chunks created")
        
        # Get cached data
        cached_doc = document_cache[doc_hash]
        index = vector_store_cache[doc_hash]
        chunks = cached_doc["chunks"]
        
        # Process questions
        answers = []
        all_source_chunks = []
        
        for question in request.questions:
            logger.info(f"Processing question: {question}")
            
            relevant_chunks = await retrieve_relevant_chunks(question, index, chunks, top_k=5)
            
            if not relevant_chunks:
                answers.append("No relevant information found in the policy document for this question.")
                continue
            
            # Clean up chunk data
            for chunk in relevant_chunks:
                chunk["score"] = chunk.pop("similarity_score", 0.0)
                for key, value in chunk.items():
                    if hasattr(value, 'item'):
                        chunk[key] = value.item()
            
            answer = await answer_question(question, relevant_chunks)
            answers.append(answer)
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

@app.post("/query")
async def simple_query(request: Request):
    """Simple query endpoint for Streamlit frontend"""
    try:
        body = await request.json()
        user_query = body.get("query", "")
        
        if not user_query:
            return JSONResponse(content={"error": "No query provided"}, status_code=400)
        
        # Default insurance document for demo
        demo_doc_url = "https://raw.githubusercontent.com/example/docs/main/insurance-policy.pdf"
        
        # Simple demo response with AI processing
        if gemini_model:
            prompt = f"""You are an expert insurance assistant. Answer this question about insurance policies: {user_query}
            
            Provide a helpful, professional response about insurance coverage, claims, or policy terms."""
            
            try:
                response = await asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt
                )
                answer = response.text.strip()
            except Exception as e:
                answer = f"I can help you with insurance questions like '{user_query}'. Please provide a specific policy document for detailed analysis."
        else:
            answer = f"I can help you with insurance questions like '{user_query}'. Please provide a specific policy document for detailed analysis."
        
        return JSONResponse(content={
            "answer": answer,
            "query": user_query,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Error in simple query: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    return {
        "documents_cached": len(document_cache),
        "vector_stores_cached": len(vector_store_cache)
    }
