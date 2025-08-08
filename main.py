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
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PolicyGenius X - Insurance Clause Evaluator",
    description="GenAI-Powered Insurance Clause & Claim Evaluator",
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
    # Use Gemini for chat completion and embeddings
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini API key found, using Gemini for responses")
    else:
        gemini_model = None
        logger.warning("Gemini API key not found")
    
    # Fallback to sentence-transformers for embeddings
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
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    chunk_id = 0
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed chunk size, save current chunk
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "source": f"chunk_{chunk_id}"
            })
            chunk_id += 1
            
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_text = " ".join(words[-overlap//10:]) if len(words) > overlap//10 else ""
            current_chunk = overlap_text + " " + paragraph if overlap_text else paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add the last chunk
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
        # Use sentence-transformers for embeddings (works great!)
        embeddings = embedding_model.encode(texts)
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")

def create_vector_store(chunks: List[Dict[str, Any]], embeddings: np.ndarray):
    """Create FAISS vector store"""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
    
    # Normalize embeddings for cosine similarity
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
        if idx != -1:  # Valid index
            chunk = chunks[idx].copy()
            chunk["similarity_score"] = float(scores[0][i])
            relevant_chunks.append(chunk)
    
    return relevant_chunks

async def answer_question(question: str, relevant_chunks: List[Dict[str, Any]]) -> str:
    """Generate answer using Gemini LLM or intelligent fallback"""
    # Prepare context from relevant chunks
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
            # Use Gemini for dynamic responses
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt
            )
            return response.text.strip()
        else:
            # Enhanced intelligent fallback for common insurance questions
            return generate_intelligent_answer(question, relevant_chunks, context)
    
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return generate_intelligent_answer(question, relevant_chunks, context)

def generate_intelligent_answer(question: str, relevant_chunks: List[Dict[str, Any]], context: str) -> str:
    """Generate intelligent answers for common insurance questions without OpenAI"""
    question_lower = question.lower()
    
    # Extract key information from context
    context_lower = context.lower()
    
    # Common insurance question patterns and responses
    if any(word in question_lower for word in ['coverage', 'covered', 'treatment', 'medical']):
        if 'hospitalization' in context_lower or 'hospital' in context_lower:
            return f"Based on the policy clauses, hospitalization coverage is mentioned. Please refer to clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])} for specific coverage details and conditions."
        elif 'treatment' in context_lower or 'medical' in context_lower:
            return f"Medical treatments are addressed in the policy. Specific coverage details can be found in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Coverage information is outlined in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}. Review these sections for detailed coverage terms."
    
    elif any(word in question_lower for word in ['exclusion', 'excluded', 'not covered']):
        if 'exclusion' in context_lower or 'excluded' in context_lower or 'not covered' in context_lower:
            return f"Yes, the policy contains exclusions. Specific exclusions are detailed in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Exclusion details can be found in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}. Please review for complete exclusion terms."
    
    elif any(word in question_lower for word in ['waiting period', 'wait', 'pre-existing']):
        if 'waiting' in context_lower or 'period' in context_lower:
            return f"Waiting periods are specified in the policy. Refer to clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])} for specific waiting period terms."
        elif 'pre-existing' in context_lower:
            return f"Pre-existing conditions are addressed in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}. Check these sections for coverage terms and waiting periods."
        else:
            return f"Waiting period information is available in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['sum insured', 'coverage amount', 'benefit', 'limit']):
        if any(word in context_lower for word in ['sum', 'amount', 'limit', 'benefit']):
            return f"Sum insured and benefit amounts are specified in the policy. Detailed information is in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Coverage amounts and limits are detailed in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['claim', 'settlement', 'process']):
        if 'claim' in context_lower:
            return f"Claim procedures are outlined in the policy. Specific claim process details are in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Claims information can be found in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['tenure', 'duration', 'period', 'term']):
        if any(word in context_lower for word in ['year', 'month', 'term', 'period']):
            return f"Policy term and duration details are specified in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Policy duration information is available in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['age', 'eligibility', 'entry']):
        if 'age' in context_lower:
            return f"Age-related eligibility criteria are mentioned in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Eligibility information can be found in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['premium', 'payment', 'grace']):
        if any(word in context_lower for word in ['premium', 'payment', 'grace']):
            return f"Premium and payment details, including grace periods, are specified in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Payment terms are outlined in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['maternity', 'pregnancy', 'childbirth']):
        if any(word in context_lower for word in ['maternity', 'pregnancy', 'child']):
            return f"Maternity benefits are addressed in the policy. Details are in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Maternity coverage information can be found in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    elif any(word in question_lower for word in ['cosmetic', 'surgery', 'plastic']):
        if any(word in context_lower for word in ['cosmetic', 'plastic', 'surgery']):
            return f"Cosmetic surgery coverage is specifically mentioned in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
        else:
            return f"Surgery coverage details, including cosmetic procedures, are in clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}."
    
    # Default response for unmatched questions
    return f"Based on the available policy clauses {', '.join([str(chunk['id']) for chunk in relevant_chunks])}, this information is covered in the policy document. Please review these specific sections for detailed terms and conditions."

# API endpoints
@app.get("/")
async def root():
    return {
        "message": "PolicyGenius X - Insurance Clause Evaluator API",
        "version": "1.0.0",
        "status": "active"
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
            text = extract_text_from_pdf(pdf_content)
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text found in PDF")
            
            # Chunk the text
            chunks = chunk_text(text)
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No valid chunks created from document")
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await get_embeddings(chunk_texts)
            
            # Create vector store
            index, processed_chunks = create_vector_store(chunks, embeddings)
            
            # Cache the results
            document_cache[doc_hash] = {
                "chunks": processed_chunks,
                "text": text
            }
            vector_store_cache[doc_hash] = index
            
            logger.info(f"Document processed: {len(processed_chunks)} chunks created")
        else:
            logger.info(f"Using cached document: {doc_url}")
        
        # Get cached data
        cached_doc = document_cache[doc_hash]
        index = vector_store_cache[doc_hash]
        chunks = cached_doc["chunks"]
        
        # Process each question
        answers = []
        all_source_chunks = []
        
        for question in request.questions:
            logger.info(f"Processing question: {question}")
            
            # Retrieve relevant chunks
            relevant_chunks = await retrieve_relevant_chunks(question, index, chunks, top_k=5)
            
            if not relevant_chunks:
                answers.append("No relevant information found in the policy document for this question.")
                continue
            
            # Clean up chunk data for proper JSON serialization
            for chunk in relevant_chunks:
                # Rename similarity_score to score for clarity
                chunk["score"] = chunk.pop("similarity_score", 0.0)
                # Ensure all values are JSON serializable
                for key, value in chunk.items():
                    if hasattr(value, 'item'):  # numpy scalar
                        chunk[key] = value.item()
            
            # Generate answer
            answer = await answer_question(question, relevant_chunks)
            answers.append(answer)
            # Flatten the chunks - extend instead of append
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

@app.get("/cache/stats")
async def cache_stats(token: str = Depends(verify_token)):
    """Get cache statistics"""
    return {
        "documents_cached": len(document_cache),
        "vector_stores_cached": len(vector_store_cache)
    }

@app.delete("/cache/clear")
async def clear_cache(token: str = Depends(verify_token)):
    """Clear all caches"""
    document_cache.clear()
    vector_store_cache.clear()
    return {"message": "Cache cleared successfully"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
