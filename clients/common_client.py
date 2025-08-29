from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from schemas.agent_state import AgentState
from typing import Any
import os
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

class CommonClient:
    def __init__(self):
        groq_key = os.getenv("GROQ_API_KEY")
        self.llm = None
        if groq_key:
            self.llm = ChatGroq(
                model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
                temperature=0,
                api_key=SecretStr(groq_key),
            )

    def execute(self, ability: str, state: AgentState) -> Any:
        if ability == "parse_request_text":
            prompt = ChatPromptTemplate.from_template(
                "You are an information extraction assistant.\n"
                "Extract key entities from the customer query. Return strictly JSON with key 'entities' and this shape:\n"
                "{{\n  'issue_type': string,\n  'affected_component': string,\n  'problem_description': string[],\n  'request_type': string\n}}\n"
                "If a field is unknown, return an empty string or empty array.\n\nQuery:\n{query}"
            )
            if self.llm is not None:
                chain = prompt | self.llm | JsonOutputParser()
                return chain.invoke({"query": state["query"]})
            return {"entities": {"issue_type": "", "affected_component": "", "problem_description": [], "request_type": ""}}
        elif ability == "normalize_fields":
            return {"priority": state["priority"].upper()}
        elif ability == "add_flags_calculations":
            flags = {}
            if "high" in state["priority"].lower():
                flags["sla_risk"] = "high"
            return flags
        elif ability == "entity_normalization":
            return {"entities": state.get("entities", {})}
        elif ability == "generate_semantic_query":
            prompt = ChatPromptTemplate.from_template(
                "Rewrite the following user query into a concise semantic search query for a knowledge base.\n"
                "Original: {query}\n"
                "Entities (may be empty): {entities}\n"
                "Return just the rewritten query text."
            )
            if self.llm is not None:
                chain = prompt | self.llm | StrOutputParser()
                return {"semantic_query": chain.invoke({
                    "query": state.get("query", ""),
                    "entities": state.get("entities", {})
                })}
            return {"semantic_query": state.get("query", "")}
        elif ability == "summarize_retrieval":
            prompt = ChatPromptTemplate.from_template(
                "Summarize the following KB snippet in one sentence. If content is empty or generic,"
                " produce: 'No relevant KB found. Escalating based on SLA and priority.'\nKB: {kb}"
            )
            if self.llm is not None:
                chain = prompt | self.llm | StrOutputParser()
                return chain.invoke({"kb": state.get("retrieved_data", {})})
            data = str(state.get("retrieved_data", {}).get("data", ""))
            if not data:
                return "No relevant KB found. Escalating based on SLA and priority."
            return f"Summary: {data[:140]}" + ("..." if len(data) > 140 else "")
        elif ability == "solution_evaluation":
            prompt = ChatPromptTemplate.from_template(
                "Evaluate resolution confidence based on the inputs.\n"
                "Return strictly valid JSON with keys \"score\" (integer 0-100) and \"reason\" (string). Only output JSON.\n\n"
                "Inputs:\n- Query: {query}\n- Priority: {priority}\n- Retrieved: {retrieved_data}"
            )
            if self.llm is not None:
                chain = prompt | self.llm | JsonOutputParser()
                result = chain.invoke({"query": state["query"], "retrieved_data": state.get("retrieved_data", {}), "priority": state.get("priority", "")})
                if isinstance(result, dict) and "score" in result:
                    result["score"] = int(max(0, min(100, round(float(result["score"])))))
                else:
                    result = {"score": 70, "reason": "normalized_fallback"}
                return result
            return {"score": 70, "reason": "llm_unavailable"}
        elif ability == "decision_rationale":
            prompt = ChatPromptTemplate.from_template(
                "Given the context, write a short contextual reason for escalation or not (one sentence).\n"
                "Inputs:\n- Score: {score}\n- Priority: {priority}\n- Entities: {entities}\n- KB Summary: {kb}"
            )
            if self.llm is not None:
                chain = prompt | self.llm | StrOutputParser()
                return chain.invoke({
                    "score": state.get("solution_score", 0),
                    "priority": state.get("priority", ""),
                    "entities": state.get("entities", {}),
                    "kb": state.get("retrieved_data", {}),
                })
            return "Automated rationale unavailable"
        elif ability == "response_generation":
            prompt = ChatPromptTemplate.from_template(
                "Write a concise, empathetic customer response.\n"
                "Use: name={name}, entities={entities}, kb={kb}, decision={decision}.\n"
                "Include summary of issue, immediate steps, and next steps/escalation.\n"
                "If delivery: add a proactive timeline (e.g., courier escalation within 12 hours).\n"
                "If payment/banking: add a settlement-team escalation within 12 hours if unresolved.\n"
                "If authentication: offer a temporary access fallback within 30 minutes if reset fails."
            )
            if self.llm is not None:
                chain = prompt | self.llm | StrOutputParser()
                return chain.invoke({
                    "name": state.get("customer_name", "Customer"),
                    "entities": state.get("entities", {}),
                    "kb": state.get("retrieved_data", {}),
                    "decision": {
                        "score": state.get("solution_score", 0),
                        "escalate": state.get("escalate", False),
                        "reason": state.get("decision_reason", "")
                    }
                })
            return f"Hello {state.get('customer_name','Customer')}, we have received your request and will follow up shortly."
        else:
            raise ValueError(f"Unknown ability '{ability}' for COMMON server")