"""Pinned 2.1.325 scripted-probe wire shape, never execution authority.

PR6302, reviewed profile v2/P3, 2026-11-21. This pure module reads no files,
normalizes no evidence and grants no tools. Callers retain semantic/effect checks.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import re
from uuid import UUID

from . import native_model_aliases
from . import native_shared_permission_protocol as protocol


VERSION = '2.1.325 (Claude Code)'
INIT_VERSION = '2.1.325'
EXECUTABLE_SHA256 = '84590fefe6338be9087f5814b61f9a54c5f21524163a4c127cb5a808e31009f2'
COMPANION_SHA256 = '3cc4badc14f30c968f501cb860c00515691e8ec0de7f2c5cdd21f62fb484094a'

# reviewed-literals:begin
_REVIEWED = json.loads(r'''
{
  "ack": {
    "response": {
      "pending_permission_requests": [],
      "pending_user_dialog_requests": [],
      "request_id": "d4d_initialize_v1",
      "response": {
        "account": {
          "apiKeySource": "ANTHROPIC_API_KEY",
          "apiProvider": "firstParty",
          "tokenSource": "claude.ai"
        },
        "agents": [
          {
            "description": "Catch-all for any task that doesn't fit a more specific agent. FleetView's default when no agent name is typed.",
            "name": "claude"
          },
          {
            "description": "Fast read-only search agent for locating code. Use it to find files by pattern (eg. \"src/components/**/*.tsx\"), grep for symbols or keywords (eg. \"API endpoints\"), or answer \"where is X defined / which files reference Y.\" Do NOT use it for code review, design-doc auditing, cross-file consistency checks, or open-ended analysis \u2014 it reads excerpts rather than whole files and will miss content past its read window. When calling, specify search breadth: \"quick\" for a single targeted lookup, \"medium\" for moderate exploration, or \"very thorough\" to search across multiple locations and naming conventions.",
            "model": "inherit",
            "name": "Explore"
          },
          {
            "description": "General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks. When you are searching for a keyword or file and are not confident that you will find the right match in the first few tries use this agent to perform the search for you.",
            "name": "general-purpose"
          },
          {
            "description": "Software architect agent for designing implementation plans. Use this when you need to plan the implementation strategy for a task. Returns step-by-step plans, identifies critical files, and considers architectural trade-offs.",
            "model": "inherit",
            "name": "Plan"
          }
        ],
        "analytics_disabled": true,
        "auth_conflict": {
          "api_key_source": "ANTHROPIC_API_KEY",
          "token_source": "claude.ai"
        },
        "available_output_styles": [
          "default",
          "Proactive",
          "Concise",
          "Explanatory",
          "Learning"
        ],
        "capabilities": [
          "ui_surface_v1",
          "mcp_call_result_not_for_model_v1",
          "mcp_call_check_permissions_v1",
          "voice_call_talk_line_v1",
          "ui_pane_widget_v1",
          "reload_plugins_refuse_if_busy_v1"
        ],
        "claude_code_version": "2.1.325",
        "commands": [],
        "current_permission_mode": "dontAsk",
        "fast_mode_disabled_reason": "sdk_opt_in_required",
        "fast_mode_state": "off",
        "feedback_mode": {
          "kind": "disabled"
        },
        "hook_on_failure_supported": true,
        "hooks_applied": true,
        "ide_rc_auto_enable_gate": false,
        "models": [
          {
            "description": "Use the default model (currently Opus 5.5) \u00b7 $4/$20 per Mtok",
            "displayName": "Default (recommended)",
            "resolvedModel": "claude-opus-5-5",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsFastMode": true,
            "supportsThinkingOff": false,
            "value": "default"
          },
          {
            "description": "Opus 5.5 \u00b7 Best for everyday, complex tasks \u00b7 $4/$20 per Mtok",
            "displayName": "Opus",
            "resolvedModel": "claude-opus-5-5",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsFastMode": true,
            "supportsThinkingOff": false,
            "value": "opus"
          },
          {
            "description": "Fable 5.2 \u00b7 Most capable for your hardest and longest-running tasks \u00b7 $8/$40 per Mtok",
            "displayName": "Fable",
            "resolvedModel": "claude-fable-5-2",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsFastMode": true,
            "supportsThinkingOff": false,
            "value": "fable"
          },
          {
            "description": "Sonnet 5.5 \u00b7 Efficient for routine tasks \u00b7 $2/$10 per Mtok",
            "displayName": "Sonnet",
            "resolvedModel": "claude-sonnet-5-5",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsThinkingOff": false,
            "value": "sonnet"
          },
          {
            "description": "Haiku 5.5 \u00b7 Fastest for quick answers \u00b7 $0.10/$0.50 per Mtok ($0.50/$2.50 for prompts over 100k)",
            "displayName": "Haiku",
            "resolvedModel": "claude-haiku-5-5",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsThinkingOff": false,
            "value": "haiku"
          },
          {
            "description": "Newer version available \u00b7 select Opus for Opus 5.5",
            "displayName": "Opus 5",
            "resolvedModel": "claude-opus-5",
            "supportedEffortLevels": [
              "low",
              "medium",
              "high",
              "xhigh",
              "max"
            ],
            "supportsAdaptiveThinking": true,
            "supportsAutoMode": true,
            "supportsEffort": true,
            "supportsFastMode": true,
            "supportsThinkingOff": true,
            "value": "claude-opus-5[1m]"
          }
        ],
        "other_hook_ask_outranks_host": true,
        "output_style": "default",
        "pid": 50580,
        "remote_control_auto_connect_default": false,
        "remote_control_auto_enable": false,
        "remote_control_auto_on_by_default": false,
        "remote_control_available": false,
        "session_state": "idle",
        "user_output_styles_dir": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/config_root/output-styles"
      },
      "subtype": "success"
    },
    "type": "control_response"
  },
  "assistant_call": {
    "message": {
      "content": [
        {
          "id": "source_read",
          "input": {
            "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/data/preprocessed/concatenated/CHORUS_preprocessed.txt"
          },
          "name": "Read",
          "type": "tool_use"
        }
      ],
      "context_management": null,
      "id": "d4d_permission_0",
      "model": "claude-opus-5",
      "role": "assistant",
      "stop_reason": null,
      "stop_sequence": null,
      "type": "message",
      "usage": {
        "input_tokens": 0,
        "output_tokens": 0
      }
    },
    "parent_tool_use_id": null,
    "session_id": "7528d84c-c240-4459-a64e-13e547ae2907",
    "timestamp": "2026-11-21T14:07:38.161Z",
    "type": "assistant",
    "uuid": "ac0f341f-5c7d-4ccf-881e-bdd1985e5d1b"
  },
  "assistant_completion": {
    "message": {
      "content": [
        {
          "text": "OFFLINE_COMPLETE",
          "type": "text"
        }
      ],
      "context_management": null,
      "id": "d4d_permission_19",
      "model": "claude-opus-5",
      "role": "assistant",
      "stop_reason": null,
      "stop_sequence": null,
      "type": "message",
      "usage": {
        "input_tokens": 0,
        "output_tokens": 0
      }
    },
    "parent_tool_use_id": null,
    "session_id": "7528d84c-c240-4459-a64e-13e547ae2907",
    "timestamp": "2026-11-21T14:07:43.612Z",
    "type": "assistant",
    "uuid": "c46337fa-79d5-49d3-b9eb-aa6570028366"
  },
  "bash_result": {
    "message": {
      "content": [
        {
          "content": "{\"argv\":[\"advance\",\"--registration\",\"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/packets/CHORUS/input-prefix/selection.json\"],\"d4d_shared_permission_stub\":\"stage\"}",
          "is_error": false,
          "tool_use_id": "stage_receipt",
          "type": "tool_result"
        }
      ],
      "role": "user"
    },
    "parent_tool_use_id": null,
    "session_id": "7528d84c-c240-4459-a64e-13e547ae2907",
    "timestamp": "2026-11-21T14:07:38.888Z",
    "tool_result_meta": [
      {
        "id": "stage_receipt",
        "permission_decision": {
          "decision": "accept",
          "reason_type": "rule",
          "source": "config"
        }
      }
    ],
    "tool_use_result": {
      "interrupted": false,
      "isImage": false,
      "noOutputExpected": false,
      "stderr": "",
      "stdout": "{\"argv\":[\"advance\",\"--registration\",\"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/packets/CHORUS/input-prefix/selection.json\"],\"d4d_shared_permission_stub\":\"stage\"}"
    },
    "type": "user",
    "uuid": "5d4ebfed-1eab-4b46-a849-148c749d8487"
  },
  "init": {
    "additional_directories": [],
    "agents": [
      "claude",
      "Explore",
      "general-purpose",
      "Plan"
    ],
    "analytics_disabled": true,
    "apiKeySource": "ANTHROPIC_API_KEY",
    "capabilities": [
      "interrupt_receipt_v1",
      "interrupt_cancel_queued_v1",
      "interrupt_send_now_v1",
      "interrupt_requeue_taken_v1",
      "msg_lifecycle_v1",
      "request_marker_lists_v1",
      "ask_user_question_unanswered_v1",
      "lifecycle_wakeup_source_v1",
      "sdk_mcp_tools_list_changed",
      "sdk_mcp_manifests",
      "mcp_read_resource_v1",
      "mcp_tool_ui_meta_v1",
      "ui_surface_v1",
      "mcp_call_result_not_for_model_v1",
      "mcp_call_check_permissions_v1",
      "voice_call_talk_line_v1",
      "withdrawn_files_note_v2",
      "ui_pane_widget_v1",
      "reload_plugins_refuse_if_busy_v1"
    ],
    "claude_code_version": "2.1.325",
    "cwd": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae",
    "fast_mode_disabled_reason": "sdk_opt_in_required",
    "fast_mode_state": "off",
    "mcp_servers": [],
    "model": "claude-opus-5",
    "original_cwd": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae",
    "output_style": "default",
    "per_turn_effort_active": false,
    "permissionMode": "dontAsk",
    "plugins": [
      {
        "name": "cc-plugin-agents-md",
        "path": "builtin",
        "source": "cc-plugin-agents-md\u0040builtin"
      },
      {
        "name": "cc-plugin-privacy",
        "path": "builtin",
        "source": "cc-plugin-privacy\u0040builtin"
      },
      {
        "name": "cc-plugin-plugin-authoring",
        "path": "builtin",
        "source": "cc-plugin-plugin-authoring\u0040builtin"
      }
    ],
    "product_feedback_disabled": true,
    "session_id": "7528d84c-c240-4459-a64e-13e547ae2907",
    "skills": [],
    "slash_commands": [],
    "subtype": "init",
    "tools": [
      "Bash",
      "Read",
      "Write"
    ],
    "type": "system",
    "ultrathink_available": false,
    "ultrathink_typed_raises": false,
    "uuid": "4e07b406-7c82-44bb-93bc-bf9531fee4c4",
    "view_mode": "default"
  },
  "terminal": {
    "api_error_status": null,
    "duration_api_ms": 852,
    "duration_ms": 6207,
    "fast_mode_disabled_reason": "sdk_opt_in_required",
    "fast_mode_state": "off",
    "first_content_frame_ms": 753,
    "is_error": false,
    "modelUsage": {
      "claude-opus-5": {
        "cacheCreationEphemeral1hInputTokens": 0,
        "cacheCreationEphemeral5mInputTokens": 0,
        "cacheCreationInputTokens": 0,
        "cacheReadInputTokens": 0,
        "canonicalModel": "claude-opus-5",
        "contextWindow": 1000000,
        "costBasis": "list",
        "costUSD": 0,
        "inputTokens": 0,
        "maxOutputTokens": 64000,
        "outputTokens": 0,
        "provider": "firstParty",
        "thinkingTokens": 0,
        "webSearchRequests": 0
      }
    },
    "model_usage_since_last_result": {
      "claude-opus-5": {
        "cacheCreationEphemeral1hInputTokens": 0,
        "cacheCreationEphemeral5mInputTokens": 0,
        "cacheCreationInputTokens": 0,
        "cacheReadInputTokens": 0,
        "canonicalModel": "claude-opus-5",
        "contextWindow": 1000000,
        "costBasis": "list",
        "costUSD": 0,
        "inputTokens": 0,
        "maxOutputTokens": 64000,
        "outputTokens": 0,
        "provider": "firstParty",
        "thinkingTokens": 0,
        "webSearchRequests": 0
      }
    },
    "num_turns": 20,
    "permission_denials": [
      {
        "tool_input": {
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/requests/000001.json"
        },
        "tool_name": "Read",
        "tool_use_id": "request_receipt_read"
      },
      {
        "tool_input": {
          "content": "{\"cursor\":{\"kind\":\"receipt\",\"ordinal\":1,\"target_id\":\"receipt\"},\"domain\":\"native_shared_permission_projection_v1\",\"kind\":\"synthetic_permission_answer\",\"recipe_sha256\":\"40cbe58f637c3701b94dc2f0eb7a26fe4aa336c3335d3bdaf922779ebf78a85e\",\"selection_sha256\":\"20d75c5dd2671966b840094f78f2578f085edd466d50b5be748275df0f3318f4\",\"session_id\":\"7528d84c-c240-4459-a64e-13e547ae2907\"}\n",
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/responses/000001.bin"
        },
        "tool_name": "Write",
        "tool_use_id": "response_receipt_write"
      },
      {
        "tool_input": {
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/requests/000002.json"
        },
        "tool_name": "Read",
        "tool_use_id": "request_worker_read"
      },
      {
        "tool_input": {
          "content": "{\"cursor\":{\"kind\":\"worker\",\"ordinal\":2,\"target_id\":\"worker-000001\"},\"domain\":\"native_shared_permission_projection_v1\",\"kind\":\"synthetic_permission_answer\",\"recipe_sha256\":\"40cbe58f637c3701b94dc2f0eb7a26fe4aa336c3335d3bdaf922779ebf78a85e\",\"selection_sha256\":\"20d75c5dd2671966b840094f78f2578f085edd466d50b5be748275df0f3318f4\",\"session_id\":\"7528d84c-c240-4459-a64e-13e547ae2907\"}\n",
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/responses/000002.bin"
        },
        "tool_name": "Write",
        "tool_use_id": "response_worker_write"
      },
      {
        "tool_input": {
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/requests/000003.json"
        },
        "tool_name": "Read",
        "tool_use_id": "request_omission_read"
      },
      {
        "tool_input": {
          "content": "{\"cursor\":{\"kind\":\"omission\",\"ordinal\":3,\"target_id\":\"omission\"},\"domain\":\"native_shared_permission_projection_v1\",\"kind\":\"synthetic_permission_answer\",\"recipe_sha256\":\"40cbe58f637c3701b94dc2f0eb7a26fe4aa336c3335d3bdaf922779ebf78a85e\",\"selection_sha256\":\"20d75c5dd2671966b840094f78f2578f085edd466d50b5be748275df0f3318f4\",\"session_id\":\"7528d84c-c240-4459-a64e-13e547ae2907\"}\n",
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/responses/000003.bin"
        },
        "tool_name": "Write",
        "tool_use_id": "response_omission_write"
      },
      {
        "tool_input": {
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/requests/000004.json"
        },
        "tool_name": "Read",
        "tool_use_id": "request_integration_read"
      },
      {
        "tool_input": {
          "content": "{\"cursor\":{\"kind\":\"integration\",\"ordinal\":4,\"target_id\":\"integration\"},\"domain\":\"native_shared_permission_projection_v1\",\"kind\":\"synthetic_permission_answer\",\"recipe_sha256\":\"40cbe58f637c3701b94dc2f0eb7a26fe4aa336c3335d3bdaf922779ebf78a85e\",\"selection_sha256\":\"20d75c5dd2671966b840094f78f2578f085edd466d50b5be748275df0f3318f4\",\"session_id\":\"7528d84c-c240-4459-a64e-13e547ae2907\"}\n",
          "file_path": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission/settled/effect_root/responses/000004.bin"
        },
        "tool_name": "Write",
        "tool_use_id": "response_integration_write"
      },
      {
        "tool_input": {
          "command": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/.venv/bin/python -c 'print(\"D4D_UNREGISTERED_PERMISSION_PROBE\")'"
        },
        "tool_name": "Bash",
        "tool_use_id": "arbitrary_python"
      },
      {
        "tool_input": {
          "command": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/.venv/bin/python -m data_sheets_schema.source_attribution_preflight --report data/d4d_concatenated/claudecode_direct_core/post-merge-native/CHORUS_reconciliation.md --record data/d4d_concatenated/claudecode_direct/post-merge-native/CHORUS_d4d.yaml --bundle /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/data/preprocessed/chunks/CHORUS_chunks.yaml --protocol-version 7 --source-manifest /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/data/preprocessed/source_manifest.yaml --project CHORUS --d4d-unregistered-permission-argument"
        },
        "tool_name": "Bash",
        "tool_use_id": "modified_draft"
      },
      {
        "tool_input": {
          "command": "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-724f6b349bae/.venv/bin/python -m data_sheets_schema.native_shared_stage advance --registration /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-fastpath-724f6b349bae-r4/packets/CHORUS/input-prefix/selection.json --worker d4d-unregistered"
        },
        "tool_name": "Bash",
        "tool_use_id": "modified_stage"
      }
    ],
    "queued_turn_count": 0,
    "result": "OFFLINE_COMPLETE",
    "result_index": 0,
    "safety_stops": 0,
    "session_id": "7528d84c-c240-4459-a64e-13e547ae2907",
    "stop_reason": "end_turn",
    "subagent_stats": {
      "by_type": {},
      "completed": 0,
      "failed": 0,
      "killed": {
        "parent": 0,
        "system": 0,
        "user": 0
      },
      "max_depth": 0,
      "refused": {
        "budget": 0,
        "concurrency_limit": 0,
        "depth_limit": 0
      },
      "requested": {
        "background": 0,
        "foreground": 0,
        "unset": 0
      },
      "spawned": 0,
      "spawned_by_subagents": 0,
      "started_in_background": 0
    },
    "subtype": "success",
    "terminal_reason": "completed",
    "time_to_request_ms": 747,
    "total_cost_usd": 0,
    "ttft_ms": 753,
    "ttft_stream_ms": 753,
    "type": "result",
    "usage": {
      "cache_creation": {
        "ephemeral_1h_input_tokens": 0,
        "ephemeral_5m_input_tokens": 0
      },
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0,
      "fallback_credit": null,
      "inference_geo": "",
      "input_tokens": 0,
      "iterations": [],
      "output_tokens": 0,
      "output_tokens_details": {
        "thinking_tokens": 0
      },
      "server_tool_use": {
        "web_fetch_requests": 0,
        "web_search_requests": 0
      },
      "service_tier": "standard",
      "speed": "standard"
    },
    "uuid": "e4dd9ade-de18-4a48-a984-88d9806cd0c6"
  }
}
''')
# reviewed-literals:end


def _need(condition, message):
    if not condition:
        raise ValueError('native permission wire: ' + message)


def _same(left, right):
    return json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _keys(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), label + ' has missing or unknown fields')


def _uuid(value, label):
    _need(type(value) is str, label + ' is not a UUID')
    try:
        valid = str(UUID(value)) == value
    except ValueError:
        valid = False
    _need(valid, label + ' is not a canonical UUID')
    return value


def _timestamp(value):
    _need(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)', value),
          'timestamp is not UTC')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('native permission wire: invalid timestamp') from exc
    _need(parsed.utcoffset() == timedelta(0), 'timestamp is not UTC')


def _literals(actual, template, bindings, label):
    """Compare reviewed literals plus separately checked dynamic bindings."""
    _keys(actual, template, label)
    for key, literal in template.items():
        _need(_same(actual[key], bindings[key] if key in bindings else literal), label + ' differs: ' + key)


def profile(runtime):
    executable = runtime['executable']
    return (executable.get('version'), executable.get('init_version'), executable.get('sha256')) == (
        VERSION, INIT_VERSION, EXECUTABLE_SHA256)


def begin_trace(events, clean, runtime, launch, policy, *, additional_directories):
    _need(profile(runtime), 'unreviewed executable identity')
    return TraceWire(events, clean, runtime, launch, policy, additional_directories)


class TraceWire:
    """Trace-local identity checks over original parsed frames and raw indices."""

    def __init__(self, events, clean, runtime, launch, policy, additional_directories):
        _need(len(events) >= 3 and len(clean) >= 2, 'initialization is incomplete')
        self.runtime, self.launch, self.policy = runtime, launch, policy
        self.aliases = native_model_aliases.model_aliases(runtime)
        self.frame_ids, self.callback_ids = set(), set()
        self.prompt_id = None
        self.offset = 3
        ui, ack, init = events[:3]
        self.session = _uuid(init.get('session_id'), 'session')
        _keys(ui, {'type', 'subtype', 'event', 'uuid', 'session_id'}, 'UI prefix')
        _need(ui['type'] == 'system' and ui['subtype'] == 'ui_invalidate' and ui['event'] == 'ui.render',
              'unknown leading frame')
        self._scope(ui)
        self._ack(ack)
        _need(_same(clean[0], {'kind': 'initialize_sent', 'policy_sha256': protocol.policy_digest(policy),
              'frame': protocol.initialize_frame(policy['pretool_control'])}), 'initialization sent differs')
        _need(_same(clean[1], {'kind': 'initialize_ack', 'frame': ack}), 'ack/control join differs')
        self._scope(init)
        _need(type(additional_directories) is list, 'directory grant is not independently specified')
        _literals(init, _REVIEWED['init'], {'cwd': launch['cwd'], 'original_cwd': launch['cwd'],
            'session_id': self.session, 'uuid': init['uuid'], 'model': native_model_aliases.reported_model(self.aliases),
            'additional_directories': additional_directories}, 'init')

    def _scope(self, event, *, timestamp=False):
        _need(event.get('session_id') == self.session and event.get('parent_tool_use_id') is None,
              'frame session or parent scope differs')
        identity = _uuid(event.get('uuid'), 'frame identity')
        _need(identity not in self.frame_ids, 'duplicate frame identity')
        self.frame_ids.add(identity)
        native_model_aliases.require_frame_models(event, self.aliases)
        if timestamp:
            _timestamp(event.get('timestamp'))

    def _ack(self, ack):
        _keys(ack, {'type', 'response'}, 'ack')
        _need(ack['type'] == 'control_response', 'ack type differs')
        response = ack['response']
        _keys(response, _REVIEWED['ack']['response'], 'ack response')
        payload = response.get('response')
        _keys(payload, _REVIEWED['ack']['response']['response'], 'ack payload')
        pid = payload['pid']
        _need(type(pid) is int and pid > 0, 'ack PID is not a positive integer')
        wanted_payload = deepcopy(_REVIEWED['ack']['response']['response'])
        wanted_payload.update(pid=pid, user_output_styles_dir=self.launch['config_root'] + '/output-styles')
        _literals(response, _REVIEWED['ack']['response'], {
            'request_id': protocol.initialization_id(), 'response': wanted_payload}, 'ack response')

    def _assistant(self, event, content, ordinal):
        _keys(event, _REVIEWED['assistant_call'], 'assistant envelope')
        self._scope(event, timestamp=True)
        _need(event['type'] == 'assistant', 'assistant type differs')
        _literals(event['message'], _REVIEWED['assistant_call']['message'], {
            'id': 'd4d_permission_' + str(ordinal), 'model': self.aliases['returned'], 'content': content},
            'assistant message')

    def call(self, event, case, ordinal):
        self._assistant(event, [{'type': 'tool_use', 'id': case['id'], 'name': case['tool'], 'input': case['input']}], ordinal)

    def completion(self, event, ordinal):
        self._assistant(event, [{'type': 'text', 'text': 'OFFLINE_COMPLETE'}], ordinal)

    def callback(self, event, case):
        _keys(event, {'type', 'request_id', 'request'}, 'callback')
        identity = _uuid(event['request_id'], 'callback identity')
        _need(identity not in self.callback_ids and identity != protocol.initialization_id(), 'duplicate callback identity')
        self.callback_ids.add(identity)
        request = event['request']
        _keys(request, {'subtype', 'callback_id', 'input', 'tool_use_id'}, 'callback request')
        data = request['input']
        _keys(data, {'session_id', 'transcript_path', 'cwd', 'prompt_id', 'permission_mode', 'effort',
                     'hook_event_name', 'tool_name', 'tool_input', 'tool_use_id'}, 'callback input')
        prompt = _uuid(data['prompt_id'], 'prompt identity')
        if self.prompt_id is None:
            self.prompt_id = prompt
        _need(prompt == self.prompt_id, 'prompt identity changed')
        cwd = self.launch['cwd']
        _need(type(cwd) is str and re.fullmatch(r'/[A-Za-z0-9/-]+', cwd), 'unsupported project cwd encoding')
        transcript = self.launch['config_root'] + '/projects/' + cwd.replace('/', '-') + '/' + self.session + '.jsonl'
        wanted = {'type': 'control_request', 'request_id': identity, 'request': {'subtype': 'hook_callback',
            'callback_id': self.policy['pretool_control']['callback_id'], 'tool_use_id': case['id'], 'input': {
                'session_id': self.session, 'transcript_path': transcript, 'cwd': cwd, 'prompt_id': self.prompt_id,
                'permission_mode': 'dontAsk', 'effort': {'level': self.runtime['effort']}, 'hook_event_name': 'PreToolUse',
                'tool_name': case['tool'], 'tool_input': case['input'], 'tool_use_id': case['id']}}}
        _need(_same(event, wanted), 'callback differs from selected case and launch')

    def result(self, event, case, classification):
        _keys(event, {'type', 'message', 'parent_tool_use_id', 'session_id', 'uuid', 'timestamp',
                      'tool_use_result', 'tool_result_meta'}, 'result envelope')
        self._scope(event, timestamp=True)
        _need(event['type'] == 'user', 'result type differs')
        _keys(event['message'], {'role', 'content'}, 'result message')
        content = event['message']['content']
        _need(event['message']['role'] == 'user' and type(content) is list and len(content) == 1,
              'result message lacks one user result')
        denied = case['mode'] == 'native_denied'
        item = content[0]
        keys = {'type', 'tool_use_id', 'content'}
        if case['tool'] == 'Bash' or denied:
            keys.add('is_error')
        elif type(item) is dict and 'is_error' in item and case['tool'] == 'Write':
            keys.add('is_error')
        _keys(item, keys, 'result block')
        _need(item['type'] == 'tool_result' and item['tool_use_id'] == case['id']
              and item.get('is_error', False) is denied, 'result identity or success differs')
        annotation = {'id': case['id'], 'permission_decision': {
            'decision': 'reject' if denied else 'accept', 'source': 'hook' if denied else 'config',
            'reason_type': 'hook' if denied else 'rule'}}
        if denied:
            _need(case['tool'] == 'Bash', 'only derived Bash denials are supported')
            annotation['non_execution_kind'] = 'permission-rule'
            text = 'PreToolUse:Bash hook error: Outside the registered tool policy: ' + classification[1]
            _need(item['content'] == text and event['tool_use_result'] == 'Error: ' + text,
                  'denied Bash wrapper or basis differs')
        elif case['tool'] == 'Bash':
            metadata = event['tool_use_result']
            _literals(metadata, _REVIEWED['bash_result']['tool_use_result'], {'stdout': metadata.get('stdout')},
                      'successful Bash metadata')
            _need(type(metadata['stdout']) is str, 'successful Bash stdout is not text')
        elif case['tool'] == 'Read':
            _keys(event['tool_use_result'], {'type', 'file'}, 'Read metadata')
            _need(event['tool_use_result']['type'] == 'text', 'Read metadata type differs')
        _need(_same(event['tool_result_meta'], [annotation]), 'result annotation differs')

    def terminal(self, event, cases):
        template = _REVIEWED['terminal']
        _keys(event, template, 'terminal')
        self._scope(event)
        metrics = ('duration_api_ms', 'duration_ms', 'ttft_ms', 'ttft_stream_ms',
                   'time_to_request_ms', 'first_content_frame_ms')
        for key in metrics:
            _need(type(event[key]) is int and event[key] >= 0, 'terminal timing is not a nonnegative integer')
        model = native_model_aliases.reported_model(self.aliases)
        observed_accounting = template['modelUsage']['claude-opus-5']
        wanted_accounting = deepcopy(observed_accounting)
        wanted_accounting['canonicalModel'] = model
        denied = [{'tool_name': case['tool'], 'tool_use_id': case['id'], 'tool_input': case['input']}
                  for case in cases if case['mode'] == 'native_denied']
        bindings = {key: event[key] for key in metrics}
        bindings.update(session_id=self.session, uuid=event['uuid'], num_turns=len(cases) + 1,
            permission_denials=denied, modelUsage={model: wanted_accounting},
            model_usage_since_last_result={model: wanted_accounting})
        _literals(event, template, bindings, 'terminal')
        native_model_aliases.require_model_usage(event, self.aliases)

    def permission_denied(self, event, case):
        """Diagnostic-only restricted Read; qualifying consumers never call this."""
        _need(case['tool'] == 'Read', 'boundary diagnostic is not a Read')
        _keys(event, {'type', 'subtype', 'tool_name', 'tool_use_id', 'decision_reason_type',
                      'decision_reason', 'message', 'uuid', 'session_id'}, 'restricted Read denial')
        self._scope(event)
        text = (case['input']['file_path'] + ' is outside ' + self.launch['cwd']
                + '; --restricted confines the file tools to the working directory.')
        wanted = {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Read', 'tool_use_id': case['id'],
            'decision_reason_type': 'other', 'decision_reason': '--restricted: path outside the working directory',
            'message': text, 'uuid': event['uuid'], 'session_id': self.session}
        _need(_same(event, wanted), 'restricted Read denial differs')

    def restricted_read_result(self, event, case):
        """Diagnostic-only exact native rejection, never qualifying Read success."""
        _need(case['tool'] == 'Read', 'boundary diagnostic is not a Read')
        _keys(event, {'type', 'message', 'parent_tool_use_id', 'session_id', 'uuid', 'timestamp',
                      'tool_use_result', 'tool_result_meta'}, 'restricted Read result')
        self._scope(event, timestamp=True)
        text = (case['input']['file_path'] + ' is outside ' + self.launch['cwd']
                + '; --restricted confines the file tools to the working directory.')
        wanted = {'type': 'user', 'parent_tool_use_id': None, 'session_id': self.session,
            'uuid': event['uuid'], 'timestamp': event['timestamp'], 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': case['id'], 'is_error': True, 'content': text}]},
            'tool_use_result': 'Error: ' + text, 'tool_result_meta': [{'id': case['id'],
                'non_execution_kind': 'permission-rule', 'permission_decision': {
                    'decision': 'reject', 'source': 'config', 'reason_type': 'other'}}]}
        _need(_same(event, wanted), 'restricted Read result differs')
