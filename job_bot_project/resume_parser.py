import PyPDF2
import docx
import logging
import os

def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file."""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        logging.error(f"Failed to extract text from PDF {file_path}: {e}", exc_info=True)
        return None

def extract_text_from_docx(file_path):
    """Extracts text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logging.error(f"Failed to extract text from DOCX {file_path}: {e}", exc_info=True)
        return None

def parse_resume(file_path):
    """Parses a resume file (PDF or DOCX) to extract text."""
    if not os.path.exists(file_path):
        logging.error(f"Resume file not found at: {file_path}")
        return None
    
    _, extension = os.path.splitext(file_path.lower())
    if extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif extension == '.docx':
        return extract_text_from_docx(file_path)
    else:
        logging.error(f"Unsupported file format: {extension}. Please use PDF or DOCX.")
        return None
