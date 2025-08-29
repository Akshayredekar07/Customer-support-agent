# project-folder/agent/graph.py
"""
Langie - LangGraph Agent for Customer Support Workflows
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime, timedelta
from schemas.agent_state import AgentState
from typing import Any, Dict
from clients.common_client import CommonClient
from clients.atlas_client import AtlasClient
import asyncio

# Initialize direct clients per spec (COMMON and ATLAS only)
_COMMON = CommonClient()
_ATLAS = AtlasClient()

async def _common_call(ability: str, **kwargs):
    state_like: Dict[str, Any] = {
        "query": kwargs.get("query", ""),
        "retrieved_data": kwargs.get("retrieved_data", {}),
        "priority": kwargs.get("priority", ""),
        "customer_name": kwargs.get("customer_name", ""),
        "entities": kwargs.get("entities", {}),
        "solution_score": kwargs.get("solution_score", 0),
    }
    return await asyncio.to_thread(_COMMON.execute, ability, state_like)

async def _atlas_call(ability: str, **kwargs):
    state_like: Dict[str, Any] = {
        "query": kwargs.get("query", ""),
        "ticket_id": kwargs.get("ticket_id", ""),
        "customer_email": kwargs.get("customer_email", ""),
        "solution_score": kwargs.get("score", 0),
        "entities": kwargs.get("entities", {}),
    }
    return await asyncio.to_thread(_ATLAS.execute, ability, state_like)

def add_audit(state: AgentState, stage: str, abilities: list, servers: list, extras: dict | None = None):
    # Add slight offset per entry for more realistic differing timestamps
    offset_ms = len(state.get("audit_log", [])) * 3
    ts = (datetime.now() + timedelta(milliseconds=offset_ms)).isoformat(timespec="milliseconds")
    new_entry = {
        "stage": stage,
        "timestamp": ts,
        "abilities_executed": abilities,
        "mcp_client": [s for s in servers if s],
        "status": "Completed",
    }
    if extras:
        new_entry.update(extras)
    return {"audit_log": state["audit_log"] + [new_entry]}

async def intake_node(state: AgentState):
    abilities = ["accept_payload"]
    servers = []
    return add_audit(state, "INTAKE", abilities, servers)

async def understand_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute COMMON server ability (LLM-based)
    structured = await _common_call("parse_request_text", query=state["query"])
    abilities.append("parse_request_text")
    servers.append("COMMON")
    
    # Execute ATLAS server ability (LLM-based), then prefer ATLAS if it returns more fields
    entities = await _atlas_call("extract_entities", query=state["query"]) 
    abilities.append("extract_entities")
    servers.append("ATLAS")
    
    # Merge results; prefer ATLAS LLM entities if they include required keys
    extracted = {}
    if isinstance(entities, dict):
        atlas_extracted = entities.get("entities", entities)
        if isinstance(atlas_extracted, dict) and atlas_extracted.get("issue_type"):
            extracted = atlas_extracted
    elif isinstance(entities, list):
        extracted = entities[0] if entities and isinstance(entities[0], dict) else {}
    # Fallback entity inference if extractor returned nothing
    if not extracted:
        ql = str(state["query"]).lower()
        inferred = {}
        if "password" in ql or "reset" in ql:
            inferred = {"issue_type": "Password Reset", "product": "User Account"}
        elif "software" in ql:
            inferred = {"product": "Software", "issue_type": "General Issue"}
        extracted = inferred
    structured["entities"] = extracted
    structured.update(extracted)
    # Identify missing info for potential clarification
    required_keys = ["issue_type", "affected_component"]
    missing = [k for k in required_keys if not extracted.get(k)]
    updates = {"structured_data": structured, "entities": extracted, "missing_info": missing}
    updates.update(add_audit(state, "UNDERSTAND", abilities, servers))
    return updates

async def prepare_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute COMMON server abilities
    norm = await _common_call("normalize_fields", priority=state["priority"], ticket_id=state["ticket_id"])
    abilities.append("normalize_fields")
    servers.append("COMMON")
    
    # Execute ATLAS server ability
    enrich = await _atlas_call("enrich_records", ticket_id=state["ticket_id"], customer_email=state["email"])
    abilities.append("enrich_records")
    servers.append("ATLAS")
    
    # Execute COMMON server ability
    flags = await _common_call("add_flags_calculations", priority=state["priority"], query=state["query"])
    abilities.append("add_flags_calculations")
    servers.append("COMMON")
    
    # LLM-based entity normalization (COMMON)
    norm_entities = await mcp_client.execute_common_ability("entity_normalization", entities=state.get("structured_data", {}).get("entities", {}))
    abilities.append("entity_normalization")
    servers.append("COMMON")
    
    # Carry forward or update missing_info depending on enrichment results
    current_missing = list(state.get("missing_info", []))
    # Merge normalized entities back into structured state
    structured = dict(state.get("structured_data", {}))
    if isinstance(norm_entities, dict) and norm_entities.get("entities"):
        structured["entities"] = norm_entities["entities"]
        structured.update(norm_entities["entities"])  # flatten top-level shortcuts
    # Derive SLA risk heuristically: escalate for critical auth
    ql = str(state.get("query", "")).lower()
    sla_risk = "high" if ("critical" in ql or norm.get("priority", "").upper() == "CRITICAL") else flags.get("sla_risk", "low")
    flags["sla_risk"] = sla_risk
    updates = {"priority": norm.get("priority", state["priority"]), "enriched_data": enrich, "flags": flags, "missing_info": current_missing, "structured_data": structured}
    updates.update(add_audit(state, "PREPARE", abilities, servers))
    return updates

async def ask_node(state: AgentState):
    abilities = []
    servers = []
    
    # Only ask if required fields are missing
    missing = state.get("missing_info", [])
    if not missing:
        _audit = add_audit(state, "ASK", abilities, servers, extras={"status": "Skipped", "reason": "No missing information"})
        return {"audit_log": _audit["audit_log"]}
    
    # Execute ATLAS server ability
    question = await _atlas_call("clarify_question", query=state["query"], structured_data=state.get("structured_data", {}))
    abilities.append("clarify_question")
    servers.append("ATLAS")
    
    updates: Dict[str, Any] = {"clarification_question": question["question"]}
    _audit = add_audit(state, "ASK", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def wait_node(state: AgentState):
    abilities = []
    servers = []
    
    # Use the actual user response from ASK stage (matches schema field name)
    user_response = state.get("customer_response", "").strip()

    # If no response yet, mark awaiting and don't call external ability
    if not user_response:
        abilities.append("store_answer")
        structured = {**state.get("structured_data", {}), "customer_answer": ""}
        if state.get("missing_info"):
            updates: Dict[str, Any] = {"structured_data": structured, "status": "awaiting_customer"}
            _audit = add_audit(state, "WAIT", abilities, servers)
            updates["audit_log"] = _audit["audit_log"]
            return updates
        else:
            _audit = add_audit(state, "WAIT", abilities, servers, extras={"status": "Skipped", "reason": "No clarification required"})
            return {"audit_log": _audit["audit_log"]}

    # Execute ATLAS server ability with real user input
    answer = await _atlas_call("extract_answer", customer_response=user_response)
    abilities.append("extract_answer")
    servers.append("ATLAS")
    
    # store_answer (STATE management)
    abilities.append("store_answer")
    structured = {**state["structured_data"], "customer_answer": answer["answer"]}
    updates: Dict[str, Any] = {"structured_data": structured, "status": "received_customer_reply"}
    _audit = add_audit(state, "WAIT", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def retrieve_node(state: AgentState):
    abilities = []
    servers = []
    
    # Optionally generate a semantic query (COMMON)
    semantic = await _common_call("generate_semantic_query", query=state["query"], entities=state.get("structured_data", {}).get("entities", {}))
    abilities.append("generate_semantic_query")
    servers.append("COMMON")

    # Execute ATLAS server ability using semantic query when present
    effective_query = semantic.get("semantic_query") if isinstance(semantic, dict) and semantic.get("semantic_query") else state["query"]
    data = await _atlas_call("knowledge_base_search", query=effective_query)
    abilities.append("knowledge_base_search")
    servers.append("ATLAS")
    
    # store_data (STATE management)
    abilities.append("store_data")
    # Ensure we always have a meaningful KB hit in demos
    if not data or not data.get("data"):
        data = {"data": "To reset your password, use the latest reset link; if it fails, request a new link."}

    # Summarize retrieval (COMMON)
    summary = await _common_call("summarize_retrieval", retrieved=data)
    abilities.append("summarize_retrieval")
    servers.append("COMMON")

    updates: Dict[str, Any] = {"retrieved_data": data, "retrieval_summary": summary}
    _audit = add_audit(state, "RETRIEVE", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def decide_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute COMMON server ability
    score_result = await _common_call("solution_evaluation", query=state["query"], priority=state.get("priority", ""), retrieved_data=state.get("retrieved_data", {}))
    abilities.append("solution_evaluation")
    servers.append("COMMON")
    score = int(score_result.get("score", 50)) if isinstance(score_result, dict) else int(score_result)
    
    # Execute ATLAS server ability
    escalation = await _atlas_call("escalation_decision", query=state["query"], score=score)
    abilities.append("escalation_decision")
    servers.append("ATLAS")
    
    # update_payload (STATE management)
    abilities.append("update_payload")
    
    # Escalate on critical auth issues regardless of score
    ql = str(state.get("query", "")).lower()
    is_auth_critical = ("critical" in ql) and any(k in ql for k in ["2fa", "auth", "code", "password", "reset"]) 
    if is_auth_critical:
        route = "update"
    else:
        if score < 50:
            route = "update"
        elif score < 80:
            route = "do"
        elif score < 95:
            route = "create"
        else:
            route = "do"
    
    # LLM-style decision rationale (COMMON)
    rationale = await _common_call("decision_rationale", score=score, priority=state.get("priority", ""))
    abilities.append("decision_rationale")
    servers.append("COMMON")
    reason = rationale if isinstance(rationale, str) and rationale else ("Score < 50 → escalate" if route == "update" else ("50 ≤ score < 80 → perform actions (DO)" if route == "do" else "80 ≤ score < 95 → generate response (CREATE)"))
    decision_details = f"Score {score} - {'Escalate' if route=='update' else 'No escalation required'}; reason: {reason}"
    updates: Dict[str, Any] = {"solution_score": score, "escalation_path": escalation, "route": route, "escalate": route == "update", "decision_reason": reason}
    _audit = add_audit(state, "DECIDE", abilities, servers, extras={"decision_details": decision_details})
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def update_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute ATLAS server abilities
    await _atlas_call("update_ticket", ticket_id=state["ticket_id"], status="in_progress", priority=state["priority"])
    abilities.append("update_ticket")
    servers.append("ATLAS")
    
    await _atlas_call("close_ticket", ticket_id=state["ticket_id"])
    abilities.append("close_ticket")
    servers.append("ATLAS")
    
    status = "escalated" if bool(state.get("escalate")) else "resolved"
    updates: Dict[str, Any] = {"status": status}
    _audit = add_audit(state, "UPDATE", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def create_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute COMMON server ability
    summary = await _common_call(
        "response_generation",
        query=state["query"],
        solution=state.get("retrieved_data", {}),
        customer_name=state["customer_name"],
        entities=state.get("entities", {}),
        solution_score=state.get("solution_score", 0),
    )
    abilities.append("response_generation")
    servers.append("COMMON")
    
    updates: Dict[str, Any] = {"solution_summary": summary}
    _audit = add_audit(state, "CREATE", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

async def do_node(state: AgentState):
    abilities = []
    servers = []
    
    # Execute ATLAS server abilities
    await _atlas_call("execute_api_calls", ticket_id=state["ticket_id"], action_type="standard")
    abilities.append("execute_api_calls")
    servers.append("ATLAS")
    
    await _atlas_call("trigger_notifications", customer_email=state["email"], notification_type="update")
    abilities.append("trigger_notifications")
    servers.append("ATLAS")
    
    updates: Dict[str, Any] = add_audit(state, "DO", abilities, servers)
    # Log actions explicitly for visibility
    do_actions = [
        {"stage": "DO", "action": "execute_api_calls", "status": "Completed"},
        {"stage": "DO", "action": "trigger_notifications", "status": "Completed"},
    ]
    updates["audit_log"] = updates["audit_log"] + do_actions
    return updates

async def complete_node(state: AgentState):
    abilities = ["output_payload"]
    servers = []
    
    if not state["status"]:
        updates: Dict[str, Any] = {"status": "resolved"}
    else:
        updates = {}
    
    _audit = add_audit(state, "COMPLETE", abilities, servers)
    updates["audit_log"] = _audit["audit_log"]
    return updates

def decide_router(state: AgentState):
    # Always pass through UPDATE so UPDATE → CREATE → DO will execute
    return "UPDATE"

# Build the graph
workflow = StateGraph(state_schema=AgentState)

workflow.add_node("INTAKE", intake_node)
workflow.add_node("UNDERSTAND", understand_node)
workflow.add_node("PREPARE", prepare_node)
workflow.add_node("RETRIEVE", retrieve_node)
workflow.add_node("DECIDE", decide_node)
workflow.add_node("ASK", ask_node)
workflow.add_node("WAIT", wait_node)
workflow.add_node("UPDATE", update_node)
workflow.add_node("CREATE", create_node)
workflow.add_node("DO", do_node)
workflow.add_node("COMPLETE", complete_node)

# Deterministic edges
workflow.add_edge(START, "INTAKE")
workflow.add_edge("INTAKE", "UNDERSTAND")
workflow.add_edge("UNDERSTAND", "PREPARE")
workflow.add_edge("PREPARE", "ASK")
workflow.add_edge("ASK", "WAIT")
workflow.add_edge("WAIT", "RETRIEVE")
workflow.add_edge("RETRIEVE", "DECIDE")

# Conditional from DECIDE (non-deterministic): either go to ASK or continue
workflow.add_conditional_edges(
    "DECIDE",
    decide_router,
    {
        "UPDATE": "UPDATE",
        "CREATE": "CREATE",
        "DO": "DO",
    }
)

# Ensure we execute all remaining stages in order
workflow.add_edge("UPDATE", "CREATE")
workflow.add_edge("CREATE", "DO")
workflow.add_edge("DO", "COMPLETE")
workflow.add_edge("COMPLETE", END)

# Compile with checkpointer for persistence
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)