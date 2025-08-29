import os
import json
import asyncio
import gradio as gr

from agent2.agent.graph import graph
from agent2.schemas.agent_state import AgentState


def run_agent(customer_name: str, email: str, query: str, priority: str, ticket_id: str) -> str:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "customer_name": customer_name,
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
        "solution_summary": ""
    }

    thread_id = ticket_id
    async def _run():
        async for _ in graph.astream(initial_state, config={"configurable": {"thread_id": thread_id}}):
            pass
        state = graph.get_state({"configurable": {"thread_id": thread_id}}).values
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
                    "reason": state.get("decision_reason", "")
                },
                "response": state.get("solution_summary", ""),
                "actions_taken": [
                    "Generated new password reset link" if "password" in str(state.get("query", "")).lower() else "Applied standard resolution",
                    "Sent reset link via email" if "password" in str(state.get("query", "")).lower() else "Notified customer"
                ]
            },
            "logs": state.get("audit_log", [])
        }
        return json.dumps(final_output, indent=2)

    return asyncio.run(_run())


with gr.Blocks(title="Langie Agent") as demo:
    gr.Markdown("**Langie Agent - Customer Support Workflow**")
    with gr.Row():
        customer_name = gr.Textbox(label="Customer Name", value="Akshay Redekar")
        email = gr.Textbox(label="Email", value="akshay.redekar@example.com")
    query = gr.Textbox(label="Query", value="Hi, I cannot reset my password and the reset link does not work. Can you help me?")
    priority = gr.Dropdown(choices=["Low", "Medium", "High", "Critical"], value="High", label="Priority")
    ticket_id = gr.Textbox(label="Ticket ID", value="TCK12345")
    run_btn = gr.Button("Run Agent")
    output = gr.Code(label="Final Output (JSON)")

    run_btn.click(
        fn=run_agent,
        inputs=[customer_name, email, query, priority, ticket_id],
        outputs=output,
    )

if __name__ == "__main__":
    demo.launch()


