import PyPDF2
import docx
import logging
import os
import fitz
import re

def extract_text_from_pdf(file_path):
    """
    Extracts text content from a PDF file.

    Args:
        file_path (str): The absolute path to the PDF file.

    Inputs:
        - file_path (str): Path to the PDF file.

    Returns:
        str or None: The extracted text content as a string, or None if extraction fails.
    """
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
    """
    Extracts text content from a DOCX file.

    Args:
        file_path (str): The absolute path to the DOCX file.

    Inputs:
        - file_path (str): Path to the DOCX file.

    Returns:
        str or None: The extracted text content as a string, or None if extraction fails.
    """
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logging.error(f"Failed to extract text from DOCX {file_path}: {e}", exc_info=True)
        return None

def parse_resume(file_path):
    """
    Parses a resume file (PDF or DOCX) to extract its text content.

    Args:
        file_path (str): The absolute path to the resume file.

    Inputs:
        - file_path (str): Path to the resume file (PDF or DOCX).

    Returns:
        str or None: The extracted text content as a string, or None if the file is not found,
                     is of an unsupported format, or extraction fails.
    """
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

def parse_resume_with_pymupdf(file_path):
      doc = fitz.open(file_path)
      text = ""
      for page in doc:
          text += page.get_text()
      # Simple NLP to extract clusters (improve with regex or Gemini)
      education_match = re.search(r'Education\s*(.*?)\s*Experience', text, re.DOTALL | re.IGNORECASE)
      education = {"institution": "Extracted", "degree": "Extracted"} if education_match else {}
      # Similar for other clusters
      return {"raw_text": text, "education": education, "work_experience": []}  # Return dict for agents
