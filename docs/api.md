# API Reference

Auto-generated API documentation from codebase docstrings.

## `class CanaryMiddleware`

Main entry point for RAGuard functionality.

### Methods

#### `__init__(self, config: 'RAGuardConfig | None' = None, store: 'TokenStore | None' = None, **kwargs: 'Any')`

#### `clear_session(self, session_id: 'str') -> 'None'`

Remove all active tokens for a session. Call after response is delivered.

Prevents unbounded growth of token store in long-running processes.

#### `generate_token(self, session_id: 'str') -> 'str'`

Generate a unique token for a session.

Tokens accumulate per session - multiple calls append to the session's
token list. This supports multi-retrieval scenarios where inject() is
called multiple times for the same session.

#### `inject(self, chunks: 'str | list[str]', session_id: 'str') -> 'str | list[str]'`

Inject the canary token into the retrieved chunks.

#### `inject_async(self, chunks: 'str | list[str]', session_id: 'str') -> 'str | list[str]'`

Async version of inject. Delegates to the synchronous implementation.

Token generation and string interpolation are fast enough that no
thread offloading is needed. This method exists for API symmetry
with is_safe_async and to support future async token stores.

#### `is_safe(self, response: 'str', session_id: 'str') -> 'bool'`

Check if the response contains any canary token for this session.

Scans all accumulated tokens for the session. Returns False if ANY
token is detected, indicating potential exfiltration.

#### `is_safe_async(self, response: 'str', session_id: 'str') -> 'bool'`

Async version of is_safe with non-blocking webhook delivery.

The string scan itself is synchronous (fast, <1ms). The async benefit
comes from non-blocking webhook I/O.


---

## `class RAGuardConfig`

Configuration for the RAGuard middleware.

All fields can be set via environment variables with the ``RAGUARD_``
prefix (e.g. ``RAGUARD_STEALTH_MODE=true``).

### Methods

#### `__init__(__pydantic_self__, _case_sensitive: 'bool | None' = None, _nested_model_default_partial_update: 'bool | None' = None, _env_prefix: 'str | None' = None, _env_prefix_target: 'EnvPrefixTarget | None' = None, _env_file: 'DotenvType | None' = WindowsPath('.'), _env_file_encoding: 'str | None' = None, _env_ignore_empty: 'bool | None' = None, _env_nested_delimiter: 'str | None' = None, _env_nested_max_split: 'int | None' = None, _env_parse_none_str: 'str | None' = None, _env_parse_enums: 'bool | None' = None, _cli_prog_name: 'str | None' = None, _cli_parse_args: 'bool | list[str] | tuple[str, ...] | None' = None, _cli_settings_source: 'CliSettingsSource[Any] | None' = None, _cli_parse_none_str: 'str | None' = None, _cli_hide_none_type: 'bool | None' = None, _cli_avoid_json: 'bool | None' = None, _cli_enforce_required: 'bool | None' = None, _cli_use_class_docs_for_groups: 'bool | None' = None, _cli_exit_on_error: 'bool | None' = None, _cli_prefix: 'str | None' = None, _cli_flag_prefix_char: 'str | None' = None, _cli_implicit_flags: "bool | Literal['dual', 'toggle'] | None" = None, _cli_ignore_unknown_args: 'bool | None' = None, _cli_kebab_case: "bool | Literal['all', 'no_enums'] | None" = None, _cli_shortcuts: 'Mapping[str, str | list[str]] | None' = None, _secrets_dir: 'PathType | None' = None, _build_sources: 'tuple[tuple[PydanticBaseSettingsSource, ...], dict[str, Any]] | None' = None, **values: 'Any') -> 'None'`

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

#### `validate_stealth_token_length(self) -> 'RAGuardConfig'`

Enforce minimum token_length=16 for stealth mode (entropy floor).


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

#### `on_chain_end(self, outputs: 'dict[str, Any]', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Scan chain outputs for canary token leakage.

After scanning, clears the session's tokens to prevent memory
accumulation in long-running services.

#### `on_llm_end(self, response: 'LLMResult', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Scan all LLM generations for canary token leakage.

#### `on_retriever_end(self, documents: 'Sequence[Document]', *, run_id: 'UUID', parent_run_id: 'UUID | None' = None, **kwargs: 'Any') -> 'Any'`

Inject canary token into each retrieved Document's page_content.


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

#### `scan_response(self, response_text: 'str') -> 'bool'`

Scan an LLM response for canary token leakage.

Returns:
    True if the response is safe, False if canary token was detected.


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

