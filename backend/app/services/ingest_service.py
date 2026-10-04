import re

def chunk_section_text(text: str) -> list[dict]:
    """
    Split text into chunks by paragraphs, tagging type by heuristic.
    Production: use layout parser (unstructured, PyMuPDF) for real PDFs.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    for p in paragraphs:
        ptype = "concept"
        low = p.lower()
        if low.startswith("example") or "solution:" in low:
            ptype = "example"
        elif low.startswith("exercise") or low.startswith("try"):
            ptype = "exercise"
        chunks.append({"text": p, "type": ptype})
    return chunks