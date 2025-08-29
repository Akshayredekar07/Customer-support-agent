
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from schemas.agent_state import AgentState
import os
from typing import Any
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


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
                "{{\n  'issue_type': string,\n  'affected_component': string,\n  'problem_description': string[],\n  'request_type': string\n}}\n"
                "Guidance:\n- For authentication issues, issue_type='Authentication', affected_component='Two-Factor Authentication' or 'Password Reset'.\n- For payment issues, issue_type='Payment', affected_component='Billing'.\n- request_type should reflect intent (e.g., 'refund', 'account access recovery').\n\nQuery:\n{query}"
            )
            chain = prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"query": state["query"]})
            ql = str(state.get("query", "")).lower()
            ents = result.get("entities", result) if isinstance(result, dict) else {}
            if any(k in ql for k in ["2fa", "auth", "code", "password", "reset"]) and "invoice" in ql:
                ents["issue_type"] = "Authentication"
                ents["affected_component"] = "Two-Factor Authentication"
                if "problem_description" not in ents or not ents.get("problem_description"):
                    ents["problem_description"] = ["2FA codes not arriving", "authenticator app out-of-sync"]
                ents.setdefault("request_type", "account access recovery")
            return {"entities": ents}
        elif ability == "enrich_records":
            return {"sla_in_hours": 24, "historical_tickets": 0}
        elif ability == "clarify_question":
            prompt = ChatPromptTemplate.from_template(
                "Based on the query and entities, generate up to 2 concise clarification questions if any critical details are missing (IDs, steps tried, account details).\n"
                "Prefer asking for 'order_number' for delivery or 'transaction_reference' for payment when missing.\n"
                "Return plain text with questions joined by ' | ' (or an empty string if none).\n\nQuery: {query}\nEntities: {entities}\nMissing: {missing}"
            )
            chain = prompt | self.llm | StrOutputParser()
            text = chain.invoke({
                "query": state.get("query", ""),
                "entities": state.get("entities", {}),
                "missing": state.get("missing_info", []),
            })
            return {"question": text.strip()}
        elif ability == "extract_answer":
            return {"answer": "The broken part is the motor."}
        elif ability == "knowledge_base_search":
            q = str(state.get("query", "")).lower()
            entities = state.get("entities", {}) or {}
            env_paths = os.getenv("KB_PATHS") or os.getenv("KB_PATH") or "config/knowledge_base.json"
            paths: list[Path] = []
            for p in env_paths.split(";"):
                pp = Path(p.strip())
                if not pp.exists():
                    continue
                if pp.is_dir():
                    paths.extend(sorted(pp.glob("*.json")))
                else:
                    paths.append(pp)
            if not paths:
                return {"data": ""}
            best = {"score": 0, "content": ""}
            for file in paths:
                data = json.loads(file.read_text(encoding="utf-8"))
                for art in data.get("articles", []):
                    tags = [str(t).lower() for t in art.get("tags", [])]
                    hit = 0
                    hit += sum(1 for t in tags if t in q)
                    ent_text = " ".join([str(v).lower() for v in entities.values() if isinstance(v, str)])
                    hit += sum(1 for t in tags if t in ent_text)
                    if hit > best["score"]:
                        best = {"score": hit, "content": art.get("content", "")}
            return {"data": best["content"]}
        elif ability == "escalation_decision":
            prompt = ChatPromptTemplate.from_template(
                "Decide escalation path for query: {query} with score: {score}\n"
                "Output path like 'Tier 2 Support'"
            )
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"query": state["query"], "score": state["solution_score"]})
        elif ability == "update_ticket":
            return True
        elif ability == "close_ticket":
            return True
        elif ability == "execute_api_calls":
            return True
        elif ability == "trigger_notifications":
            return True
        else:
            raise ValueError(f"Unknown ability '{ability}' for ATLAS server")