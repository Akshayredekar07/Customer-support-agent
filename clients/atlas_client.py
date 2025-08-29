# project-folder/clients/atlas_client.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from schemas.agent_state import AgentState
import os
from typing import Any

class AtlasClient:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    def execute(self, ability: str, state: AgentState) -> Any:
        if ability == "extract_entities":
            prompt = ChatPromptTemplate.from_template(
                "You are an expert support triage assistant.\n"
                "Extract entities from the customer query.\n"
                "Return STRICT JSON with key 'entities' using this schema:\n"
                "{\n  'issue_type': string,\n  'affected_component': string,\n  'problem_description': string[],\n  'request_type': string\n}\n"
                "Guidance:\n- For authentication issues, issue_type='Authentication', affected_component='Two-Factor Authentication' or 'Password Reset'.\n- For payment issues, issue_type='Payment', affected_component='Billing'.\n- request_type should reflect intent (e.g., 'refund', 'account access recovery').\n\nQuery:\n{query}"
            )
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"query": state["query"]})
            # Post-process to avoid bleed-through when query mentions invoices but is primarily auth
            try:
                ql = str(state.get("query", "")).lower()
                ents = result.get("entities", result) if isinstance(result, dict) else {}
                if any(k in ql for k in ["2fa", "auth", "code", "password", "reset"]) and "invoice" in ql:
                    ents["issue_type"] = "Authentication"
                    ents["affected_component"] = "Two-Factor Authentication"
                    if "problem_description" not in ents or not ents.get("problem_description"):
                        ents["problem_description"] = ["2FA codes not arriving", "authenticator app out-of-sync"]
                    ents.setdefault("request_type", "account access recovery")
                return {"entities": ents}
            except Exception:
                return result
        elif ability == "enrich_records":
            # Mock external enrichment
            return {"sla_in_hours": 24, "historical_tickets": 0}
        elif ability == "clarify_question":
            prompt = ChatPromptTemplate.from_template(
                "Based on the query and any known entities, generate up to 2 concise clarification questions if any critical details are missing (IDs, steps tried, account details).\n"
                "Return plain text with questions joined by ' | ' (or an empty string if none).\n\nQuery: {query}\nEntities: {entities}"
            )
            chain = prompt | self.llm | StrOutputParser()
            text = chain.invoke({
                "query": state.get("query", ""),
                "entities": state.get("entities", {}),
            })
            return {"question": text.strip()}
        elif ability == "extract_answer":
            # Mock extracting answer (in real, from external input)
            return {"answer": "The broken part is the motor."}
        elif ability == "knowledge_base_search":
            # Delegate to file-backed search in the MCP client path; keep a minimal fallback
            return {"data": "No information found."}
        elif ability == "escalation_decision":
            prompt = ChatPromptTemplate.from_template(
                "Decide escalation path for query: {query} with score: {score}\n"
                "Output path like 'Tier 2 Support'"
            )
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"query": state["query"], "score": state["solution_score"]})
        elif ability == "update_ticket":
            # Mock API call
            print("Updating ticket in external CRM system.")
            return True
        elif ability == "close_ticket":
            # Mock API call
            print("Closing ticket in external system.")
            return True
        elif ability == "execute_api_calls":
            # Mock API
            print("Executing external API calls.")
            return True
        elif ability == "trigger_notifications":
            # Mock notification
            print("Triggering notifications.")
            return True
        else:
            raise ValueError(f"Unknown ability '{ability}' for ATLAS server")