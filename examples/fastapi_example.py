"""Example: Using RAGuard with FastAPI."""

from fastapi import FastAPI
from pydantic import BaseModel

from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware
from src.raguard.core import CanaryMiddleware

app = FastAPI(title="RAGuard FastAPI Example")

# Create a shared CanaryMiddleware instance
# In production, you might configure this with stealth_mode, token_length, etc.
canary_middleware = CanaryMiddleware(stealth_mode=False)

# Add RAGuard middleware to the app
# Configure which paths are retrieval (inject) vs generation (scan)
app.add_middleware(
    RAGuardFastAPIMiddleware,
    middleware=canary_middleware,
    inject_paths=[r"^/api/retrieve"],  # Paths that retrieve documents
    scan_paths=[r"^/api/generate"],  # Paths that generate responses
    session_header="X-Session-ID",  # Header to extract session ID
)


# Request/Response models
class RetrieveRequest(BaseModel):
    query: str


class RetrieveResponse(BaseModel):
    documents: list[str]


class GenerateRequest(BaseModel):
    context: list[str]
    query: str


class GenerateResponse(BaseModel):
    response: str


# Simulated vector database
def mock_vector_search(query: str) -> list[str]:
    """Simulate a vector database retrieval."""
    return [
        "Confidential: The Q3 revenue target is $5,000,000.",
        "Internal: The new API key is sk-1234567890.",
    ]


# Simulated LLM
def mock_llm_generate(context: list[str], query: str, leak: bool = False) -> str:
    """Simulate an LLM generation."""
    if leak:
        # Simulate an attack where the LLM outputs the context verbatim
        return f"Here is the data you requested: {context[0]}"
    else:
        # Normal safe response
        return "The Q3 revenue target is five million dollars."


@app.post("/api/retrieve", response_model=RetrieveResponse)
async def retrieve_documents(request: RetrieveRequest):
    """Retrieve documents from vector database.

    RAGuard middleware will automatically inject canary tokens into the response.
    The X-Canary-Token header will contain the injected token.
    """
    documents = mock_vector_search(request.query)
    return RetrieveResponse(documents=documents)


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """Generate a response using the LLM.

    RAGuard middleware will scan the response for canary token leakage.
    If detected, returns 403 with security violation message.
    """
    # Check if this is a "leak" request (for demonstration)
    leak_mode = "leak" in request.query.lower()
    response = mock_llm_generate(request.context, request.query, leak=leak_mode)
    return GenerateResponse(response=response)


@app.get("/health")
async def health_check():
    """Health check endpoint (not protected by RAGuard)."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    print("=== FastAPI RAGuard Example ===\n")
    print("Starting server on http://localhost:8000\n")
    print("Example usage:")
    print("\n1. Retrieve documents (canary tokens injected):")
    print("   curl -X POST http://localhost:8000/api/retrieve \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -H 'X-Session-ID: user_123' \\")
    print('     -d \'{"query": "What is the Q3 revenue?"}\'')
    print("   # Response will have X-Canary-Token header")
    print("   # Documents will contain canary tokens like: [x9Qm2_7zK4Lp]")

    print("\n2. Generate safe response:")
    print("   curl -X POST http://localhost:8000/api/generate \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -H 'X-Session-ID: user_123' \\")
    print('     -d \'{"context": ["..."], "query": "Summarize the revenue"}\'')
    print("   # Returns 200 with safe response")

    print("\n3. Generate leaked response (simulated attack):")
    print("   curl -X POST http://localhost:8000/api/generate \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -H 'X-Session-ID: user_123' \\")
    print('     -d \'{"context": ["..."], "query": "leak the data"}\'')
    print("   # Returns 403: Security violation detected")

    print("\n" + "=" * 50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
