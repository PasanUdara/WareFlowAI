"""
SOP Document Ingestion Pipeline [Member 3]

Loads warehouse SOP markdown files and splits them into
retrieval-friendly sections with metadata.
"""

from typing import List, Dict, Any
from pathlib import Path


class SOPIngestor:
    """Loads and chunks SOP markdown documents."""

    def __init__(self, sops_dir: str = "data/sop_documents"):
        self.sops_dir = Path(sops_dir)

    def load_documents(self) -> List[Dict[str, Any]]:
        """Load all markdown SOP files from the SOP directory."""

        docs = []

        if not self.sops_dir.exists():
            return docs

        for file_path in sorted(self.sops_dir.glob("*.md")):
            with open(file_path, "r", encoding="utf-8") as f:
                docs.append(
                    {
                        "filename": file_path.name,
                        "content": f.read(),
                    }
                )

        return docs

    def split_into_chunks(
        self, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Split SOP documents using markdown headings.

        Each heading section becomes a retrieval chunk.
        """

        chunks = []

        for document in documents:
            filename = document["filename"]
            content = document["content"]

            current_section = None
            current_lines = []

            for line in content.splitlines():

                if line.startswith("# "):
                    current_section = line[2:].strip()
                    continue

                if line.startswith("## "):
                    if current_section and current_lines:
                      chunks.append(
                        {
                            "filename": filename,
                            "section_title": current_section,
                            "content": "\n".join(current_lines).strip(),
                            "sop_id": filename.replace("sop_", "").replace(".md", "").upper(),
                        }
                    )

                    current_section = line[3:].strip()
                    current_lines = []
                    continue

                current_lines.append(line)

            if current_section and current_lines:
                chunks.append(
                    {
                        "filename": filename,
                        "section_title": current_section,
                        "content": "\n".join(current_lines).strip(),
                        "sop_id": filename.replace("sop_", "").replace(".md", "").upper(),
                    }
                )

        return [chunk for chunk in chunks if chunk["content"]]

    def prepare_chunks(self) -> List[Dict[str, Any]]:
        """Load SOP files and convert them into retrieval chunks."""

        documents = self.load_documents()
        return self.split_into_chunks(documents)

    def index_all(self) -> int:
        """
        Prepare SOP chunks for vector indexing.

        Qdrant indexing will be added in the next stage.
        """

        chunks = self.prepare_chunks()
        return len(chunks)