"""
Dynamic Industry Configuration Loader
Allows switching between different industry configurations without code changes
"""

import json
import os
from typing import Dict, Any, Optional

class IndustryLoader:
    """Dynamic loader for industry-specific configurations"""
    
    def __init__(self, config_path: str = "config/industry_config.json"):
        self.config_path = config_path
        self.current_industry = None
        self.config = None
        self._load_configs()
    
    def _load_configs(self):
        """Load all industry configurations from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Loaded {len(self.config)} industry configurations")
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_path}")
            self.config = {}
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in configuration file: {self.config_path}")
            self.config = {}
    
    def get_available_industries(self) -> list:
        """Get list of available industry configurations"""
        return list(self.config.keys())
    
    def set_industry(self, industry_name: str) -> bool:
        """Set the current industry configuration"""
        if industry_name not in self.config:
            print(f"❌ Industry '{industry_name}' not found. Available: {self.get_available_industries()}")
            return False
        
        self.current_industry = industry_name
        print(f"✅ Industry set to: {self.config[industry_name]['name']}")
        return True
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the current industry configuration"""
        if not self.current_industry:
            print("❌ No industry selected. Use set_industry() first.")
            return None
        return self.config[self.current_industry]
    
    def get_keywords(self, category: str) -> list:
        """Get keywords for a specific category in current industry"""
        config = self.get_current_config()
        if not config:
            return []
        return config.get("keywords", {}).get(category, [])
    
    def get_sla_config(self, priority: str) -> int:
        """Get SLA hours for a priority level in current industry"""
        config = self.get_current_config()
        if not config:
            return 24  # Default
        return config.get("sla_config", {}).get(priority.lower(), 24)
    
    def get_escalation_path(self, priority: str) -> str:
        """Get escalation path for a priority level in current industry"""
        config = self.get_current_config()
        if not config:
            return "Standard Support"
        return config.get("escalation_paths", {}).get(priority.lower(), "Standard Support")
    
    def get_knowledge_base(self) -> list:
        """Get knowledge base entries for current industry"""
        config = self.get_current_config()
        if not config:
            return []
        return config.get("knowledge_base", [])
    
    def search_knowledge_base(self, query: str) -> Optional[Dict[str, Any]]:
        """Search knowledge base for patterns matching the query"""
        kb_entries = self.get_knowledge_base()
        query_lower = query.lower()
        
        for entry in kb_entries:
            pattern = entry.get("pattern", "").lower()
            if pattern in query_lower:
                return entry
        
        return None
    
    def print_current_config(self):
        """Print the current industry configuration"""
        config = self.get_current_config()
        if not config:
            return
        
        print(f"\n🏭 Current Industry: {config['name']}")
        print(f"📝 Description: {config['description']}")
        print(f"🔑 Keywords:")
        for category, keywords in config['keywords'].items():
            print(f"   {category}: {', '.join(keywords)}")
        print(f"⏰ SLA Configuration:")
        for priority, hours in config['sla_config'].items():
            print(f"   {priority}: {hours} hours")
        print(f"📚 Knowledge Base Entries: {len(config['knowledge_base'])}")

# Global industry loader instance
industry_loader = IndustryLoader()

# Example usage:
# industry_loader.set_industry("software_engineering")
# industry_loader.print_current_config()
