# project-folder/clients/common_client.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from schemas.agent_state import AgentState
from typing import Any
import os

class CommonClient:
    def __init__(self):
        from pydantic import SecretStr
        self.llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), # type: ignore
            temperature=0,
            api_key=SecretStr(os.getenv("GROQ_API_KEY") or "")
        )

    def execute(self, ability: str, state: AgentState) -> Any:
        if ability == "parse_request_text":
            prompt = ChatPromptTemplate.from_template(
                "You are an information extraction assistant.\n"
                "Extract key entities from the customer query. Return strictly JSON with key 'entities' and this shape:\n"
                "{\n  'issue_type': string,\n  'affected_component': string,\n  'problem_description': string[],\n  'request_type': string\n}\n"
                "If a field is unknown, return an empty string or empty array.\n\nQuery:\n{query}"
            )
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"query": state["query"]})
            return result
        elif ability == "normalize_fields":
            # Simple normalization example
            return {"priority": state["priority"].upper()}
        elif ability == "add_flags_calculations":
            flags = {}
            if "high" in state["priority"].lower():
                flags["sla_risk"] = "high"
            return flags
        elif ability == "solution_evaluation":
            prompt = ChatPromptTemplate.from_template(
                "Evaluate resolution confidence based on the inputs.\n"
                "Return strict JSON: { 'score': number, 'reason': string }\n\n"
                "Inputs:\n- Query: {query}\n- Priority: {priority}\n- Retrieved: {retrieved_data}"
            )
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"query": state["query"], "retrieved_data": state.get("retrieved_data", {}), "priority": state.get("priority", "")})
            return result
        elif ability == "response_generation":
            prompt = ChatPromptTemplate.from_template(
                "Write a concise, empathetic customer response.\n"
                "Use: name={name}, entities={entities}, kb={kb}, decision={decision}.\n"
                "Include summary of issue, immediate steps, and next steps/escalation."
            )
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
        else:
            raise ValueError(f"Unknown ability '{ability}' for COMMON server")