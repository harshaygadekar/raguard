"""Example: Using RAGuard with LlamaIndex."""

from unittest.mock import MagicMock

from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor


def main():
    # Initialize the postprocessor with a session ID
    postprocessor = RAGuardLlamaIndexPostprocessor(
        session_id="user_123_session",
    )

    print("=== LlamaIndex RAGuard Example ===\n")

    # Simulate retrieved nodes
    # In a real app, these come from your VectorStoreIndex retriever
    mock_node_1 = MagicMock()
    mock_node_1.node = MagicMock()
    mock_node_1.node.get_content.return_value = (
        "Confidential: The Q3 revenue target is $5,000,000."
    )
    mock_node_1.score = 0.95

    mock_node_2 = MagicMock()
    mock_node_2.node = MagicMock()
    mock_node_2.node.get_content.return_value = (
        "Internal: The new API key is sk-1234567890."
    )
    mock_node_2.score = 0.87

    nodes = [mock_node_1, mock_node_2]

    print("Step 1: Retriever returns nodes")
    print(f"  Node 1: {nodes[0].node.get_content()}")
    print(f"  Node 2: {nodes[1].node.get_content()}\n")

    # Postprocess nodes to inject canary tokens
    # In a real app, add this to your QueryEngine's node_postprocessors list
    secure_nodes = postprocessor.postprocess_nodes(nodes)

    print("Step 2: Canary tokens injected (via postprocess_nodes)")
    # Get the injected content from the set_content call
    injected_1 = secure_nodes[0].node.set_content.call_args[0][0]
    injected_2 = secure_nodes[1].node.set_content.call_args[0][0]
    print(f"  Node 1: {injected_1}")
    print(f"  Node 2: {injected_2}\n")

    # Simulate LLM responses
    # In a real app, this comes from query_engine.query()

    # Scenario 1: Safe response (LLM summarizes without leaking tokens)
    safe_response = "The Q3 revenue target is five million dollars."

    print("Step 3a: Testing safe LLM response")
    print(f"  Response: {safe_response}")
    if postprocessor.scan_response(safe_response):
        print("  ✅ Result: Response is safe to return to user\n")
    else:
        print("  ❌ Result: Canary token detected!")
        print("  Action: Block response and alert security team\n")

    # Scenario 2: Leaked response (attacker forces LLM to output context)
    # Extract the token that was injected
    token_start = injected_1.rfind("[") + 1
    token_end = injected_1.rfind("]")
    leaked_token = injected_1[token_start:token_end]

    leaked_response = f"Here is the confidential data: {leaked_token}"

    print("Step 3b: Testing leaked LLM response (simulated attack)")
    print(f"  Response: {leaked_response}")
    if postprocessor.scan_response(leaked_response):
        print("  ✅ Result: Response is safe to return to user\n")
    else:
        print("  ❌ Result: Canary token detected!")
        print("  Action: Block response and alert security team\n")

    print("=== Example Complete ===")
    print("\nIn a real LlamaIndex application:")
    print("  query_engine = RetrieverQueryEngine(")
    print("      retriever=retriever,")
    print("      node_postprocessors=[postprocessor],  # Add RAGuard here")
    print("      response_synthesizer=response_synthesizer,")
    print("  )")
    print("  response = query_engine.query('What is the Q3 revenue?')")
    print("  if not postprocessor.scan_response(str(response)):")
    print("      raise CanaryTokenDetected(session_id='user_123_session')")


if __name__ == "__main__":
    main()
