"""Job description parser and cleaner."""

from pathlib import Path
import re
import unicodedata
from bs4 import BeautifulSoup
import pymupdf


BOILERPLATE_PATTERNS = [
    r"(?i)equal\s+opportunity\s+employer.*?(?=\n\n|\Z)",
    r"(?i)we\s+are\s+an\s+equal\s+opportunity.*?employer.*?(?=\n\n|\Z)",
    r"(?i)eeo\s+statement.*?(?=\n\n|\Z)",
    r"(?i)accommodations?:\s*if\s+you\s+need\s+an\s+accommodation.*?(?=\n\n|\Z)",
    r"(?i)privacy\s+notice:\s*please\s+note\s+that\s+by\s+submitting.*?(?=\n\n|\Z)",
    r"(?i)california\s+consumer\s+privacy\s+act.*?(?=\n\n|\Z)",
    r"(?i)applicant\s+privacy\s+policy.*?(?=\n\n|\Z)",
    r"(?i)we\s+do\s+not\s+discriminate\s+on\s+the\s+basis\s+of.*?(?=\n\n|\Z)",
]


class JDParser:
    """Parses and cleans job description HTML, text, and PDF files."""

    @staticmethod
    def clean_html(html_content: str) -> str:
        """Strip HTML tags, normalize whitespace and unicode, and remove boilerplate."""
        if not html_content or not html_content.strip():
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Add linebreaks before block elements
        for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"]):
            block.insert_before("\n")

        raw_text = soup.get_text()
        return JDParser.clean_text(raw_text)

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize encoding, whitespace, and remove known boilerplate paragraphs."""
        if not text:
            return ""

        # Normalize unicode (decompose accented chars and non-breaking spaces)
        text = unicodedata.normalize("NFKC", text)

        # Remove boilerplate sections
        for pattern in BOILERPLATE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.DOTALL)

        # Normalize whitespace while preserving paragraphs
        lines = []
        for line in text.splitlines():
            cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
            if cleaned_line:
                lines.append(cleaned_line)

        # Join into coherent text with single empty lines between blocks
        cleaned_text = "\n".join(lines)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        return cleaned_text.strip()

    @staticmethod
    def extract_from_file(file_path: str | Path) -> str:
        """Extract clean text from PDF or text file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JD file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return JDParser.extract_from_pdf(path)
        elif suffix in [".txt", ".md", ".html", ".htm"]:
            content = path.read_text(encoding="utf-8", errors="replace")
            if suffix in [".html", ".htm"]:
                return JDParser.clean_html(content)
            return JDParser.clean_text(content)
        else:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported: .pdf, .txt, .html, .md")

    @staticmethod
    def extract_from_pdf(pdf_path: str | Path) -> str:
        """Extract and clean text from PDF using PyMuPDF."""
        doc = pymupdf.open(str(pdf_path))
        text_parts = []
        try:
            for page in doc:
                text_parts.append(page.get_text())
        finally:
            doc.close()

        full_text = "\n".join(text_parts)
        return JDParser.clean_text(full_text)
