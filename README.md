# Langie Agent (Customer Support Workflow)

Langie Agent is a staged, auditable customer support workflow built on LangGraph and MCP tools. It orchestrates COMMON (internal/LLM) and ATLAS (external) servers, persists state across stages, and outputs a final structured payload with detailed logs.

## Key Features
- Stage-based orchestration (11 stages) with clear responsibilities
- MCP routing: COMMON for internal LLM/logic, ATLAS for external systems
- Persistent state via MemorySaver, with stage-by-stage audit logs
- Conditional human-in-the-loop (ASK/WAIT)
- LLM-enhanced steps: entity parsing/normalization, semantic KB search, retrieval summarization, scoring with rationale, empathetic response generation
- Deterministic and non-deterministic transitions with explicit routing

## Folder Structure
- agent/
  - graph.py: LangGraph workflow and node implementations (stages, routing, logs)
  - langie_agent.py: agent stub (not required for CLI)
  - abilities.py: placeholder (abilities implemented via MCP clients)
- clients/
  - mcp_client.py: MCP integration and robust fallbacks for all abilities
- config/
  - workflow_config.json: input schema, stage definitions, prompts, ability-to-MCP mapping
- schemas/
  - agent_state.py: TypedDict schema for workflow state
- main.py: CLI runner (prints final JSON or human-readable output)
- mcp_servers/: reference tool shapes (use external servers if available)

## Workflow Stages
1) INTAKE: accept input payload
2) UNDERSTAND: parse request (COMMON), extract entities (ATLAS), fallback entity inference
3) PREPARE: normalize fields (COMMON), enrich records (ATLAS), flags (COMMON), LLM entity normalization (COMMON)
4) ASK: LLM clarification (ATLAS) only if missing_info exists; otherwise Skipped
5) WAIT: Await customer reply if ASK was needed; otherwise Skipped
6) RETRIEVE: generate semantic query (COMMON), KB search (ATLAS), LLM summarize retrieval (COMMON)
7) DECIDE: LLM-like scoring (COMMON), escalation path (ATLAS), LLM decision rationale (COMMON)
8) UPDATE: update/close external ticket (ATLAS); status reflects escalate
9) CREATE: LLM response generation (COMMON)
10) DO: external API calls + notifications (ATLAS)
11) COMPLETE: finalize and log

## MCP Routing
- COMMON (internal): parse_request_text, normalize_fields, add_flags_calculations, entity_normalization, generate_semantic_query, summarize_retrieval, solution_evaluation, decision_rationale, response_generation
- ATLAS (external): extract_entities, enrich_records, clarify_question, extract_answer, knowledge_base_search, escalation_decision, update_ticket, close_ticket, execute_api_calls, trigger_notifications

## Setup
Prerequisites: Python 3.10+.

1) Create a virtual environment and install dependencies (example):
```
pip install -r ../requirements.txt
```

2) Optional: Configure MCP endpoints via environment variables (fallback defaults used if unset):
```
COMMON_MCP_URL, ATLAS_MCP_URL
```

## Run
Run and print final JSON with logs:
```
python main.py --json
```

Optional input overrides via environment variables:
- INPUT_CUSTOMER_NAME
- INPUT_EMAIL
- INPUT_QUERY
- INPUT_PRIORITY (Low/Medium/High/Critical)
- INPUT_TICKET_ID
- CUSTOMER_RESPONSE (used to resume WAIT)

## Output (Summary)
- final_payload:
  - input echoes: ticket_id, customer_name, email, query, priority
  - entities: structured entities (issue_type, product, ...)
  - normalized_fields: priority_score, sla_risk, ticket_status
  - retrieved_info: KB evidence
  - retrieval_summary: LLM-generated summary of KB content
  - decision: solution_score, escalated, assigned_to, reason (LLM rationale)
  - response: LLM-generated customer reply
  - actions_taken: operational steps performed
- logs: stage-by-stage audit with abilities executed and MCP client used

## Configuration
See `config/workflow_config.json`
- input_schema: validated input keys
- stages: name, mode (deterministic/non_deterministic), abilities, prompts
- ability_to_mcp: explicit mapping of abilities to COMMON or ATLAS

## How LLM Is Used
- UNDERSTAND: parsing (COMMON), extraction (ATLAS)
- PREPARE: entity normalization (COMMON)
- RETRIEVE: semantic query + summarization (COMMON)
- DECIDE: scoring and rationale (COMMON)
- ASK: clarification question (ATLAS) when needed
- CREATE: final response generation (COMMON)

If an external LLM client is unavailable, intelligent fallbacks in `mcp_client.py` produce consistent demo outputs.

## Troubleshooting
- No output / import errors: ensure dependencies installed and Python ≥ 3.10
- ASK not triggered: ensure `missing_info` is produced in UNDERSTAND/PREPARE
- Empty entities: extractor returns nothing → fallback infers from query
- KB empty: fallback injects a minimal helpful hint
- Status mismatch: status is derived from `escalate` in UPDATE

## License
Proprietary / Internal use
