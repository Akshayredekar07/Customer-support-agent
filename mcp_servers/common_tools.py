# """
# COMMON MCP Server for internal, stateless operations
# Handles abilities that don't require external system access
# """
# import json
# import asyncio
# from typing import Dict, Any, Optional
# from langchain_groq import ChatGroq
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.messages import HumanMessage, SystemMessage
# from langchain_core.output_parsers import JsonOutputParser
# import os
# from dotenv import load_dotenv
# from fastmcp import FastMCP

# load_dotenv()

# # Initialize FastMCP server
# mcp = FastMCP("Common Tools Server")

# # Initialize LLM clients
# groq_llm = ChatGroq(model="openai/gpt-oss-120b")
# google_llm = ChatGoogleGenerativeAI(
#     google_api_key=os.getenv("GOOGLE_API_KEY"),
#     model="gemini-2.5-flash"
# )
# json_parser = JsonOutputParser()

# @mcp.tool()
# async def parse_request_text(query: str) -> Dict[str, Any]:
#     """
#     Parse unstructured customer request into structured data
#     """
#     system_prompt = """
#     You are an expert at parsing customer support requests. 
#     Extract structured information from the customer query.
    
#     Return JSON with these fields:
#     - order_id: Any order/transaction numbers mentioned
#     - product: Product or service mentioned
#     - issue: Brief description of the problem
#     - urgency_keywords: List of urgent words found
#     - category: Support category (technical, billing, shipping, returns, general)
#     """
    
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=f"Parse this customer request: {query}")
#     ]
    
#     try:
#         chain = groq_llm | json_parser
#         result = await chain.ainvoke(messages)
#         return result
#     except Exception as e:
#         print(f"Error in parse_request_text: {e}")
#         return {
#             "order_id": None,
#             "product": None,
#             "issue": query[:100],
#             "urgency_keywords": [],
#             "category": "general"
#         }

# @mcp.tool()
# async def normalize_fields(structured_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Normalize and clean structured data fields
#     """
#     normalized = {}
    
#     if structured_data.get("order_id"):
#         order_id = ''.join(c for c in str(structured_data["order_id"]) if c.isalnum())
#         normalized["order_id"] = order_id if order_id else None
    
#     if structured_data.get("product"):
#         normalized["product"] = str(structured_data["product"]).lower().strip()
    
#     if structured_data.get("issue"):
#         normalized["issue"] = str(structured_data["issue"]).strip()
    
#     normalized["urgency_keywords"] = structured_data.get("urgency_keywords", [])
#     normalized["category"] = structured_data.get("category", "general").lower()
    
#     return normalized

# @mcp.tool()
# async def add_flags_calculations(structured_data: Dict[str, Any], 
#                                enriched_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Calculate flags and risk scores based on data
#     """
#     flags = {
#         "sla_risk": "low",
#         "escalation_risk": 0.0,
#         "complexity_score": 1,
#         "requires_human": False
#     }
    
#     # Calculate SLA risk
#     urgency_keywords = structured_data.get("urgency_keywords", [])
#     urgent_words = ["urgent", "asap", "immediately", "broken", "not working", "critical"]
#     urgency_score = sum(1 for word in urgency_keywords if word.lower() in urgent_words)
    
#     if urgency_score >= 2 or enriched_data.get("sla_in_hours", 24) <= 4:
#         flags["sla_risk"] = "high"
#     elif urgency_score >= 1:
#         flags["sla_risk"] = "medium"
    
#     # Calculate escalation risk
#     category = structured_data.get("category", "general")
#     high_risk_categories = ["technical", "billing", "returns"]
    
#     risk_score = 0.1  # Base risk
#     if category in high_risk_categories:
#         risk_score += 0.3
#     if enriched_data.get("historical_tickets", 0) > 2:
#         risk_score += 0.2
#     if flags["sla_risk"] == "high":
#         risk_score += 0.3
    
#     flags["escalation_risk"] = min(risk_score, 1.0)
    
#     # Calculate complexity score
#     complexity = 1
#     if "order_id" in structured_data and structured_data["order_id"]:
#         complexity += 2
#     if category in high_risk_categories:
#         complexity += 3
    
#     flags["complexity_score"] = min(complexity, 10)
#     flags["requires_human"] = flags["escalation_risk"] > 0.7
    
#     return flags

# @mcp.tool()
# async def solution_evaluation(retrieved_data: Dict[str, Any], 
#                             structured_data: Dict[str, Any]) -> int:
#     """
#     Evaluate solution confidence score based on available data
#     """
#     system_prompt = """
#     You are evaluating how confident we are in solving a customer's issue.
    
#     Consider:
#     - Availability of relevant knowledge base data
#     - Complexity of the issue
#     - Completeness of information
    
#     Return a JSON object with a single field 'score' (integer 1-100):
#     - 90-100: Very confident, can resolve automatically
#     - 70-89: Moderately confident, may need minor clarification  
#     - 50-69: Low confidence, likely needs human review
#     - 1-49: Very low confidence, definitely needs escalation
#     """
    
#     context = f"""
#     Customer Issue: {structured_data.get('issue', 'Unknown')}
#     Category: {structured_data.get('category', 'general')}
#     Available Knowledge: {len(retrieved_data.get('articles', []))} articles found
#     Has Order ID: {bool(structured_data.get('order_id'))}
#     """
    
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=context)
#     ]
    
#     try:
#         chain = google_llm | json_parser
#         result = await chain.ainvoke(messages)
#         return result.get("score", 50)
#     except Exception as e:
#         print(f"Error in solution_evaluation: {e}")
#         return 50  # Default moderate score

# @mcp.tool()
# async def response_generation(state_data: Dict[str, Any]) -> str:
#     """
#     Generate customer response based on all available data
#     """
#     system_prompt = """
#     You are a professional customer support agent. Generate a helpful, 
#     empathetic response to the customer based on the available information.
    
#     Be concise but thorough. If escalating, explain next steps clearly.
#     If resolving, provide clear instructions.
#     """
    
#     context = f"""
#     Customer: {state_data.get('customer_name', 'Valued Customer')}
#     Issue: {state_data.get('structured_data', {}).get('issue', 'Support request')}
#     Status: {state_data.get('status', 'in_progress')}
#     Solution Score: {state_data.get('solution_score', 'N/A')}
#     Retrieved Info: {state_data.get('retrieved_data', {}).get('summary', 'No specific info found')}
#     """
    
#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=f"Generate response for: {context}")
#     ]
    
#     try:
#         response = await groq_llm.ainvoke(messages)
#         if isinstance(response.content, str):
#             return response.content
#         elif isinstance(response.content, list):
#             # Join list elements into a single string
#             return " ".join(
#                 str(item) if isinstance(item, (str, dict)) else ""
#                 for item in response.content
#             )
#         else:
#             return str(response.content)
#     except Exception as e:
#         print(f"Error in response_generation: {e}")
#         return f"Thank you for contacting support. We are reviewing your request and will respond shortly."


import json
import asyncio
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
import os
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Common Tools Server")

groq_llm = ChatGroq(model="openai/gpt-oss-120b")
google_llm = ChatGoogleGenerativeAI(
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini-2.5-flash"
)
json_parser = JsonOutputParser()

@mcp.tool()
async def parse_request_text(query: str) -> Dict[str, Any]:
    system_prompt = """
    You are an expert at parsing customer support requests. 
    Extract structured information from the customer query.
    
    Return JSON with these fields:
    - order_id: Any order/transaction numbers mentioned
    - product: Product or service mentioned
    - issue: Brief description of the problem
    - urgency_keywords: List of urgent words found
    - category: Support category (technical, billing, shipping, returns, general)
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Parse this customer request: {query}")
    ]
    
    chain = groq_llm | json_parser
    result = await chain.ainvoke(messages)
    return result

@mcp.tool()
async def normalize_fields(structured_data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {}
    
    if structured_data.get("order_id"):
        order_id = ''.join(c for c in str(structured_data["order_id"]) if c.isalnum())
        normalized["order_id"] = order_id if order_id else None
    
    if structured_data.get("product"):
        normalized["product"] = str(structured_data["product"]).lower().strip()
    
    if structured_data.get("issue"):
        normalized["issue"] = str(structured_data["issue"]).strip()
    
    normalized["urgency_keywords"] = structured_data.get("urgency_keywords", [])
    normalized["category"] = structured_data.get("category", "general").lower()
    
    return normalized

@mcp.tool()
async def add_flags_calculations(structured_data: Dict[str, Any], 
                               enriched_data: Dict[str, Any]) -> Dict[str, Any]:
    flags = {
        "sla_risk": "low",
        "escalation_risk": 0.0,
        "complexity_score": 1,
        "requires_human": False
    }
    
    urgency_keywords = structured_data.get("urgency_keywords", [])
    urgent_words = ["urgent", "asap", "immediately", "broken", "not working", "critical"]
    urgency_score = sum(1 for word in urgency_keywords if word.lower() in urgent_words)
    
    if urgency_score >= 2 or enriched_data.get("sla_in_hours", 24) <= 4:
        flags["sla_risk"] = "high"
    elif urgency_score >= 1:
        flags["sla_risk"] = "medium"
    
    category = structured_data.get("category", "general")
    high_risk_categories = ["technical", "billing", "returns"]
    
    risk_score = 0.1
    if category in high_risk_categories:
        risk_score += 0.3
    if enriched_data.get("historical_tickets", 0) > 2:
        risk_score += 0.2
    if flags["sla_risk"] == "high":
        risk_score += 0.3
    
    flags["escalation_risk"] = min(risk_score, 1.0)
    
    complexity = 1
    if "order_id" in structured_data and structured_data["order_id"]:
        complexity += 2
    if category in high_risk_categories:
        complexity += 3
    
    flags["complexity_score"] = min(complexity, 10)
    flags["requires_human"] = flags["escalation_risk"] > 0.7
    
    return flags

@mcp.tool()
async def solution_evaluation(retrieved_data: Dict[str, Any], 
                            structured_data: Dict[str, Any]) -> int:
    system_prompt = """
    You are evaluating how confident we are in solving a customer's issue.
    
    Consider:
    - Availability of relevant knowledge base data
    - Complexity of the issue
    - Completeness of information
    
    Return a JSON object with a single field 'score' (integer 1-100):
    - 90-100: Very confident, can resolve automatically
    - 70-89: Moderately confident, may need minor clarification  
    - 50-69: Low confidence, likely needs human review
    - 1-49: Very low confidence, definitely needs escalation
    """
    
    context = f"""
    Customer Issue: {structured_data.get('issue', 'Unknown')}
    Category: {structured_data.get('category', 'general')}
    Available Knowledge: {len(retrieved_data.get('articles', []))} articles found
    Has Order ID: {bool(structured_data.get('order_id'))}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]
    
    chain = google_llm | json_parser
    result = await chain.ainvoke(messages)
    return result.get("score", 50)

@mcp.tool()
async def response_generation(state_data: Dict[str, Any]) -> str:
    system_prompt = """
    You are a professional customer support agent. Generate a helpful, 
    empathetic response to the customer based on the available information.
    
    Be concise but thorough. If escalating, explain next steps clearly.
    If resolving, provide clear instructions.
    """
    
    context = f"""
    Customer: {state_data.get('customer_name', 'Valued Customer')}
    Issue: {state_data.get('structured_data', {}).get('issue', 'Support request')}
    Status: {state_data.get('status', 'in_progress')}
    Solution Score: {state_data.get('solution_score', 'N/A')}
    Retrieved Info: {state_data.get('retrieved_data', {}).get('summary', 'No specific info found')}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate response for: {context}")
    ]
    
    response = await groq_llm.ainvoke(messages)
    if isinstance(response.content, str):
        return response.content
    elif isinstance(response.content, list):
        return " ".join(
            str(item) if isinstance(item, (str, dict)) else ""
            for item in response.content
        )
    else:
        return str(response.content)