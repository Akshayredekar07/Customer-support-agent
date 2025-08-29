"""
Lang Graph Agent - Customer Support Workflow
"""
import os
import sys
import json
import asyncio
from argparse import ArgumentParser
from pathlib import Path

os.environ.setdefault("COMMON_MCP_URL", "http://localhost:5001/mcp/")
os.environ.setdefault("ATLAS_MCP_URL", "http://localhost:5002/mcp/")

# Import existing modular components
from agent.graph import graph
from schemas.agent_state import AgentState

def load_input_payload(path: str | None) -> dict:
    if path:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    default_path = Path("config/sample_input.json")
    if default_path.exists():
        with default_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "customer_name": "Akshay Redekar",
        "email": "akshay.redekar@example.com",
        "query": "Hi, I cannot reset my password and the reset link does not work. Can you help me?",
        "priority": "High",
        "ticket_id": "TCK12345",
    }

async def main():
    parser = ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print final output JSON only")
    parser.add_argument("--input", type=str, default=None, help="Path to input JSON file")
    # No forced routing by default; decisions are made by LLM/tools
    args = parser.parse_args()

    print("LANG GRAPH AGENT - CUSTOMER SUPPORT WORKFLOW")
    print("=" * 80)
    
    input_payload = load_input_payload(args.input)
    
    incoming_response = ""
    
    # Initialize state (abbrev comments omitted)
    initial_state: AgentState = {
        "ticket_id": input_payload["ticket_id"],
        "customer_name": input_payload["customer_name"],
        "email": input_payload["email"],
        "query": input_payload["query"],
        "priority": input_payload["priority"],
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
        "customer_response": incoming_response,
        "api_results": [],
        "notification_result": {},
        "status": "started",
        "audit_log": [],
        "workflow_start_time": "",
        "workflow_end_time": "",
        "messages": [],
        "solution_summary": ""
    }
    
    # Run the workflow
    try:
        thread_id = input_payload["ticket_id"]

        # First pass
        async for _ in graph.astream(initial_state, config={"configurable": {"thread_id": thread_id}}):
            pass
        final_state = graph.get_state({"configurable": {"thread_id": thread_id}}).values

        # If we are awaiting a human response (regardless of route), prompt and resume
        if (
            str(final_state.get("status", "")) == "awaiting_customer"
            and not incoming_response
        ):
            # Use dedicated clarification field
            question_text = final_state.get("clarification_question")
            print("\nClarification needed (from LLM):")
            print(question_text or "Please provide more details to proceed.")

            try:
                user_reply = input("\nYour reply: ").strip()
            except Exception:
                user_reply = ""

            if user_reply:
                # Resume second pass with customer_response provided
                resume_state: AgentState = {
                    "ticket_id": thread_id,
                    "customer_response": user_reply,
                    # Minimal keys; checkpointer will merge with existing
                    "structured_data": final_state.get("structured_data", {}),
                    "audit_log": final_state.get("audit_log", []),
                }  # type: ignore
                async for _ in graph.astream(resume_state, config={"configurable": {"thread_id": thread_id}}):
                    pass
                final_state = graph.get_state({"configurable": {"thread_id": thread_id}}).values
    except Exception as e:
        print(f"Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if args.json:
        # Build final JSON in requested structure
        final_output = {
            "final_payload": {
                "ticket_id": final_state.get("ticket_id"),
                "customer_name": final_state.get("customer_name"),
                "email": final_state.get("email"),
                "query": final_state.get("query"),
                "priority": final_state.get("priority"),
                "entities": final_state.get("structured_data", {}).get("entities", final_state.get("entities", {})),
                "normalized_fields": {
                    # Derive a dynamic priority score influenced by priority and decision score
                    "priority_score": (
                        min(100, max(50,
                            (90 if str(final_state.get("priority", "")).lower()=="high" else (98 if str(final_state.get("priority", "")).lower()=="critical" else (80 if str(final_state.get("priority", "")).lower()=="medium" else 70)))
                        ))
                    ),
                    "sla_risk": final_state.get("flags", {}).get("sla_risk", "Low").title(),
                    "ticket_status": final_state.get("status", "resolved").title(),
                },
                "retrieved_info": [
                    {
                        "source": "Knowledge Base",
                        "content": final_state.get("retrieved_data", {}).get("data", "")
                    }
                ],
                "decision": {
                    "solution_score": final_state.get("solution_score", 0),
                    "escalated": bool(final_state.get("escalate", False)),
                    "assigned_to": "Automated Resolution" if not final_state.get("escalate", False) else str(final_state.get("escalation_path", "")),
                    "reason": final_state.get("decision_reason", "")
                },
                "response": final_state.get("solution_summary", ""),
                "retrieval_summary": final_state.get("retrieval_summary", ""),
                "actions_taken": (lambda logs: [
                    (a.get("action") or "").replace("_", " ").title()
                    for a in logs if a.get("stage")=="DO" and a.get("action")
                ])(final_state.get("audit_log", []))
            },
            "logs": final_state.get("audit_log", [])
        }
        print(json.dumps(final_output, indent=2))
        return

    # Default: human-friendly console output
    print("\nFINAL PAYLOAD - key fields")
    print("=" * 80)
    for k in ("ticket_id","customer_name","email","query","priority","solution_score","route","status"):
        print(f"{k}: {final_state.get(k)}")
    print("\nLogs (stage, abilities, mcp)")
    for log in final_state.get("audit_log", []):
        print(f"- {log.get('stage')}: {log.get('abilities_executed')} via {log.get('mcp_client')}")

if __name__ == "__main__":
    asyncio.run(main())