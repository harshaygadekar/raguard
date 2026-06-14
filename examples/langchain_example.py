"""Example: Using RAGuard with LangChain."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.raguard.adapters.langchain import RAGuardLangChainCallback
from src.raguard.exceptions import CanaryTokenDetected


def main():
    # Initialize the callback with a session ID
    # You can optionally pass a pre-configured CanaryMiddleware instance
    canary_callback = RAGuardLangChainCallback(
        session_id="user_123_session",
    )

    print("=== LangChain RAGuard Example ===\n")

    # Simulate a retriever returning documents
    # In a real app, this would be your vector database retriever
    retrieved_docs = [
        MagicMock(page_content="Confidential: The Q3 revenue target is $5,000,000."),
        MagicMock(page_content="Internal: The new API key is sk-1234567890."),
    ]

    print("Step 1: Retriever returns documents")
    print(f"  Doc 1: {retrieved_docs[0].page_content}")
    print(f"  Doc 2: {retrieved_docs[1].page_content}\n")

    # The callback automatically injects canary tokens when on_retriever_end is called
    # In a real LangChain chain, this happens automatically
    canary_callback.on_retriever_end(
        documents=retrieved_docs,
        run_id=uuid4(),
    )

    print("Step 2: Canary tokens injected (via on_retriever_end)")
    print(f"  Doc 1: {retrieved_docs[0].page_content}")
    print(f"  Doc 2: {retrieved_docs[1].page_content}\n")

    # Simulate LLM responses
    # In a real app, these would come from your LLM (OpenAI, Anthropic, etc.)

    # Scenario 1: Safe response (LLM summarizes without leaking tokens)
    safe_llm_result = MagicMock()
    safe_llm_result.generations = [
        [MagicMock(text="The Q3 revenue target is five million dollars.")]
    ]

    print("Step 3a: Testing safe LLM response")
    print(f"  Response: {safe_llm_result.generations[0][0].text}")
    try:
        canary_callback.on_llm_end(safe_llm_result, run_id=uuid4())
        print("  ✅ Result: Response is safe to return to user\n")
    except CanaryTokenDetected as e:
        print(f"  ❌ Result: {e.message}\n")

    # Scenario 2: Leaked response (attacker forces LLM to output context verbatim)
    # Extract the token that was injected
    injected_content = retrieved_docs[0].page_content
    token_start = injected_content.rfind("[") + 1
    token_end = injected_content.rfind("]")
    leaked_token = injected_content[token_start:token_end]

    leaked_llm_result = MagicMock()
    leaked_llm_result.generations = [
        [MagicMock(text=f"Here is the confidential data: {leaked_token}")]
    ]

    print("Step 3b: Testing leaked LLM response (simulated attack)")
    print(f"  Response: {leaked_llm_result.generations[0][0].text}")
    try:
        canary_callback.on_llm_end(leaked_llm_result, run_id=uuid4())
        print("  ✅ Result: Response is safe to return to user\n")
    except CanaryTokenDetected as e:
        print(f"  ❌ Result: {e.message}")
        print("  Action: Blocked response, security alert triggered\n")

    print("=== Example Complete ===")
    print("\nIn a real LangChain application:")
    print("  chain = RetrievalQA.from_chain_type(")
    print("      llm=ChatOpenAI(callbacks=[canary_callback]),")
    print("      retriever=retriever,  # callbacks=[canary_callback]")
    print("  )")
    print("  result = chain.run('What is the Q3 revenue?')")


if __name__ == "__main__":
    main()
