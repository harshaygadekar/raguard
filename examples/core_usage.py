"""Example: Basic usage of the RAGuard core engine."""

from src.raguard import CanaryMiddleware

def main():
    # Initialize middleware
    canary = CanaryMiddleware(stealth_mode=False)
    session_id = "user_123_session"

    # 1. Simulate retrieval
    retrieved_docs = [
        "Confidential: The Q3 revenue target is $5,000,000.",
        "Internal: The new API key is sk-1234567890."
    ]

    # 2. Inject canary tokens
    secure_docs = canary.inject(retrieved_docs, session_id)
    print("--- Secure Context ---")
    for doc in secure_docs:
        print(doc)
    print("----------------------\n")

    # 3. Simulate LLM responses
    safe_response = "The Q3 revenue target is five million dollars."
    leaked_response = "Confidential: The Q3 revenue target is $5,000,000."

    # 4. Validate responses
    print("Testing safe response:")
    if canary.is_safe(safe_response, session_id):
        print("✅ Response is safe to return to user.\n")
    else:
        print("❌ Response blocked.\n")

    print("Testing leaked response:")
    if canary.is_safe(leaked_response, session_id):
        print("✅ Response is safe to return to user.\n")
    else:
        print("❌ Response blocked due to canary token detection.\n")

if __name__ == "__main__":
    main()