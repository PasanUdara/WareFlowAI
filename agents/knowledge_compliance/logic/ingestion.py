"""
SOP Document Ingestion Pipeline [Member 3]
Parses markdown SOP files, splits into semantic chunks, and indexes into Qdrant collection.
"""

from typing import List, Dict, Any
from pathlib import Path


class SOPIngestor:
    """Chunks and indexes SOP markdown documents."""
    
    def __init__(self, sops_dir: str = "data/sop_documents"):
        self.sops_dir = Path(sops_dir)
        
    def load_documents(self) -> List[Dict[str, Any]]:
        """
        Scan directory and read markdown SOP files.
        
        # TODO: [Member 3] Implement markdown header splitting and metadata tagging.
        """
        docs = []
        if not self.sops_dir.exists():
            return docs
            
        for file_path in self.sops_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                docs.append({
                    "filename": file_path.name,
                    "content": f.read()
                })
        return docs

    def index_all(self) -> int:
        """
        Embed all loaded SOP documents into Qdrant vector database.
        
        # TODO: [Member 3] Upsert vectors to Qdrant collection.
        """
        docs = self.load_documents()
        return len(docs)
