"""
Knowledge and Compliance Agent Coordinator [Member 3]
"""

from typing import Dict, Any, List
from .logic.rag_engine import RAGEngine
from .logic.rules_checker import RulesChecker


class KnowledgeComplianceAgent:
    """
    Validates task parameters against warehouse SOP regulations
    and retrieves relevant evidence from the Qdrant RAG system.
    """

    def __init__(self):
        self.rag_engine = RAGEngine()
        self.rules_checker = RulesChecker()

    def check_compliance(
        self,
        task_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate proposed task actions against warehouse safety rules
        and retrieve relevant SOP evidence.

        Returns:
            Dict containing:
            - is_compliant
            - violations
            - sop_citations
            - sop_evidence
        """

        # 1. Deterministic safety rules check
        violations = self.rules_checker.evaluate(task_parameters)

        # 2. Build a context-specific RAG query
        query_parts: List[str] = []

        if task_parameters.get("is_hazmat"):
            query_parts.append("hazmat")

        if task_parameters.get("target_zone"):
            query_parts.append(
                str(task_parameters.get("target_zone"))
            )

        # Search for the relevant safety topic.
        if violations:
            violation_text = " ".join(violations).lower()

            if "battery" in violation_text:
                query_parts.append(
                    "battery charging minimum battery level"
                )

            if "payload" in violation_text:
                query_parts.append(
                    "payload capacity weight"
                )

            if "speed" in violation_text:
                query_parts.append(
                    "speed limits"
                )

        # Fallback query for hazmat/compliance checks
        if not query_parts:
            query_parts.append(
                "warehouse safety SOP compliance"
            )

        query = " ".join(query_parts)

        # 3. Retrieve authoritative SOP evidence
        search_results = self.rag_engine.search_sops(
            query,
            top_k=3
        )

        # 4. Return readable citation names
        citations: List[str] = [
            result.get(
                "section_title",
                "General SOP"
            )
            for result in search_results
        ]

        # Remove duplicate citation names while preserving order
        citations = list(dict.fromkeys(citations))

        # 5. Return detailed evidence for audit/demo purposes
        sop_evidence: List[Dict[str, Any]] = []

        for result in search_results:
            sop_evidence.append(
                {
                    "sop_id": result.get("sop_id", ""),
                    "filename": result.get("filename", ""),
                    "section_title": result.get(
                        "section_title",
                        "General SOP"
                    ),
                    "content": result.get("content", ""),
                    "similarity_score": result.get("score", 0.0),
                }
            )

        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "sop_citations": citations,
            "sop_evidence": sop_evidence,
        }