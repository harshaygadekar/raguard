# RAGuard System Architecture

## Overview
RAGuard is designed with a strict separation of concerns: a framework-agnostic **Core Engine** handles the cryptographic logic, while lightweight **Adapters** bridge the core to specific RAG frameworks (LangChain, LlamaIndex, FastAPI).

## Core Components

1. **Token Generator**: Creates cryptographically secure random strings (alphanumeric) or zero-width Unicode sequences per session.
2. **Context Injector**: Appends the token to the retrieved text chunks without altering their semantic meaning.
3. **Output Scanner**: Performs a fast, deterministic regex or string match on the LLM's final output before it reaches the user.

## Architecture Diagram

```mermaid
sequenceDiagram
    participant User
    participant App as RAG Application
    participant RAGuard as RAGuard Middleware
    participant VectorDB as Vector Database
    participant LLM as LLM Provider

    User->>App: Send Query (potentially malicious)
    App->>VectorDB: Search for relevant chunks
    VectorDB-->>App: Return raw chunks
    App->>RAGuard: inject(chunks, session_id)
    RAGuard-->>App: Return chunks + canary token
    App->>LLM: Prompt (System + Augmented Context + Query)
    LLM-->>App: Generate response
    App->>RAGuard: is_safe(response, session_id)
    alt Token Detected
        RAGuard-->>App: Block response, trigger alert
        App-->>User: "Security Violation"
    else Token Not Detected
        RAGuard-->>App: Allow response
        App-->>User: Return safe response
    end
```

## Adapter Pattern
Adapters do not contain business logic. They simply hook into the lifecycle events of their respective frameworks:
- **LangChain**: Implements `BaseCallbackHandler` (`on_retriever_end`, `on_llm_end`).
- **LlamaIndex**: Implements `NodePostprocessor` (modifies nodes pre-LLM) and a custom output parser.
- **FastAPI**: Implements standard `BaseHTTPMiddleware` to wrap the entire chat endpoint.