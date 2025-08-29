import asyncio
import json
import gradio as gr

from agent.graph import graph
from schemas.agent_state import AgentState


def run_agent(name: str, email: str, query: str, priority: str, ticket_id: str) -> tuple[str, str]:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "customer_name": name,
        "email": email,
        "query": query,
        "priority": priority,
        "structured_data": {},
        "enriched_data": {},
        "flags": {},
        "entities": {},
        "normalized_data": {},
        "clarification_question": "",
        "missing_info": [],
        "extracted_answer": {},
        "retrieved_data": {},
        "retrieval_summary": "",
        "knowledge_base_data": {},
        "solution_score": 0,
        "escalation_decision": {},
        "escalate": False,
        "decision_reason": "",
        "escalation_path": "",
        "next_action": "",
        "route": "",
        "ticket_update": {},
        "ticket_close": {},
        "customer_response": "",
        "api_results": [],
        "notification_result": {},
        "status": "started",
        "audit_log": [],
        "workflow_start_time": "",
        "workflow_end_time": "",
        "messages": [],
        "solution_summary": "",
    }

    async def _invoke() -> dict:
        thread_id = ticket_id
        async for _ in graph.astream(initial_state, config={"configurable": {"thread_id": thread_id}}):
            pass
        return graph.get_state({"configurable": {"thread_id": thread_id}}).values

    state = asyncio.run(_invoke())

    final_output = {
        "final_payload": {
            "ticket_id": state.get("ticket_id"),
            "customer_name": state.get("customer_name"),
            "email": state.get("email"),
            "query": state.get("query"),
            "priority": state.get("priority"),
            "entities": state.get("structured_data", {}).get("entities", state.get("entities", {})),
            "normalized_fields": {
                "priority_score": 95 if str(state.get("priority", "")).lower() in ("high", "critical") else 70,
                "sla_risk": state.get("flags", {}).get("sla_risk", "Low").title(),
                "ticket_status": state.get("status", "resolved").title(),
            },
            "retrieved_info": [
                {"source": "Knowledge Base", "content": state.get("retrieved_data", {}).get("data", "")}
            ],
            "retrieval_summary": state.get("retrieval_summary", ""),
            "decision": {
                "solution_score": state.get("solution_score", 0),
                "escalated": bool(state.get("escalate", False)),
                "assigned_to": "Automated Resolution" if not state.get("escalate", False) else str(state.get("escalation_path", "")),
                "reason": state.get("decision_reason", ""),
            },
            "response": state.get("solution_summary", ""),
        },
        "logs": state.get("audit_log", []),
    }

    md = f"""
### Final Summary
- Ticket: `{state.get('ticket_id')}`  
- Priority: `{state.get('priority')}`  
- Escalated: `{bool(state.get('escalate', False))}`  
- Decision: {state.get('decision_reason','')}

#### Response
{state.get('solution_summary','')}

#### Clarification (if any)
{state.get('clarification_question','')}
""".strip()

    return md, json.dumps(final_output, indent=2)


with gr.Blocks(title="Langie Agent") as demo:
    gr.Markdown("**Langie Agent - Customer Support Workflow**")
    with gr.Row():
        name = gr.Textbox(label="Customer Name", value="Akshay Redekar")
        email = gr.Textbox(label="Email", value="akshay.redekar@example.com")
    query = gr.Textbox(label="Query", lines=4, value="Hi, I cannot reset my password and the reset link does not work. Can you help me?")
    with gr.Row():
        priority = gr.Dropdown(choices=["Low", "Medium", "High", "Critical"], value="High", label="Priority")
        ticket_id = gr.Textbox(label="Ticket ID", value="TCK12345")
    run_btn = gr.Button("Run Agent")
    md_out = gr.Markdown()
    json_out = gr.Code(label="Final Output (JSON)", language="json")

    run_btn.click(fn=run_agent, inputs=[name, email, query, priority, ticket_id], outputs=[md_out, json_out])

if __name__ == "__main__":
    demo.launch()


