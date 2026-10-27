"""Extracts raw text from an uploaded resume file (PDF or DOCX)."""
import os
from pypdf import PdfReader
from docx import Document


def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if not text.strip():
            raise ValueError(
                "Could not extract any text from this PDF. It may be a scanned image without a text layer."
            )
        return text

    if ext == ".docx":
        doc = Document(file_path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        if not text.strip():
            raise ValueError("Could not extract any text from this DOCX file.")
        return text

    raise ValueError(f'Unsupported file type "{ext}". Please upload a .pdf or .docx resume.')
