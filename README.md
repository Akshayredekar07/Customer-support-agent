# Langie Agent (Customer Support Workflow)

Langie Agent is a staged, auditable customer support workflow built on LangGraph and MCP tools. It orchestrates COMMON (internal/LLM) and ATLAS (external) servers, persists state across stages, and outputs a final structured payload with detailed logs.

## Key Features
- Stage-based orchestration (11 stages) with clear responsibilities
- MCP routing: COMMON for internal LLM/logic, ATLAS for external systems
- Persistent state via MemorySaver, with stage-by-stage audit logs
- Conditional human-in-the-loop (ASK/WAIT)
- LLM-enhanced steps: entity parsing/normalization, semantic KB search, retrieval summarization, scoring with rationale, empathetic response generation
- Deterministic and non-deterministic transitions with explicit routing
- Comprehensive edge case testing framework

## Folder Structure
Top-level layout with descriptions of important files and directories.

```
customer_support_agent/
├─ agent/
│  └─ graph.py                  # LangGraph workflow nodes, routing, and audit logging
├─ clients/
│  ├─ atlas_client.py           # ATLAS client abilities (external-facing/mocked if no API key)
│  └─ common_client.py          # COMMON client abilities (internal logic/LLM-like)
├─ config/
│  ├─ agent_config.json         # Agent nodes, abilities, and routing metadata
│  ├─ workflow_config.json      # Input schema, prompts, and ability-to-MCP mapping
│  ├─ knowledge_base.json       # Demo KB articles used by retrieval
│  ├─ input_detailed.json       # Sample input payload
│  ├─ payment_input.json        # Sample payment issue
│  ├─ ask_demo_delivery.json    # Sample delivery issue
│  ├─ rohit_input.json          # Sample request
│  └─ amit_input.json           # Sample request
├─ mcp_servers/
│  ├─ atlas_tools.py            # ATLAS MCP tool definitions (http_app)
│  └─ common_tools.py           # COMMON MCP tool definitions (http_app)
├─ schemas/
│  └─ agent_state.py            # TypedDict schema for workflow state
├─ start_mcp_servers.py         # Starts COMMON (5001) and ATLAS (5002) MCP servers
├─ frontend.py                  # Simple runner/preview (imports graph)
├─ main.py                      # CLI entrypoint for running the workflow
├─ pyproject.toml               # Project metadata
├─ requirements.txt             # Python dependencies
├─ uv.lock                      # Locked dependency versions
└─ README.md                    # This guide
```

## Setup
Prerequisites: Python 3.10+ recommended.

1) Create and activate a virtual environment, then install dependencies.
```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt
```

2) Optional environment variables (defaults exist):
- `COMMON_MCP_URL` (default `http://localhost:5001/mcp/`)
- `ATLAS_MCP_URL` (default `http://localhost:5002/mcp/`)
- `KB_PATHS` or `KB_PATH` (default `config/knowledge_base.json`)
- `GOOGLE_API_KEY` (only needed if using live Google GenAI in `atlas_client.py`)

If `GOOGLE_API_KEY` is not set, the ATLAS client should be configured to operate in a mock/deterministic mode.

## Running
### Start MCP servers (in a dedicated shell)
```
python start_mcp_servers.py
```
This launches:
- COMMON server on `http://localhost:5001/mcp/`
- ATLAS server on `http://localhost:5002/mcp/`

### Run the workflow
Human-readable output:
```
python main.py --input config/input_detailed.json
```
JSON output with logs:
```
python main.py --input config/input_detailed.json --json
```

### Optional frontend runner
```
python frontend.py
```

## Workflow Stages
1) INTAKE: accept input payload
2) UNDERSTAND: parse request (COMMON), extract entities (ATLAS), fallback entity inference
3) PREPARE: normalize fields (COMMON), enrich records (ATLAS), flags (COMMON), LLM entity normalization (COMMON)
4) ASK: clarification (ATLAS) only if `missing_info` exists; otherwise skipped
5) WAIT: awaits customer reply when ASK ran; otherwise skipped
6) RETRIEVE: generate semantic query (COMMON), KB search (ATLAS), summarize retrieval (COMMON)
7) DECIDE: scoring (COMMON), escalation decision (ATLAS), decision rationale (COMMON)
8) UPDATE: update/close external ticket (ATLAS); status reflects escalation decision
9) CREATE: response generation (COMMON)
10) DO: external API calls and notifications (ATLAS)
11) COMPLETE: finalize and log

## MCP Routing
- COMMON: `parse_request_text`, `normalize_fields`, `add_flags_calculations`, `entity_normalization`, `generate_semantic_query`, `summarize_retrieval`, `solution_evaluation`, `decision_rationale`, `response_generation`
- ATLAS: `extract_entities`, `enrich_records`, `clarify_question`, `extract_answer`, `knowledge_base_search`, `escalation_decision`, `update_ticket`, `close_ticket`, `execute_api_calls`, `trigger_notifications`

## Edge Case Testing
Use provided sample configs to exercise different flows:
- Critical/auth-like: adjust priority and query to test escalation path
- Delivery clarification: ensure `order_number` or delivery identifiers trigger ASK/WAIT
- Payment dispute: ensure `transaction_reference` triggers ASK/WAIT

Run examples:
```
python main.py --input config/ask_demo_delivery.json --json
python main.py --input config/payment_input.json --json
```

## Configuration Overview
- `config/agent_config.json`: node catalog and abilities metadata
- `config/workflow_config.json`: input schema, stage prompts, and ability-to-MCP mapping
- `config/knowledge_base.json`: retrieval corpus used by `knowledge_base_search`
- `config/*.json`: input examples you can customize

## Troubleshooting
- Credentials error for Google GenAI: set `GOOGLE_API_KEY` or enable mock mode in `clients/atlas_client.py`.
- ASK stage not triggered: ensure `missing_info` is produced in UNDERSTAND/PREPARE.
- Empty KB result: update `config/knowledge_base.json` or set `KB_PATHS` to additional KB files.
- Import errors: verify virtual environment activation and dependency installation.

## License
Proprietary / Internal use
