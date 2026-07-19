import zipfile
from io import BytesIO
from typing import Literal

from pypdf import PdfReader
from bs4 import BeautifulSoup

from app.shared.enums import BookFileType


BookFileTypeLiteral = Literal["pdf", "epub"]


def detect_file_type(filename: str, file_bytes: bytes) -> BookFileType:
    if filename.lower().endswith('.pdf'):
        if not file_bytes.startswith(b'%PDF'):
            raise ValueError("File extension is .pdf but content is not a valid PDF")
        return BookFileType.pdf
    elif filename.lower().endswith('.epub'):
        if not (file_bytes.startswith(b'PK\x03\x04') or file_bytes.startswith(b'PK\x05\x06')):
            raise ValueError("File extension is .epub but content is not a valid EPUB")
        return BookFileType.epub
    else:
        raise ValueError("Unsupported file type. Only PDF and EPUB are supported")


def validate_file_size(file_type: BookFileType, size_bytes: int) -> None:
    if file_type == BookFileType.pdf and size_bytes > 52428800:
        raise ValueError("PDF file size exceeds maximum limit of 50 MB")
    elif file_type == BookFileType.epub and size_bytes > 20971520:
        raise ValueError("EPUB file size exceeds maximum limit of 20 MB")


def extract_pdf_page_count(file_bytes: bytes) -> int:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        return len(reader.pages)
    except Exception:
        raise ValueError("Invalid or corrupted PDF file")


def extract_epub_word_count(file_bytes: bytes) -> int:
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as epub:
            word_count = 0
            for filename in epub.namelist():
                if filename.endswith('.xhtml') or filename.endswith('.html'):
                    with epub.open(filename) as file:
                        content = file.read().decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(content, 'html.parser')
                        text = soup.get_text()
                        words = text.split()
                        word_count += len(words)
            return word_count
    except Exception:
        raise ValueError("Invalid or corrupted EPUB file")


def validate_content_limits(file_type: BookFileType, page_count: int | None, word_count: int | None) -> None:
    if file_type == BookFileType.pdf and page_count and page_count > 300:
        raise ValueError("PDF page count exceeds maximum limit of 300 pages")
    elif file_type == BookFileType.epub and word_count and word_count > 100000:
        raise ValueError("EPUB word count exceeds maximum limit of 100,000 words")