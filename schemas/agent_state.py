# project-folder/schemas/agent_state.py
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    ticket_id: str
    customer_name: str
    email: str
    query: str
    priority: str
    structured_data: Dict[str, Any]
    enriched_data: Dict[str, Any]
    flags: Dict[str, Any]
    messages: Annotated[List[BaseMessage], add_messages]
    solution_score: int
    escalation_path: str
    retrieved_data: Dict[str, Any]
    retrieval_summary: str
    solution_summary: str
    status: str
    audit_log: List[Dict[str, Any]]
    route: str  # Temporary for routing
    
    # Additional fields for the workflow
    entities: Dict[str, Any]
    normalized_data: Dict[str, Any]
    clarification_question: str
    missing_info: List[str]
    extracted_answer: Dict[str, Any]
    knowledge_base_data: Dict[str, Any]
    escalation_decision: Dict[str, Any]
    escalate: bool
    decision_reason: str
    next_action: str
    ticket_update: Dict[str, Any]
    ticket_close: Dict[str, Any]
    customer_response: str
    api_results: List[Dict[str, Any]]
    notification_result: Dict[str, Any]
    workflow_start_time: str
    workflow_end_time: str