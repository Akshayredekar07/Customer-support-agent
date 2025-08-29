"""
ATLAS MCP Server for external system interactions
Handles abilities that require API calls and external data access
"""
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Atlas Tools Server")

# Mock databases for demonstration
customer_db = {
    "akshay.redekar@example.com": {
        "customer_id": "CUST_001",
        "tier": "premium",
        "historical_tickets": 1,
        "sla_hours": 4
    }
}

product_db = {
    "machine": {
        "category": "hardware",
        "warranty_months": 24,
        "common_issues": ["broken part", "not working", "assembly"]
    }
}

knowledge_base = [
    {
        "id": "KB_001",
        "title": "Broken Parts in Hardware Orders",
        "content": "For broken parts in hardware orders, we offer immediate replacement. Contact tier 2 support with order number.",
        "category": "hardware",
        "keywords": ["broken", "part", "hardware", "replacement"]
    },
    {
        "id": "KB_002", 
        "title": "Machine Not Working - Troubleshooting",
        "content": "If machine is not working: 1) Check power connections 2) Verify assembly 3) Contact support for replacement if defective.",
        "category": "technical",
        "keywords": ["machine", "not working", "troubleshooting"]
    }
]

@mcp.tool()
async def extract_entities(structured_data: Dict[str, Any], 
                         customer_email: str) -> Dict[str, Any]:
    """
    Extract additional entities from external systems
    """
    entities = {}
    
    # Extract customer information
    customer_info = customer_db.get(customer_email, {})
    entities.update(customer_info)
    
    # Extract product information
    product = structured_data.get("product")
    if product:
        product_info = product_db.get(product, {})
        entities["product_info"] = product_info
    
    # Simulate API delay
    await asyncio.sleep(0.1)
    
    return entities

@mcp.tool()
async def enrich_records(structured_data: Dict[str, Any], 
                       customer_email: str) -> Dict[str, Any]:
    """
    Enrich customer records with additional data from external systems
    """
    customer_info = customer_db.get(customer_email, {})
    
    enriched = {
        "sla_in_hours": customer_info.get("sla_hours", 24),
        "historical_tickets": customer_info.get("historical_tickets", 0),
        "customer_tier": customer_info.get("tier", "standard"),
        "product_warranty": None
    }
    
    # Add product warranty info if available
    product = structured_data.get("product")
    if product and product in product_db:
        warranty_months = product_db[product].get("warranty_months")
        if warranty_months:
            enriched["product_warranty"] = f"{warranty_months} months"
    
    # Simulate external API call delay
    await asyncio.sleep(0.2)
    
    return enriched

@mcp.tool()
async def knowledge_base_search(query: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Search knowledge base for relevant articles
    """
    query_lower = query.lower()
    relevant_articles = []
    
    for article in knowledge_base:
        # Score based on keyword matches
        score = 0
        for keyword in article["keywords"]:
            if keyword in query_lower:
                score += 1
        
        # Category bonus
        if category and article["category"] == category:
            score += 2
        
        if score > 0:
            relevant_articles.append({
                "id": article["id"],
                "title": article["title"],
                "content": article["content"],
                "score": score
            })
    
    # Sort by relevance score
    relevant_articles.sort(key=lambda x: x["score"], reverse=True)
    
    # Simulate search delay
    await asyncio.sleep(0.3)
    
    return {
        "articles": relevant_articles[:3],  # Top 3 results
        "total_found": len(relevant_articles),
        "summary": relevant_articles[0]["content"] if relevant_articles else "No relevant articles found"
    }

@mcp.tool()
async def escalation_decision(solution_score: int, flags: Dict[str, Any], 
                            structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make escalation decision based on various factors
    """
    escalate = False
    escalation_path = None
    reasoning = []
    
    # Low solution score
    if solution_score < 70:
        escalate = True
        reasoning.append(f"Low solution confidence: {solution_score}")
    
    # High risk flags
    if flags.get("escalation_risk", 0) > 0.6:
        escalate = True
        reasoning.append(f"High escalation risk: {flags['escalation_risk']}")
    
    # Requires human flag
    if flags.get("requires_human", False):
        escalate = True
        reasoning.append("Flagged as requiring human intervention")
    
    # Specific categories that need human review
    category = structured_data.get("category", "")
    if category in ["returns", "billing"] and structured_data.get("order_id"):
        escalate = True
        reasoning.append(f"Category '{category}' with order ID requires human review")
    
    # Determine escalation path
    if escalate:
        if category == "technical":
            escalation_path = "Technical Support - Tier 2"
        elif category in ["billing", "returns"]:
            escalation_path = "Customer Relations - Tier 2"
        else:
            escalation_path = "General Support - Tier 2"
    
    # Simulate decision processing time
    await asyncio.sleep(0.1)
    
    return {
        "escalate": escalate,
        "escalation_path": escalation_path,
        "reasoning": reasoning,
        "next_action": "escalate" if escalate else "resolve"
    }

@mcp.tool()
async def clarify_question(structured_data: Dict[str, Any], 
                         missing_info: List[str]) -> str:
    """
    Generate clarification question for customer
    """
    issue = structured_data.get("issue", "your request")
    
    if "order_id" in missing_info:
        return f"To help resolve your issue with {issue}, could you please provide your order number?"
    elif "product" in missing_info:
        return f"Could you please specify which product you're having issues with?"
    else:
        return f"Could you provide more details about {issue}?"

@mcp.tool()
async def extract_answer(customer_response: str) -> Dict[str, Any]:
    """
    Extract structured answer from customer response
    """
    # Simple extraction logic - in production this would be more sophisticated
    extracted: Dict[str, Any] = {
        "order_id": None,
        "additional_info": customer_response
    }
    
    # Look for order patterns
    import re
    order_pattern = r'#?(\d{6,})'
    match = re.search(order_pattern, customer_response)
    if match:
        extracted["order_id"] = match.group(1)
    
    return extracted

@mcp.tool()
async def update_ticket(ticket_id: str, status: str, 
                      escalation_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Update ticket in external system
    """
    update_data = {
        "ticket_id": ticket_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "escalation_path": escalation_path
    }
    
    # Simulate API call to ticket system
    await asyncio.sleep(0.2)
    
    print(f"Ticket {ticket_id} updated to status: {status}")
    if escalation_path:
        print(f"Escalated to: {escalation_path}")
    
    return update_data

@mcp.tool()
async def close_ticket(ticket_id: str, resolution_summary: str) -> Dict[str, Any]:
    """
    Close ticket in external system
    """
    close_data = {
        "ticket_id": ticket_id,
        "status": "closed",
        "resolution": resolution_summary,
        "closed_at": datetime.utcnow().isoformat()
    }
    
    # Simulate API call
    await asyncio.sleep(0.1)
    
    print(f"Ticket {ticket_id} closed with resolution: {resolution_summary[:50]}...")
    
    return close_data

@mcp.tool()
async def execute_api_calls(api_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Execute multiple API calls
    """
    results = []
    
    for call in api_calls:
        # Simulate API execution
        result = {
            "api": call.get("endpoint", "unknown"),
            "status": "success",
            "executed_at": datetime.utcnow().isoformat()
        }
        results.append(result)
        await asyncio.sleep(0.1)  # Simulate API latency
    
    return results

@mcp.tool()
async def trigger_notifications(notification_type: str, 
                              recipients: List[str], message: str) -> Dict[str, Any]:
    """
    Trigger notifications via external systems
    """
    notification_data = {
        "type": notification_type,
        "recipients": recipients,
        "message": message,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
    
    # Simulate notification system call
    await asyncio.sleep(0.2)
    
    print(f"Notification sent to {len(recipients)} recipients: {message[:30]}...")
    
    return notification_data
