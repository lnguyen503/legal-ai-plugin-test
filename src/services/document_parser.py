"""
Document Parser - extracts text from PDF, DOCX, and TXT files
"""
from pathlib import Path


def parse_document(file_path: str, filename: str) -> str:
    """
    Extract text from a document file.
    Supports: PDF (.pdf), Word (.docx, .doc), plain text (.txt, .md)
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return _parse_docx(file_path)
    elif ext in (".txt", ".md"):
        return _parse_txt(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: .pdf, .docx, .doc, .txt, .md"
        )


def _parse_pdf(file_path: str) -> str:
    """Extract text from PDF. Tries pdfplumber first, falls back to PyPDF2."""
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text.strip())
        result = "\n\n".join(text_parts)
        if result.strip():
            return result
        # Fall through to PyPDF2 if pdfplumber returned nothing
    except Exception:
        pass

    # Fallback: PyPDF2
    import PyPDF2

    text_parts = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())
    result = "\n\n".join(text_parts)
    if not result.strip():
        raise ValueError("Could not extract text from PDF. The file may be image-based or encrypted.")
    return result


def _parse_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    if not paragraphs:
        raise ValueError("No text found in DOCX file.")
    return "\n\n".join(paragraphs)


def _parse_txt(file_path: str) -> str:
    """Read a plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if not content.strip():
        raise ValueError("Text file appears to be empty.")
    return content
