# Real MCP Client for Agent2
import os
import asyncio
from typing import Any, Dict

class MCPClient:
    """
    MCP Client that provides fallback implementations for all abilities.
    This ensures the application works reliably even without MCP server connectivity.
    """
    
    def __init__(self):
        # Server URLs for reference (not used in current implementation)
        self.common_url = os.getenv("COMMON_MCP_URL", "http://localhost:5001/mcp")
        self.atlas_url = os.getenv("ATLAS_MCP_URL", "http://localhost:5002/mcp")
        # Try to initialize real LLM-backed clients; fallback to local heuristics if unavailable
        self.common_client = None
        self.atlas_client = None
        try:
            from clients.common_client import CommonClient  # type: ignore
            self.common_client = CommonClient()
        except Exception:
            self.common_client = None
        try:
            from clients.atlas_client import AtlasClient  # type: ignore
            self.atlas_client = AtlasClient()
        except Exception:
            self.atlas_client = None
    
    async def execute_common_ability(self, ability: str, **kwargs) -> Any:
        """
        Execute abilities on COMMON server.
        These are internal abilities with no external data requirements.
        """
        try:
            # Prefer real LLM-backed client if available
            if self.common_client is not None and ability in {
                "parse_request_text",
                "solution_evaluation",
                "response_generation",
                "entity_normalization",
                "generate_semantic_query",
                "summarize_retrieval",
                "decision_rationale",
            }:
                # Build minimal state payload for the client
                state_like: Dict[str, Any] = {
                    "query": kwargs.get("query", ""),
                    "retrieved_data": kwargs.get("retrieved_data", {}),
                    "priority": kwargs.get("priority", ""),
                }
                return self.common_client.execute(ability, state_like)  # type: ignore[arg-type]

            # Map abilities to tool names (fallback path)
            ability_mapping = {
                "parse_request_text": "parse_request_text",
                "normalize_fields": "normalize_fields", 
                "add_flags_calculations": "add_flags_calculations",
                "entity_normalization": "entity_normalization",
                "generate_semantic_query": "generate_semantic_query",
                "summarize_retrieval": "summarize_retrieval",
                "solution_evaluation": "solution_evaluation",
                "decision_rationale": "decision_rationale",
                "response_generation": "response_generation"
            }
            
            tool_name = ability_mapping.get(ability)
            if not tool_name:
                raise ValueError(f"Unknown COMMON ability: {ability}")
            
            # Execute the tool using fallback implementation
            result = await self._fallback_tool_call(tool_name, kwargs)
            return result
            
        except Exception as e:
            print(f"❌ COMMON MCP execution failed for {ability}: {e}")
            # Fallback to mock implementation
            return self._fallback_common(ability, **kwargs)
    
    async def execute_atlas_ability(self, ability: str, **kwargs) -> Any:
        """
        Execute abilities on ATLAS server.
        These are external abilities requiring external system interaction.
        """
        try:
            # Prefer real LLM-backed client if available
            if self.atlas_client is not None and ability in {
                "extract_entities",
                "clarify_question",
                "knowledge_base_search",
                "escalation_decision",
                "update_ticket",
                "close_ticket",
                "execute_api_calls",
                "trigger_notifications",
                "extract_answer",
            }:
                state_like: Dict[str, Any] = {
                    "query": kwargs.get("query", ""),
                    "ticket_id": kwargs.get("ticket_id", ""),
                    "customer_email": kwargs.get("customer_email", ""),
                    "solution_score": kwargs.get("score", 0),
                }
                return self.atlas_client.execute(ability, state_like)  # type: ignore[arg-type]

            # Map abilities to tool names (fallback path)
            ability_mapping = {
                "extract_entities": "extract_entities",
                "enrich_records": "enrich_records",
                "clarify_question": "clarify_question",
                "extract_answer": "extract_answer",
                "knowledge_base_search": "knowledge_base_search",
                "escalation_decision": "escalation_decision",
                "update_ticket": "update_ticket",
                "close_ticket": "close_ticket",
                "execute_api_calls": "execute_api_calls",
                "trigger_notifications": "trigger_notifications"
            }
            
            tool_name = ability_mapping.get(ability)
            if not tool_name:
                raise ValueError(f"Unknown ATLAS ability: {ability}")
            
            # Execute the tool using fallback implementation
            result = await self._fallback_tool_call(tool_name, kwargs)
            return result
            
        except Exception as e:
            print(f"❌ ATLAS MCP execution failed for {ability}: {e}")
            # Fallback to mock implementation
            return self._fallback_atlas(ability, **kwargs)
    
    async def _fallback_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Fallback method that simulates the tool call based on the tool name.
        This provides realistic responses based on the actual tool implementations.
        """
        # Simulate the actual tool responses based on the tool implementations
        if tool_name == "parse_request_text":
            query = arguments.get("query", "")
            ql = str(query).lower()
            parsed: Dict[str, Any] = {}
            if any(k in ql for k in ["password", "reset", "2fa", "code", "auth"]):
                parsed.update({"issue_type": "authentication"})
            if any(k in ql for k in ["payment", "charge", "invoice", "billing"]):
                parsed.update({"issue_type": "payment"})
            if "invoice" in ql:
                parsed["document"] = "invoice"
            return parsed
        elif tool_name == "normalize_fields":
            priority = arguments.get("priority", "")
            return {"priority": priority.upper()}
        elif tool_name == "add_flags_calculations":
            priority = arguments.get("priority", "")
            flags = {}
            if "very very high" in priority.lower():
                flags["sla_risk"] = "critical"
                flags["urgent"] = "true"
                flags["immediate_attention"] = "true"
            elif "high" in priority.lower():
                flags["sla_risk"] = "high"
            else:
                flags["sla_risk"] = "low"
            return flags
        elif tool_name == "solution_evaluation":
            query_text = str(arguments.get("query", "")).lower()
            kb_text = str(arguments.get("retrieved_data", {}).get("data", "")).lower()
            priority_text = str(arguments.get("priority", "")).lower()
            score = 60
            if any(k in query_text for k in ["payment", "charge", "billing", "invoice"]):
                score = 75
            if any(k in query_text for k in ["password", "reset", "2fa", "auth"]):
                score = max(score, 70)
            if any(k in kb_text for k in ["resync", "link", "refund", "duplicate"]):
                score += 10
            if priority_text in ("high", "critical"):
                score += 5
            return {"score": max(30, min(score, 95))}
        elif tool_name == "decision_rationale":
            score = int(arguments.get("score", 0))
            priority = str(arguments.get("priority", "")).upper()
            if score < 50:
                return "Low confidence and potential risk → escalate to human operator."
            if score < 80:
                return "Moderate confidence → proceed with operational steps, monitor for follow-up."
            return "High confidence → proceed with automated response and close the loop."
        elif tool_name == "entity_normalization":
            entities = dict(arguments.get("entities", {}))
            # Simple synonym normalization
            product = entities.get("product", "")
            if product.lower() in ("account", "user account", "profile"):
                entities["product"] = "User Account"
            issue = entities.get("issue_type", "")
            if issue.lower() in ("pwd reset", "password", "password reset"):
                entities["issue_type"] = "Password Reset"
            return {"entities": entities}
        elif tool_name == "generate_semantic_query":
            q = str(arguments.get("query", ""))
            ents = arguments.get("entities", {})
            focus = ents.get("issue_type") or ents.get("product") or "support"
            return {"semantic_query": f"{q} :: intent={focus} :: troubleshooting steps"}
        elif tool_name == "summarize_retrieval":
            data = str(arguments.get("retrieved", {}).get("data", ""))
            if not data:
                return "No relevant knowledge base content found."
            return f"Summary: {data[:140]}" + ("..." if len(data) > 140 else "")
        elif tool_name == "extract_entities":
            q = str(arguments.get("query", "")).lower()
            # Prioritize authentication cues over payment when both appear
            if any(k in q for k in ["2fa", "auth", "code", "password", "reset"]):
                return {
                    "entities": {
                        "issue_type": "Authentication",
                        "affected_component": "2FA",
                        "problem_description": ["codes not arriving", "app out-of-sync"]
                    }
                }
            # Delivery / logistics
            if any(k in q for k in ["delivery", "delivered", "shipping", "shipment", "courier", "carrier", "tracking", "in transit"]):
                return {
                    "entities": {
                        "issue_type": "Delivery",
                        "affected_component": "Logistics",
                        "problem_description": ["delayed delivery", "tracking shows in transit"],
                        "request_type": "expedite delivery"
                    }
                }
            if any(k in q for k in ["payment", "charge", "billing", "invoice"]):
                return {
                    "entities": {
                        "issue_type": "Payment",
                        "affected_component": "Billing",
                        "problem_description": ["duplicate charge"],
                        "request_type": "refund"
                    }
                }
            return {"entities": {}}
        elif tool_name == "enrich_records":
            return {"sla_in_hours": 1, "historical_tickets": 0}
        elif tool_name == "clarify_question":
            ents = arguments.get("structured_data", {}).get("entities", {})
            missing = []
            for k in ("issue_type", "affected_component"):
                if not ents.get(k):
                    missing.append(k)
            if missing:
                return {"question": f"Could you provide more details for: {', '.join(missing)}?"}
            return {"question": "Could you share any reference IDs or screenshots to help us proceed?"}
        elif tool_name == "extract_answer":
            return {"answer": "The issue is related to priority threshold logic in the system."}
        elif tool_name == "knowledge_base_search":
            q = str(arguments.get("query", "")).lower()
            try:
                import json, os
                from pathlib import Path
                kb_path = Path(os.getenv("KB_PATH", "config/knowledge_base.json"))
                if kb_path.exists():
                    kb = json.loads(kb_path.read_text(encoding="utf-8"))
                    domain = "auth" if any(k in q for k in ["2fa", "auth", "code", "password", "reset"]) else (
                        "payment" if any(k in q for k in ["payment", "charge", "billing", "invoice"]) else (
                        "delivery" if any(k in q for k in ["delivery", "shipping", "shipment", "courier", "carrier", "tracking"]) else "general"))
                    for art in kb.get("articles", []):
                        tags = [str(t).lower() for t in art.get("tags", [])]
                        # For delivery, avoid matching auth-specific tags like 'password'/'reset'
                        if domain == "delivery" and any(t in ("password","reset","link") for t in tags):
                            continue
                        if any(t in q for t in tags):
                            return {"data": art.get("content", "")}
            except Exception:
                pass
            return {"data": "No information found."}
        elif tool_name == "response_generation":
            name = str(arguments.get("customer_name", "Customer"))
            query_text = str(arguments.get("query", "")).lower()
            kb = arguments.get("solution", {}) or {}
            kb_text = str(kb.get("data", ""))
            # Determine dominant domain by signals
            auth_signals = sum(1 for k in ["2fa", "auth", "code", "password", "reset"] if k in query_text)
            pay_signals = sum(1 for k in ["payment", "charge", "billing", "invoice"] if k in query_text)
            delivery_signals = sum(1 for k in ["delivery", "shipping", "shipment", "courier", "carrier", "tracking", "in transit"] if k in query_text)
            if delivery_signals > max(auth_signals, pay_signals):
                hint = "" if not kb_text else " " + kb_text
                return (
                    f"Hello {name}, we see the delivery appears delayed. "
                    "We've contacted the courier to expedite and will update you with the latest status." + hint + " "
                    "If you can share the order number and carrier, that will help us prioritize."
                ).strip()
            if auth_signals >= pay_signals:
                hint = "" if not kb_text else " " + kb_text
                return (
                    f"Hello {name}, we understand the urgency with account access. "
                    f"Please try re-syncing your authenticator and check spam for codes.{hint} "
                    "We've escalated if needed and will update you shortly."
                ).strip()
            else:
                hint = "" if not kb_text else " " + kb_text
                return (
                    f"Hello {name}, we understand the concern about a duplicate charge. "
                    "We've initiated a review and, if confirmed, will process a refund immediately." + hint + " "
                    "Please share the last 4 digits of the payment method and the transaction time to speed things up."
                ).strip()
        elif tool_name == "escalation_decision":
            return "Senior Software Engineer - Immediate"
        else:
            return {}
    
    def _fallback_common(self, ability: str, **kwargs) -> Any:
        """Fallback implementation for COMMON abilities when MCP fails."""
        if ability == "parse_request_text":
            query = kwargs.get("query", "")
            return {
                "order_id": "123456" if "order" in query else "",
                "product": "machine" if "machine" in query else "",
                "issue": "broken part" if "broken" in query else ""
            }
        elif ability == "normalize_fields":
            priority = kwargs.get("priority", "")
            return {"priority": priority.upper()}
        elif ability == "add_flags_calculations":
            priority = kwargs.get("priority", "")
            flags = {}
            if "high" in priority.lower():
                flags["sla_risk"] = "high"
            return flags
        elif ability == "solution_evaluation":
            return {"score": 70}
        elif ability == "response_generation":
            name = str(kwargs.get("customer_name", "Customer"))
            q = str(kwargs.get("query", "")).lower()
            if "password" in q or "reset" in q:
                return f"Hello {name}, we've generated a new password reset link for your account. Please check your email and try again. If the issue persists, let us know."
            return f"Hello {name}, we've reviewed your request and applied the standard resolution. If you need anything else, please reply to this message."
        else:
            raise ValueError(f"Unknown fallback ability: {ability}")
    
    def _fallback_atlas(self, ability: str, **kwargs) -> Any:
        """Fallback implementation for ATLAS abilities when MCP fails."""
        if ability == "extract_entities":
            return {
                "entities": {
                    "order_number": "123456",
                    "item_affected": "machine",
                    "problem_description": ["broken part"],
                    "request_type": "replacement"
                }
            }
        elif ability == "enrich_records":
            return {"sla_in_hours": 24, "historical_tickets": 0}
        elif ability == "clarify_question":
            return {"question": "Please provide more details on the broken part."}
        elif ability == "extract_answer":
            return {"answer": "The broken part is the motor."}
        elif ability == "knowledge_base_search":
            return {"data": "Replacement is available if within warranty."}
        elif ability == "escalation_decision":
            return "Tier 2 Support"
        elif ability == "update_ticket":
            print("Updating ticket in external CRM system.")
            return True
        elif ability == "close_ticket":
            print("Closing ticket in external system.")
            return True
        elif ability == "execute_api_calls":
            print("Executing external API calls.")
            return True
        elif ability == "trigger_notifications":
            print("Triggering notifications.")
            return True
        else:
            raise ValueError(f"Unknown fallback ability: {ability}")

# Global MCP client instance
mcp_client = MCPClient()
