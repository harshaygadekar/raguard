# API Reference

Auto-generated API documentation from codebase docstrings.

## `class CanaryMiddleware`

Main entry point for RAGuard functionality.

### Methods

#### `__init__(self, config: raguard.config.RAGuardConfig | None = None, **kwargs: Any)`

#### `clear_session(self, session_id: str) -> None`

Remove all active tokens for a session. Call after response is delivered.

Prevents unbounded growth of _active_tokens in long-running processes.

#### `generate_token(self, session_id: str) -> str`

Generate a unique token for a session.

Tokens accumulate per session - multiple calls append to the session's
token list. This supports multi-retrieval scenarios where inject() is
called multiple times for the same session.

#### `inject(self, chunks: str | list[str], session_id: str) -> str | list[str]`

Inject the canary token into the retrieved chunks.

#### `inject_async(self, chunks: str | list[str], session_id: str) -> str | list[str]`

Async version of inject. Delegates to the synchronous implementation.

Token generation and string interpolation are fast enough that no
thread offloading is needed. This method exists for API symmetry
with is_safe_async and to support future async token stores.

#### `is_safe(self, response: str, session_id: str) -> bool`

Check if the response contains any canary token for this session.

Scans all accumulated tokens for the session. Returns False if ANY
token is detected, indicating potential exfiltration.

#### `is_safe_async(self, response: str, session_id: str) -> bool`

Async version of is_safe with non-blocking webhook delivery.

The string scan itself is synchronous (fast, <1ms). The async benefit
comes from non-blocking webhook I/O.


---

## `class RAGuardConfig`

Configuration for the RAGuard middleware.

### Methods

#### `__init__(self, /, **data: 'Any') -> 'None'`

Create a new model by parsing and validating input data from keyword arguments.

Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
validated to form a valid model.

`self` is explicitly positional-only to allow `self` as a field name.

#### `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`

Returns a copy of the model.

!!! warning "Deprecated"
    This method is now deprecated; use `model_copy` instead.

If you need `include` or `exclude`, use:

```python {test="skip" lint="skip"}
data = self.model_dump(include=include, exclude=exclude, round_trip=True)
data = {**data, **(update or {})}
copied = self.model_validate(data)
```

Args:
    include: Optional set or mapping specifying which fields to include in the copied model.
    exclude: Optional set or mapping specifying which fields to exclude in the copied model.
    update: Optional dictionary of field-value pairs to override field values in the copied model.
    deep: If True, the values of fields that are Pydantic models will be deep-copied.

Returns:
    A copy of the model with included, excluded and updated fields as specified.

#### `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`

#### `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`

#### `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`

!!! abstract "Usage Documentation"
    [`model_copy`](../concepts/models.md#model-copy)

Returns a copy of the model.

!!! note
    The underlying instance's [`__dict__`][object.__dict__] attribute is copied. This
    might have unexpected side effects if you store anything in it, on top of the model
    fields (e.g. the value of [cached properties][functools.cached_property]).

Args:
    update: Values to change/add in the new model. Note: the data is not validated
        before creating the new model. You should trust this data.
    deep: Set to `True` to make a deep copy of the model.

Returns:
    New model instance.

#### `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, exclude_computed_fields: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False, polymorphic_serialization: 'bool | None' = None) -> 'dict[str, Any]'`

!!! abstract "Usage Documentation"
    [`model_dump`](../concepts/serialization.md#python-mode)

Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

Args:
    mode: The mode in which `to_python` should run.
        If mode is 'json', the output will only contain JSON serializable types.
        If mode is 'python', the output may contain non-JSON-serializable Python objects.
    include: A set of fields to include in the output.
    exclude: A set of fields to exclude from the output.
    context: Additional context to pass to the serializer.
    by_alias: Whether to use the field's alias in the dictionary key if defined.
    exclude_unset: Whether to exclude fields that have not been explicitly set.
    exclude_defaults: Whether to exclude fields that are set to their default value.
    exclude_none: Whether to exclude fields that have a value of `None`.
    exclude_computed_fields: Whether to exclude computed fields.
        While this can be useful for round-tripping, it is usually recommended to use the dedicated
        `round_trip` parameter instead.
    round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
    warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
        "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
    fallback: A function to call when an unknown value is encountered. If not provided,
        a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
    serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
    polymorphic_serialization: Whether to use model and dataclass polymorphic serialization for this call.

Returns:
    A dictionary representation of the model.

#### `model_dump_json(self, *, indent: 'int | None' = None, ensure_ascii: 'bool' = False, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, exclude_computed_fields: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False, polymorphic_serialization: 'bool | None' = None) -> 'str'`

!!! abstract "Usage Documentation"
    [`model_dump_json`](../concepts/serialization.md#json-mode)

Generates a JSON representation of the model using Pydantic's `to_json` method.

Args:
    indent: Indentation to use in the JSON output. If None is passed, the output will be compact.
    ensure_ascii: If `True`, the output is guaranteed to have all incoming non-ASCII characters escaped.
        If `False` (the default), these characters will be output as-is.
    include: Field(s) to include in the JSON output.
    exclude: Field(s) to exclude from the JSON output.
    context: Additional context to pass to the serializer.
    by_alias: Whether to serialize using field aliases.
    exclude_unset: Whether to exclude fields that have not been explicitly set.
    exclude_defaults: Whether to exclude fields that are set to their default value.
    exclude_none: Whether to exclude fields that have a value of `None`.
    exclude_computed_fields: Whether to exclude computed fields.
        While this can be useful for round-tripping, it is usually recommended to use the dedicated
        `round_trip` parameter instead.
    round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
    warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
        "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
    fallback: A function to call when an unknown value is encountered. If not provided,
        a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
    serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
    polymorphic_serialization: Whether to use model and dataclass polymorphic serialization for this call.

Returns:
    A JSON string representation of the model.

#### `model_post_init(self, context: 'Any', /) -> 'None'`

Override this method to perform additional initialization after `__init__` and `model_construct`.
This is useful if you want to do some validation that requires the entire model to be initialized.


---

## `class RAGuardLangChainCallback`

LangChain callback handler that injects canary tokens on retrieval
and scans LLM output for exfiltration.

Usage:
    canary_cb = RAGuardLangChainCallback(session_id="user_123")
    chain = RetrievalQA.from_chain_id(
        llm=ChatOpenAI(callbacks=[canary_cb]),
        retriever=retriever,
    )

### Methods

#### `__init__(self, session_id: 'str', middleware: 'CanaryMiddleware | None' = None, config: 'RAGuardConfig | None' = None, **kwargs: 'Any') -> 'None'`

#### `on_agent_action(self, action: 'AgentAction', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run on agent action.

Args:
    action: The agent action.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_agent_finish(self, finish: 'AgentFinish', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run on the agent end.

Args:
    finish: The agent finish.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_chain_end(self, outputs: 'dict[str, Any]', *, run_id: 'Any', parent_run_id: 'Any | None' = None, **kwargs: 'Any') -> 'None'`

Scan chain outputs for canary token leakage.

#### `on_chain_error(self, error: 'BaseException', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run when chain errors.

Args:
    error: The error that occurred.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_chain_start(self, serialized: 'dict[str, Any]', inputs: 'dict[str, Any]', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when a chain starts running.

Args:
    serialized: The serialized chain.
    inputs: The inputs.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    metadata: The metadata.
    **kwargs: Additional keyword arguments.

#### `on_chat_model_start(self, serialized: 'dict[str, Any]', messages: 'list[list[BaseMessage]]', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when a chat model starts running.

!!! warning

    This method is called for chat models. If you're implementing a handler for
    a non-chat model, you should use `on_llm_start` instead.

!!! note

    When overriding this method, the signature **must** include the two
    required positional arguments `serialized` and `messages`.  Avoid
    using `*args` in your override — doing so causes an `IndexError`
    in the fallback path when the callback system converts `messages`
    to prompt strings for `on_llm_start`.  Always declare the
    signature explicitly:

    .. code-block:: python

        def on_chat_model_start(
            self,
            serialized: dict[str, Any],
            messages: list[list[BaseMessage]],
            **kwargs: Any,
        ) -> None:
            raise NotImplementedError  # triggers fallback to on_llm_start

Args:
    serialized: The serialized chat model.
    messages: The messages. Must be a list of message lists — this is a
        required positional argument and must be present in any override.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    metadata: The metadata.
    **kwargs: Additional keyword arguments.

#### `on_custom_event(self, name: 'str', data: 'Any', *, run_id: 'UUID', tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Override to define a handler for a custom event.

Args:
    name: The name of the custom event.
    data: The data for the custom event.

        Format will match the format specified by the user.
    run_id: The ID of the run.
    tags: The tags associated with the custom event (includes inherited tags).
    metadata: The metadata associated with the custom event (includes inherited
        metadata).

#### `on_llm_end(self, response: 'Any', *, run_id: 'Any', parent_run_id: 'Any | None' = None, **kwargs: 'Any') -> 'None'`

Scan all LLM generations for canary token leakage.

#### `on_llm_error(self, error: 'BaseException', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when LLM errors.

Args:
    error: The error that occurred.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    **kwargs: Additional keyword arguments.

#### `on_llm_new_token(self, token: 'str', *, chunk: 'GenerationChunk | ChatGenerationChunk | None' = None, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, **kwargs: 'Any') -> 'Any'`

Run on new output token.

Only available when streaming is enabled.

For both chat models and non-chat models (legacy text completion LLMs).

Args:
    token: The new token.
    chunk: The new generated chunk, containing content and other information.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    **kwargs: Additional keyword arguments.

#### `on_llm_start(self, serialized: 'dict[str, Any]', prompts: 'list[str]', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when LLM starts running.

!!! warning

    This method is called for non-chat models (regular text completion LLMs). If
    you're implementing a handler for a chat model, you should use
    `on_chat_model_start` instead.

Args:
    serialized: The serialized LLM.
    prompts: The prompts.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    metadata: The metadata.
    **kwargs: Additional keyword arguments.

#### `on_retriever_end(self, documents: 'list[Any]', *, run_id: 'Any', parent_run_id: 'Any | None' = None, **kwargs: 'Any') -> 'None'`

Inject canary token into each retrieved Document's page_content.

#### `on_retriever_error(self, error: 'BaseException', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run when `Retriever` errors.

Args:
    error: The error that occurred.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_retriever_start(self, serialized: 'dict[str, Any]', query: 'str', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when the `Retriever` starts running.

Args:
    serialized: The serialized `Retriever`.
    query: The query.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    metadata: The metadata.
    **kwargs: Additional keyword arguments.

#### `on_retry(self, retry_state: 'RetryCallState', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run on a retry event.

Args:
    retry_state: The retry state.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_stream_event(self, event: 'MessagesData', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, **kwargs: 'Any') -> 'Any'`

Run on each protocol event from `stream_events(version="v3")`.

Also fires for the async equivalent
(`astream_events(version="v3")`).

Fires once per `MessagesData` event — `message-start`, per-block
`content-block-start` / `content-block-delta` /
`content-block-finish`, and `message-finish`. Analogous to
`on_llm_new_token` in v1 streaming, but at event granularity rather
than chunk: a single chunk can map to multiple events (e.g. a
`content-block-start` plus its first `content-block-delta`), and
lifecycle boundaries are explicit.

Fires uniformly whether the provider emits events natively via
`_stream_chat_model_events` or goes through the chunk-to-event
compat bridge. Observers see the same event stream regardless of
how the underlying model produces output.

Not fired from v1 `stream()` / `astream()`; for those, keep using
`on_llm_new_token`. Purely additive — `on_chat_model_start`,
`on_llm_end`, and `on_llm_error` still fire around a v2 call as
they do around a v1 call.

Args:
    event: The protocol event.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    **kwargs: Additional keyword arguments.

#### `on_text(self, text: 'str', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run on an arbitrary text.

Args:
    text: The text.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_tool_end(self, output: 'Any', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run when the tool ends running.

Args:
    output: The output of the tool.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_tool_error(self, error: 'BaseException', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Run when tool errors.

Args:
    error: The error that occurred.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    **kwargs: Additional keyword arguments.

#### `on_tool_start(self, serialized: 'dict[str, Any]', input_str: 'str', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, tags: 'list[str] | None' = None, metadata: 'dict[str, Any] | None' = None, inputs: 'dict[str, Any] | None' = None, **kwargs: 'Any') -> 'Any'`

Run when the tool starts running.

Args:
    serialized: The serialized chain.
    input_str: The input string.
    run_id: The ID of the current run.
    parent_run_id: The ID of the parent run.
    tags: The tags.
    metadata: The metadata.
    inputs: The inputs.
    **kwargs: Additional keyword arguments.


---

## `class RAGuardLlamaIndexPostprocessor`

LlamaIndex node postprocessor that injects canary tokens into
retrieved nodes before they reach the LLM.

Usage:
    postprocessor = RAGuardLlamaIndexPostprocessor(session_id="user_123")
    safe_nodes = postprocessor.postprocess_nodes(nodes, query_bundle)

    # After generation, manually scan the response:
    response = query_engine.query("What is the secret?")
    if not postprocessor.scan_response(str(response)):
        raise CanaryTokenDetected(session_id=postprocessor.session_id)

### Methods

#### `__init__(self, session_id: 'str', middleware: 'CanaryMiddleware | None' = None, config: 'RAGuardConfig | None' = None, **kwargs: 'Any') -> 'None'`

#### `apostprocess_nodes(self, nodes: List[llama_index.core.schema.NodeWithScore], query_bundle: llama_index.core.schema.QueryBundle | None = None, query_str: str | None = None) -> List[llama_index.core.schema.NodeWithScore]`

Postprocess nodes (async).

#### `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`

Returns a copy of the model.

!!! warning "Deprecated"
    This method is now deprecated; use `model_copy` instead.

If you need `include` or `exclude`, use:

```python {test="skip" lint="skip"}
data = self.model_dump(include=include, exclude=exclude, round_trip=True)
data = {**data, **(update or {})}
copied = self.model_validate(data)
```

Args:
    include: Optional set or mapping specifying which fields to include in the copied model.
    exclude: Optional set or mapping specifying which fields to exclude in the copied model.
    update: Optional dictionary of field-value pairs to override field values in the copied model.
    deep: If True, the values of fields that are Pydantic models will be deep-copied.

Returns:
    A copy of the model with included, excluded and updated fields as specified.

#### `custom_model_dump(self, handler: 'SerializerFunctionWrapHandler', info: 'SerializationInfo') -> 'Dict[str, Any]'`

#### `dict(self, **kwargs: 'Any') -> 'Dict[str, Any]'`

#### `json(self, **kwargs: 'Any') -> 'str'`

#### `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`

!!! abstract "Usage Documentation"
    [`model_copy`](../concepts/models.md#model-copy)

Returns a copy of the model.

!!! note
    The underlying instance's [`__dict__`][object.__dict__] attribute is copied. This
    might have unexpected side effects if you store anything in it, on top of the model
    fields (e.g. the value of [cached properties][functools.cached_property]).

Args:
    update: Values to change/add in the new model. Note: the data is not validated
        before creating the new model. You should trust this data.
    deep: Set to `True` to make a deep copy of the model.

Returns:
    New model instance.

#### `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, exclude_computed_fields: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False, polymorphic_serialization: 'bool | None' = None) -> 'dict[str, Any]'`

!!! abstract "Usage Documentation"
    [`model_dump`](../concepts/serialization.md#python-mode)

Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

Args:
    mode: The mode in which `to_python` should run.
        If mode is 'json', the output will only contain JSON serializable types.
        If mode is 'python', the output may contain non-JSON-serializable Python objects.
    include: A set of fields to include in the output.
    exclude: A set of fields to exclude from the output.
    context: Additional context to pass to the serializer.
    by_alias: Whether to use the field's alias in the dictionary key if defined.
    exclude_unset: Whether to exclude fields that have not been explicitly set.
    exclude_defaults: Whether to exclude fields that are set to their default value.
    exclude_none: Whether to exclude fields that have a value of `None`.
    exclude_computed_fields: Whether to exclude computed fields.
        While this can be useful for round-tripping, it is usually recommended to use the dedicated
        `round_trip` parameter instead.
    round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
    warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
        "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
    fallback: A function to call when an unknown value is encountered. If not provided,
        a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
    serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
    polymorphic_serialization: Whether to use model and dataclass polymorphic serialization for this call.

Returns:
    A dictionary representation of the model.

#### `model_dump_json(self, *, indent: 'int | None' = None, ensure_ascii: 'bool' = False, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, exclude_computed_fields: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False, polymorphic_serialization: 'bool | None' = None) -> 'str'`

!!! abstract "Usage Documentation"
    [`model_dump_json`](../concepts/serialization.md#json-mode)

Generates a JSON representation of the model using Pydantic's `to_json` method.

Args:
    indent: Indentation to use in the JSON output. If None is passed, the output will be compact.
    ensure_ascii: If `True`, the output is guaranteed to have all incoming non-ASCII characters escaped.
        If `False` (the default), these characters will be output as-is.
    include: Field(s) to include in the JSON output.
    exclude: Field(s) to exclude from the JSON output.
    context: Additional context to pass to the serializer.
    by_alias: Whether to serialize using field aliases.
    exclude_unset: Whether to exclude fields that have not been explicitly set.
    exclude_defaults: Whether to exclude fields that are set to their default value.
    exclude_none: Whether to exclude fields that have a value of `None`.
    exclude_computed_fields: Whether to exclude computed fields.
        While this can be useful for round-tripping, it is usually recommended to use the dedicated
        `round_trip` parameter instead.
    round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
    warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
        "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
    fallback: A function to call when an unknown value is encountered. If not provided,
        a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
    serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
    polymorphic_serialization: Whether to use model and dataclass polymorphic serialization for this call.

Returns:
    A JSON string representation of the model.

#### `model_post_init(self, context: 'Any', /) -> 'None'`

Override this method to perform additional initialization after `__init__` and `model_construct`.
This is useful if you want to do some validation that requires the entire model to be initialized.

#### `postprocess_nodes(self, nodes: List[llama_index.core.schema.NodeWithScore], query_bundle: llama_index.core.schema.QueryBundle | None = None, query_str: str | None = None) -> List[llama_index.core.schema.NodeWithScore]`

Postprocess nodes.

#### `scan_response(self, response_text: 'str') -> 'bool'`

Scan an LLM response for canary token leakage.

Returns:
    True if the response is safe, False if canary token was detected.

#### `to_dict(self, **kwargs: 'Any') -> 'Dict[str, Any]'`

#### `to_json(self, **kwargs: 'Any') -> 'str'`


---

## `class RAGuardFastAPIMiddleware`

FastAPI/Starlette middleware for RAG canary token injection and scanning.

CONFIGURABLE: Specify which paths trigger injection vs scanning.

Usage:
    app = FastAPI()
    app.add_middleware(
        RAGuardFastAPIMiddleware,
        middleware=CanaryMiddleware(),
        inject_paths=[r"^/api/retrieve"],
        scan_paths=[r"^/api/generate"],
    )

### Methods

#### `__init__(self, app: 'Any', middleware: 'CanaryMiddleware | None' = None, config: 'RAGuardConfig | None' = None, inject_paths: 'list[str] | None' = None, scan_paths: 'list[str] | None' = None, session_header: 'str' = 'X-Session-ID') -> 'None'`

#### `dispatch(self, request: 'Request', call_next: 'Any') -> 'Response'`

Process request: inject on retrieval paths, scan on generation paths.

