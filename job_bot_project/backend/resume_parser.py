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
        text += page.get_text("text")  # Use 'text' mode for better structure
    doc.close()
    # Improved section extraction with better regex for clusters
    # Contact Info (look for patterns)
    contact = {}
    phone_match = re.search(r'(\+?\d{1,3}?\s?(\(?\d{3}\)?\s?-?\d{3}\s?-?\d{4}))', text)
    if phone_match:
        contact['phone'] = phone_match.group(1)
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    if email_match:
        contact['email'] = email_match.group(1)
    linkedin_match = re.search(r'(linkedin\.com/in/[a-zA-Z0-9_-]+)', text)
    if linkedin_match:
        contact['linkedin'] = f"https://{linkedin_match.group(1)}"
    location_match = re.search(r'([A-Za-z]+,\s*[A-Z]{2})', text)  # Simple city, state
    if location_match:
        contact['location'] = location_match.group(1)
    
    # Education section
    education = []
    edu_matches = re.findall(r'(?i)(?:education|academic background)\s*([\s\S]*?)(?:experience|skills|summary|$)', text)
    if edu_matches:
        for match in edu_matches:
            lines = match.split('\n')
            for line in lines:
                if line.strip():
                    # Simple parse: assume "Degree - Institution - Dates"
                    parts = re.split(r'\s*-\s*|\s*,\s*', line)
                    if len(parts) >= 3:
                        education.append({"degree": parts[0].strip(), "institution": parts[1].strip(), "dates": parts[2].strip()})

    # Work Experience section
    work_experience = []
    work_matches = re.findall(r'(?i)(?:experience|work history|professional experience)\s*([\s\S]*?)(?:education|skills|summary|$)', text)
    if work_matches:
        for match in work_matches:
            entries = re.split(r'\n\s*\n', match)  # Split by blank lines
            for entry in entries:
                lines = entry.split('\n')
                if len(lines) >= 4:  # Assume title, company, dates, description
                    work_experience.append({
                        "title": lines[0].strip(),
                        "company": lines[1].strip(),
                        "dates": lines[2].strip(),
                        "description": ' '.join(lines[3:]).strip()
                    })

    return {
        "raw_text": text,
        "contact_info": contact,
        "education": education,
        "work_experience": work_experience
    }