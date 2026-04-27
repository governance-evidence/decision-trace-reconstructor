"""AWS Bedrock AgentCore adapter mapping tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from reconstructor.adapters.bedrock import (
    BedrockIngestOptions,
    fetch_agent_memory_contents,
    fetch_cloudwatch_events,
    load_sessions_cloudwatch,
    load_sessions_file,
    normalise_bedrock_input,
    sessions_to_fragments,
    sessions_to_manifest,
    validate_sessions_complete,
)
from reconstructor.core.fragment import FragmentKind, StackTier


def _session_payload() -> dict[str, Any]:
    return {
        "sessionId": "bedrock-session-001",
        "agentId": "agent-123",
        "agentAliasId": "support-agent",
        "agentVersion": "42",
        "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "trace": {
            "preProcessingTrace": {
                "traceId": "trace-pre",
                "eventTime": "2025-01-01T00:00:00Z",
                "modelInvocationInput": {"text": "User requests a refund"},
                "modelInvocationOutput": {"intent": "refund"},
            },
            "knowledgeBaseLookupTrace": {
                "traceId": "trace-kb",
                "eventTime": "2025-01-01T00:00:01Z",
                "knowledgeBaseLookupInput": {"query": "refund policy"},
                "knowledgeBaseLookupOutput": {
                    "sources": [{"id": "doc-1", "uri": "s3://kb/refund.md"}]
                },
            },
            "orchestrationTrace": {
                "traceId": "trace-orch",
                "eventTime": "2025-01-01T00:00:02Z",
                "modelInvocationInput": {"prompt": "decide next step"},
                "modelInvocationOutput": {"text": "issue refund"},
                "invocationInput": {
                    "actionGroupInvocationInput": {
                        "actionGroupName": "orders_api",
                        "apiPath": "/refunds",
                        "verb": "POST",
                        "parameters": {"order_id": "A100"},
                    }
                },
                "observation": {"finalResponse": {"text": "Refund submitted"}},
            },
            "guardrailTrace": {
                "traceId": "trace-policy",
                "eventTime": "2025-01-01T00:00:03Z",
                "guardrailId": "refund-approval-policy",
            },
            "returnControl": {
                "traceId": "trace-human",
                "eventTime": "2025-01-01T00:00:04Z",
                "invocationResults": {"approved": True, "operator": "ops-1"},
            },
        },
    }


def _cloudwatch_events() -> dict[str, Any]:
    first = {
        "sessionId": "bedrock-session-001",
        "agentId": "agent-123",
        "agentAliasId": "support-agent",
        "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "trace": {
            "preProcessingTrace": {
                "traceId": "trace-pre",
                "modelInvocationInput": {"text": "User requests a refund"},
            }
        },
    }
    second = {
        "sessionId": "bedrock-session-001",
        "agentId": "agent-123",
        "agentAliasId": "support-agent",
        "trace": {
            "orchestrationTrace": {
                "traceId": "trace-orch",
                "invocationInput": {
                    "actionGroupInvocationInput": {
                        "actionGroupName": "orders_api",
                        "apiPath": "/refunds",
                        "verb": "POST",
                    }
                },
            }
        },
    }
    return {
        "events": [
            {"timestamp": 1735689600000, "message": json.dumps(first)},
            {"timestamp": 1735689601000, "message": json.dumps(second)},
        ]
    }


def test_session_maps_core_bedrock_blocks_to_fragments() -> None:
    fragments = sessions_to_fragments([_session_payload()])
    kinds = [fragment.kind for fragment in fragments]

    assert kinds[0] is FragmentKind.CONFIG_SNAPSHOT
    assert FragmentKind.AGENT_MESSAGE in kinds
    assert FragmentKind.MODEL_GENERATION in kinds
    assert FragmentKind.RETRIEVAL_RESULT in kinds
    assert FragmentKind.TOOL_CALL in kinds
    assert FragmentKind.STATE_MUTATION in kinds
    assert FragmentKind.POLICY_SNAPSHOT in kinds
    assert FragmentKind.HUMAN_APPROVAL in kinds


def test_cloudwatch_export_is_grouped_into_single_session() -> None:
    sessions = normalise_bedrock_input(_cloudwatch_events())
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "bedrock-session-001"
    assert len(sessions[0]["events"]) == 2


def test_cross_stack_action_group_elevates_tool_fragments() -> None:
    fragments = sessions_to_fragments(
        [_session_payload()],
        BedrockIngestOptions(cross_stack_action_groups=("orders_api",)),
    )
    tool_fragment = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL
    )
    state_fragment = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.STATE_MUTATION
    )
    assert tool_fragment.stack_tier is StackTier.CROSS_STACK
    assert state_fragment.stack_tier is StackTier.CROSS_STACK


def test_failure_trace_emits_error_fragment() -> None:
    payload = _session_payload()
    payload["trace"] = {
        "failureTrace": {
            "traceId": "trace-failure",
            "eventTime": "2025-01-01T00:00:05Z",
            "failureReason": "tool timed out",
        }
    }
    fragments = sessions_to_fragments([payload])
    assert len(fragments) == 2
    assert fragments[1].kind is FragmentKind.ERROR
    assert fragments[1].payload["error"] == "tool timed out"


def test_auto_architecture_promotes_multi_agent_on_collaborator_trace() -> None:
    payload = _session_payload()
    payload["trace"]["orchestrationTrace"]["agentCollaboratorInvocationInput"] = {
        "collaboratorName": "reviewer_agent"
    }
    manifest = sessions_to_manifest(
        [payload],
        scenario_id="bedrock_multi_agent",
        opts=BedrockIngestOptions(auto_architecture=True),
    )
    assert manifest["architecture"] == "multi_agent"


def test_default_content_is_hashed() -> None:
    fragments = sessions_to_fragments([_session_payload()])
    message = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.AGENT_MESSAGE
    )
    assert isinstance(message.payload["content"], dict)
    assert set(message.payload["content"]) == {"sha256", "length"}


def test_load_sessions_file_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "bedrock.jsonl"
    events = _cloudwatch_events()["events"]
    path.write_text("\n".join(json.dumps(item) for item in events) + "\n")
    sessions = load_sessions_file(path)
    assert len(sessions) == 1
    assert sessions[0]["events"][0]["trace_type"] == "preProcessingTrace"


def test_function_schema_action_group_maps_to_tool_call() -> None:
    payload = _session_payload()
    payload["trace"] = {
        "orchestrationTrace": {
            "traceId": "trace-fn",
            "eventTime": "2025-01-01T00:00:02Z",
            "invocationInput": {
                "actionGroupInvocationInput": {
                    "actionGroupName": "crm_functions",
                    "functionName": "write_note",
                    "parameters": {"customer_id": "cust-1"},
                }
            },
        }
    }

    fragments = sessions_to_fragments([payload])
    tool_fragment = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL
    )

    assert tool_fragment.payload["tool_name"] == "crm_functions:write_note"


def test_code_interpreter_maps_to_tool_call_and_state_mutation() -> None:
    payload = _session_payload()
    payload["trace"] = {
        "orchestrationTrace": {
            "traceId": "trace-ci",
            "eventTime": "2025-01-01T00:00:02Z",
            "invocationInput": {
                "codeInterpreterInvocationInput": {
                    "code": "import pandas as pd\ndf.to_csv('refund.csv')",
                    "files": ["s3://tmp/input.csv"],
                }
            },
        }
    }

    fragments = sessions_to_fragments([payload])
    kinds = [fragment.kind for fragment in fragments]

    assert kinds.count(FragmentKind.TOOL_CALL) == 1
    assert kinds.count(FragmentKind.STATE_MUTATION) == 1
    tool_fragment = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.TOOL_CALL
    )
    assert tool_fragment.payload["tool_name"] == "code_interpreter"


def test_memory_contents_emit_retrieval_result() -> None:
    payload = _session_payload()
    payload["memoryId"] = "memory-user-001"
    payload["memoryContents"] = [
        {
            "sessionSummary": {
                "memoryId": "memory-user-001",
                "sessionId": "prior-session-1",
                "summaryText": "Customer previously received a courtesy refund",
            }
        }
    ]

    fragments = sessions_to_fragments([payload])
    retrieval = next(
        fragment for fragment in fragments if fragment.kind is FragmentKind.RETRIEVAL_RESULT
    )

    assert retrieval.payload["query"]["memory_id"] == "memory-user-001"


def test_session_summary_emits_memory_state_mutation() -> None:
    payload = _session_payload()
    payload["memoryId"] = "memory-user-001"
    payload["sessionSummary"] = {
        "memoryId": "memory-user-001",
        "sessionId": "bedrock-session-001",
        "summaryText": "Refund request approved and queued",
    }

    fragments = sessions_to_fragments([payload])
    state_fragment = next(
        fragment
        for fragment in fragments
        if fragment.kind is FragmentKind.STATE_MUTATION
        and fragment.payload.get("memory_id") == "memory-user-001"
    )

    assert "memory summary persisted" in state_fragment.payload["event"]


def test_fetch_cloudwatch_events_uses_boto3_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    class _FakeLogsClient:
        def filter_log_events(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(dict(kwargs))
            if len(calls) == 1:
                return {
                    "events": [_cloudwatch_events()["events"][0]],
                    "nextToken": "token-1",
                }
            return {
                "events": [_cloudwatch_events()["events"][1]],
            }

    class _FakeSession:
        def __init__(self, *, profile_name: str | None, region_name: str | None) -> None:
            assert profile_name == "sandbox"
            assert region_name == "us-east-1"

        def client(self, service_name: str) -> _FakeLogsClient:
            assert service_name == "logs"
            return _FakeLogsClient()

    class _FakeBoto3:
        class session:  # noqa: N801 - mimic boto3 surface
            Session = _FakeSession

    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.live.importlib.import_module",
        lambda name: _FakeBoto3 if name == "boto3" else None,
    )

    events = fetch_cloudwatch_events(
        "/aws/bedrock/agent-runtime/demo",
        aws_profile="sandbox",
        region="us-east-1",
        start_time_ms=1735689600000,
        end_time_ms=1735689700000,
    )

    assert len(events) == 2
    assert calls[0]["logGroupName"] == "/aws/bedrock/agent-runtime/demo"
    assert calls[0]["startTime"] == 1735689600000
    assert calls[0]["endTime"] == 1735689700000
    assert calls[1]["nextToken"] == "token-1"


def test_load_sessions_cloudwatch_filters_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    cloudwatch = _cloudwatch_events()["events"]
    extra = {
        "timestamp": 1735689602000,
        "message": json.dumps(
            {
                "sessionId": "bedrock-session-002",
                "agentId": "agent-999",
                "trace": {
                    "preProcessingTrace": {
                        "traceId": "trace-pre-2",
                        "modelInvocationInput": {"text": "ignore me"},
                    }
                },
            }
        ),
    }

    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.live.fetch_cloudwatch_events",
        lambda *args, **kwargs: [*cloudwatch, extra],
    )

    sessions = load_sessions_cloudwatch(
        "/aws/bedrock/agent-runtime/demo",
        session_id="bedrock-session-001",
    )

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "bedrock-session-001"


def test_load_sessions_cloudwatch_requires_bedrock_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(name: str) -> None:
        raise ImportError(name)

    monkeypatch.setattr("reconstructor.adapters.bedrock.live.importlib.import_module", _boom)

    with pytest.raises(ImportError, match=r"\[bedrock\]"):
        fetch_cloudwatch_events("/aws/bedrock/agent-runtime/demo")


def test_fetch_agent_memory_contents_uses_boto3_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class _FakeRuntimeClient:
        def get_agent_memory(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(dict(kwargs))
            if len(calls) == 1:
                return {
                    "memoryContents": [
                        {
                            "sessionSummary": {
                                "memoryId": "memory-user-001",
                                "sessionId": "prior-session-1",
                                "summaryText": "first summary",
                            }
                        }
                    ],
                    "nextToken": "token-2",
                }
            return {
                "memoryContents": [
                    {
                        "sessionSummary": {
                            "memoryId": "memory-user-001",
                            "sessionId": "prior-session-2",
                            "summaryText": "second summary",
                        }
                    }
                ]
            }

    class _FakeSession:
        def __init__(self, *, profile_name: str | None, region_name: str | None) -> None:
            assert profile_name == "sandbox"
            assert region_name == "us-east-1"

        def client(self, service_name: str) -> _FakeRuntimeClient:
            assert service_name == "bedrock-agent-runtime"
            return _FakeRuntimeClient()

    class _FakeBoto3:
        class session:  # noqa: N801 - mimic boto3 surface
            Session = _FakeSession

    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.live.importlib.import_module",
        lambda name: _FakeBoto3 if name == "boto3" else None,
    )

    contents = fetch_agent_memory_contents(
        "agent-123",
        "support-agent",
        "memory-user-001",
        aws_profile="sandbox",
        region="us-east-1",
        max_items=25,
    )

    assert len(contents) == 2
    assert calls[0]["memoryId"] == "memory-user-001"
    assert calls[0]["memoryType"] == "SESSION_SUMMARY"
    assert calls[0]["maxItems"] == 25
    assert calls[1]["nextToken"] == "token-2"


def test_load_sessions_cloudwatch_attaches_memory_contents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.live.fetch_cloudwatch_events",
        lambda *args, **kwargs: _cloudwatch_events()["events"],
    )
    monkeypatch.setattr(
        "reconstructor.adapters.bedrock.live.fetch_agent_memory_contents",
        lambda *args, **kwargs: [
            {
                "sessionSummary": {
                    "memoryId": "memory-user-001",
                    "sessionId": "prior-session-1",
                    "summaryText": "prior refund handled",
                }
            }
        ],
    )

    sessions = load_sessions_cloudwatch(
        "/aws/bedrock/agent-runtime/demo",
        memory_id="memory-user-001",
    )

    assert sessions[0]["memory_id"] == "memory-user-001"
    assert sessions[0]["memory_contents"][0]["sessionSummary"]["sessionId"] == "prior-session-1"


def test_validate_sessions_complete_rejects_truncated_session() -> None:
    payload = _session_payload()
    payload["trace"] = {
        "preProcessingTrace": {
            "traceId": "trace-pre",
            "eventTime": "2025-01-01T00:00:00Z",
            "modelInvocationInput": {"text": "hello"},
        }
    }

    with pytest.raises(ValueError, match="partial or truncated"):
        validate_sessions_complete([payload])


def test_validate_sessions_complete_accepts_session_summary_as_terminal_signal() -> None:
    payload = _session_payload()
    payload["trace"] = {
        "preProcessingTrace": {
            "traceId": "trace-pre",
            "eventTime": "2025-01-01T00:00:00Z",
            "modelInvocationInput": {"text": "hello"},
        }
    }
    payload["memoryId"] = "memory-user-001"
    payload["sessionSummary"] = {
        "memoryId": "memory-user-001",
        "sessionId": "bedrock-session-001",
        "summaryText": "session completed and summarized",
    }

    validate_sessions_complete([payload])
