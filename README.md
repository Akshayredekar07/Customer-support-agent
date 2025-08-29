
# **Langie Agent (Customer Support Workflow)**

Langie Agent is a staged, auditable customer support workflow built on **LangGraph** and **MCP tools**.
It orchestrates **COMMON (internal/LLM)** and **ATLAS (external)** servers, persists state across stages, and outputs a final structured payload with detailed logs.

**Key Features**

* **Stage-based orchestration** (11 stages) with clear responsibilities
* **MCP routing**: COMMON for internal LLM/logic, ATLAS for external systems
* **Persistent state** via MemorySaver, with stage-by-stage audit logs
* **Conditional human-in-the-loop** (ASK / WAIT)
* **LLM-enhanced steps**: entity parsing, normalization, semantic KB search, retrieval summarization, scoring with rationale, empathetic response generation
* **Deterministic + non-deterministic transitions** with explicit routing
* **Comprehensive edge case testing framework**

**Folder Structure**

Top-level layout with descriptions of important files and directories:

```sh
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

**Setup**

**Prerequisites**: Python 3.10+ recommended.

1. **Create and activate a virtual environment**, then install dependencies:

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell
pip install -r requirements.txt
```

2. **Set environment variables**

* Preferred: use a `.env` file at the project root.
* Copy the example file and fill in your own keys/URLs:

```bash
# Windows (PowerShell)
Copy-Item env_example.txt .env

# macOS/Linux
cp env_example.txt .env
```

Open `.env` and replace placeholders with your values:

```
GOOGLE_API_KEY=your_google_api_key
COMMON_MCP_URL=http://localhost:5001/mcp/
ATLAS_MCP_URL=http://localhost:5002/mcp/
KB_PATHS=config/knowledge_base.json
```

**Notes**:

* Do not commit `.env` to version control.
* If `GOOGLE_API_KEY` is not set, configure `clients/atlas_client.py` to use **mock mode**.

**Running**

**Start MCP servers (in a dedicated shell)**

```bash
python start_mcp_servers.py
```

This launches:

* COMMON server → `http://localhost:5001/mcp/`
* ATLAS server → `http://localhost:5002/mcp/`

**Run the workflow**

**Human-readable output:**

```bash
python main.py --input config/input_detailed.json
```

**JSON output with logs:**

```bash
python main.py --input config/input_detailed.json --json
```

**Optional frontend runner**

```bash
python frontend.py
```

**Workflow Stages**

1. **INTAKE** – accept input payload
2. **UNDERSTAND** – parse request (COMMON), extract entities (ATLAS), fallback inference
3. **PREPARE** – normalize fields (COMMON), enrich records (ATLAS), flags, entity normalization
4. **ASK** – clarification (ATLAS) if `missing_info` exists
5. **WAIT** – awaits customer reply if ASK ran
6. **RETRIEVE** – generate semantic query (COMMON), KB search (ATLAS), summarize retrieval
7. **DECIDE** – scoring (COMMON), escalation decision (ATLAS), rationale (COMMON)
8. **UPDATE** – update/close external ticket (ATLAS)
9. **CREATE** – response generation (COMMON)
10. **DO** – external API calls & notifications (ATLAS)
11. **COMPLETE** – finalize & log

**MCP Routing**

* **COMMON**:
  `parse_request_text`, `normalize_fields`, `add_flags_calculations`,
  `entity_normalization`, `generate_semantic_query`, `summarize_retrieval`,
  `solution_evaluation`, `decision_rationale`, `response_generation`

* **ATLAS**:
  `extract_entities`, `enrich_records`, `clarify_question`, `extract_answer`,
  `knowledge_base_search`, `escalation_decision`, `update_ticket`, `close_ticket`,
  `execute_api_calls`, `trigger_notifications`

**Edge Case Testing**

Use sample configs to exercise different flows:

* **Critical/auth-like**: adjust priority & query → test escalation path
* **Delivery clarification**: ensure `order_number` triggers ASK/WAIT
* **Payment dispute**: ensure `transaction_reference` triggers ASK/WAIT

**Run examples:**

```bash
python main.py --input config/ask_demo_delivery.json --json
python main.py --input config/payment_input.json --json
```

**Configuration Overview**

* `config/agent_config.json` – node catalog & abilities metadata
* `config/workflow_config.json` – input schema, stage prompts, ability-to-MCP mapping
* `config/knowledge_base.json` – retrieval corpus for KB search
* `config/*.json` – input examples

**Troubleshooting**

* **Credentials error (Google GenAI)** → set `GOOGLE_API_KEY` or enable mock mode in `atlas_client.py`
* **ASK stage not triggered** → ensure `missing_info` is produced in UNDERSTAND/PREPARE
* **Empty KB result** → update `knowledge_base.json` or add more via `KB_PATHS`
* **Import errors** → check venv activation & dependency install
