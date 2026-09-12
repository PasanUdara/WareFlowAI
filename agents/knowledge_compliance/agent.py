"""
Knowledge and Compliance Agent Coordinator [Member 3]
"""

from typing import Dict, Any, List
from .logic.rag_engine import RAGEngine
from .logic.rules_checker import RulesChecker


class KnowledgeComplianceAgent:
    """
    Validates task parameters against SOP regulations and queries Qdrant vector DB
    for authoritative compliance guidelines.
    """
    
    def __init__(self):
        self.rag_engine = RAGEngine()
        self.rules_checker = RulesChecker()
        
    def check_compliance(self, task_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate proposed task actions against rules and SOPs.
        
        Args:
            task_parameters: Dict containing payload_weight, speed, is_hazmat, target_zone, etc.
            
        Returns:
            Dict containing 'is_compliant', 'violations', and 'sop_citations'.
        """
        # 1. Deterministic rules check
        violations = self.rules_checker.evaluate(task_parameters)
        
        # 2. Retrieve relevant SOP context if violations or hazmat
        citations: List[str] = []
        if violations or task_parameters.get("is_hazmat"):
            query = f"hazmat {task_parameters.get('target_zone', '')} speed limit payload"
            search_results = self.rag_engine.search_sops(query, top_k=2)
            citations = [res.get("section_title", "General SOP") for res in search_results]
            
        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "sop_citations": citations
        }
