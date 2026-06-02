from io import BytesIO
import fitz  # PyMuPDF
from docx import Document
import re
import string


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = text.replace("\x00", "")
    return text.strip()



def is_readable(text: str) -> bool:
    if not text:
        return False
    if len(text.split()) < 5:
        return False
    printable = set(string.printable)
    ratio = sum(c in printable for c in text) / max(len(text), 1)
    return ratio > 0.9


def is_reference_line(text: str) -> bool:
    t = text.strip()
    if re.match(r'^\[\d+\]', t):
        return True
    if "arxiv preprint" in t.lower():
        return True
    return False


def classify_section(line: str) -> str | None:
    l = line.lower().strip()
    if not l:
        return None
    if any(k in l for k in ["references", "bibliography"]):
        return "skip"
    if any(k in l for k in ["abstract", "introduction", "background"]):
        return "problem"
    if any(k in l for k in ["method", "approach", "model", "architecture",
                             "distillation", "transformer"]):
        return "method"
    if any(k in l for k in ["result", "experiment", "evaluation",
                             "performance", "accuracy"]):
        return "results"
    if any(k in l for k in ["limitation", "future work",
                             "discussion", "conclusion"]):
        return "limitations"
    return None



def parse_pdf(file_bytes: bytes) -> list[dict]:
    """
    Returns a list of page dicts:
        [{"text": "...", "page_number": 1}, ...]

    Pages with no readable text are omitted.
    The reference section is dropped once encountered.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        in_skip_zone = False

        for page_index, page in enumerate(doc):
            page_number = page_index + 1   # 1-based for human readability
            blocks      = page.get_text("blocks")
            raw_lines   = []

            for block in blocks:
                text = block[4].strip().replace("\n", " ").strip()
                if not text:
                    continue
                if not is_readable(text):
                    continue
                if is_reference_line(text):
                    continue
                raw_lines.append(text)

            if not raw_lines:
                continue

            # Section detection per page
            sections = {"problem": [], "method": [], "results": [], "limitations": []}
            current  = "problem"

            for line in raw_lines:
                new_section = classify_section(line)

                if new_section == "skip":
                    in_skip_zone = True
                    break

                if in_skip_zone:
                    break

                if new_section is not None:
                    current = new_section

                if current in sections:
                    sections[current].append(line)

            if in_skip_zone:
                break   # stop processing further pages once references hit

            structured = []
            for key, content in sections.items():
                joined = " ".join(content).strip()
                if joined:
                    structured.append(f"[{key.upper()}]\n{joined}")

            page_text = clean_text("\n\n".join(structured))

            if page_text:
                pages.append({
                    "text":        page_text,
                    "page_number": page_number,
                })

        doc.close()
        return pages

    except Exception as e:
        raise ValueError(f"PDF parsing failed: {str(e)}")



def parse_docx(file_bytes: bytes) -> list[dict]:
    try:
        doc  = Document(BytesIO(file_bytes))
        text = "\n".join([p.text for p in doc.paragraphs])
        return [{"text": clean_text(text), "page_number": None}]
    except Exception as e:
        raise ValueError(f"DOCX parsing failed: {str(e)}")



# TEXT PARSER
# Returns list of dicts for consistency with parse_pdf.
# Plain text has no page concept so page_number is None.
def parse_text(file_bytes: bytes) -> list[dict]:
    try:
        text = file_bytes.decode("utf-8")
    except Exception:
        text = file_bytes.decode("latin-1")
    return [{"text": clean_text(text), "page_number": None}]


def parse_file(filename: str, file_bytes: bytes) -> list[dict]:
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        return parse_pdf(file_bytes)
    elif ext == "docx":
        return parse_docx(file_bytes)
    elif ext in ["txt", "csv", "log"]:
        return parse_text(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")