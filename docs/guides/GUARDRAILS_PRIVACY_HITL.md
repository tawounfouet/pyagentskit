# Guardrails, privacy and Human-in-the-Loop — 0.4.0

## Guardrail boundaries

`GuardrailPipeline` can govern input text, normalized `ModelRequest`, `ToolCall`, `ToolResult` and
final output. Policies run in declaration order. A transformation becomes the value evaluated by
the next policy. Any policy exception, rejection or abort fails closed.

```python
pipeline = GuardrailPipeline([input_policy, tool_policy, output_policy])
runner = Runner(model, tools=registry, guardrails=pipeline)
```

`retry_with_feedback` is supported for final output and is bounded to one additional model call.
`require_approval` is supported for tool calls. Unsupported action/stage combinations are rejected
rather than silently downgraded.

## Provider egress

```python
policy = DataPolicy(
    max_classification=DataClassification.CONFIDENTIAL,
    allowed_providers=("openrouter",),
    allowed_models=("anthropic/approved-model",),
    require_zdr=True,
    allow_training=False,
)
```

Set `RunContext.metadata["data_classification"]` to `public`, `internal`, `confidential` or
`restricted`. The policy runs immediately before network access. Required privacy properties must
be supplied by adapter-owned configuration. Prompts and agent metadata are not trusted evidence.

## Approval flow

Approval needs both an `ApprovalStore` and a `SessionStore` plus a `session_id`. When a tool is
declared `requires_approval=True`, the first call returns `WAITING_APPROVAL` and exposes only the
approval identifier in result metadata.

```python
waiting = await runner.run(agent, request, context=context)
approval = await approval_store.get(waiting.metadata["approval_id"], tenant_id=tenant)

await approval_store.resolve(
    approval.approval_id,
    ApprovalDecision.APPROVE,
    actor_id="reviewer.account",
    reason="business evidence checked",
    tenant_id=tenant,
    expected_revision=approval.revision,
)

result = await runner.resume_approval(
    agent,
    approval.approval_id,
    context=context,
)
```

The application must authenticate `actor_id`, enforce tenant authorization and protect the
approval database. A transformed call does not match the stored fingerprint and needs a new
approval. The store atomically claims either an approval or rejection before continuation, so a
second resume fails.

## Crash boundary

If the process stops after claim but before tool-result persistence, PyAgentsKit does not guess
whether the external effect happened. Lot 10's `DurableRunner` records `unknown_effect` and requires
an explicit `COMMITTED` or `NOT_APPLIED` resolution before continuation.

## Secrets and redaction

`EnvironmentSecretProvider` only reads explicitly allowlisted names and never caches values in a
serializable model. `Redactor` handles recursive values and common credential patterns. Use it as
defense in depth; application logs, traces, databases and approval UIs still require access control,
retention and dedicated DLP policy.
