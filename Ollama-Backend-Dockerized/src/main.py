"""
Ollama Backend API Server
FastAPI application that proxies requests to Ollama for LLM inference.
"""
import os
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

# Models
class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float = 0.7

class PullRequest(BaseModel):
    model: str

# Health check endpoint
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Ollama Backend starting. Ollama host: {OLLAMA_HOST}")
    yield
    logger.info("🛑 Ollama Backend shutting down")

app = FastAPI(
    title="Ollama Backend API",
    description="HTTP proxy for Ollama LLM inference on Kubernetes",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for Kubernetes liveness probe."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
        return {"status": "healthy", "ollama": "reachable"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Ollama not reachable: {str(e)}")

@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Not ready")

@app.get("/api/models", tags=["models"])
async def list_models():
    """List all available models on Ollama."""
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to list models: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Failed to reach Ollama: {str(e)}")

@app.post("/api/pull", tags=["models"])
async def pull_model(request: PullRequest):
    """Pull a model from the Ollama registry."""
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/pull",
                json={"name": request.model},
                timeout=None
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to pull model {request.model}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Failed to pull model: {str(e)}")

@app.post("/api/generate", tags=["inference"])
async def generate(request: GenerateRequest):
    """Generate text using Ollama."""
    try:
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": request.stream,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k,
            }
        }

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=None
            )
            response.raise_for_status()

            if request.stream:
                return StreamingResponse(
                    generate_stream_response(response),
                    media_type="application/x-ndjson"
                )
            else:
                return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Generate request failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Ollama error: {str(e)}")

async def generate_stream_response(response):
    """Stream response from Ollama."""
    async for line in response.aiter_lines():
        if line:
            yield line + "\n"

@app.post("/api/chat", tags=["inference"])
async def chat(request: ChatRequest):
    """Chat with Ollama using multi-turn conversation."""
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        payload = {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
            "options": {
                "temperature": request.temperature,
            }
        }

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=None
            )
            response.raise_for_status()

            if request.stream:
                return StreamingResponse(
                    generate_stream_response(response),
                    media_type="application/x-ndjson"
                )
            else:
                return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Chat request failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Ollama error: {str(e)}")

@app.get("/", tags=["root"])
async def root():
    """API root endpoint."""
    return {
        "name": "Ollama Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "ollama_host": OLLAMA_HOST
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
