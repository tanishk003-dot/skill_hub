import re
import io
import zipfile
import docx
from fastapi import HTTPException, status
from app.core.config import settings

def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def parse_txt_content(content_bytes: bytes) -> str:
    # Check for binary executable signatures (MZ, ELF, etc.) or null bytes
    if b"\x00" in content_bytes[:1024] or content_bytes.startswith(b"MZ") or content_bytes.startswith(b"\x7fELF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid text file: binary or executable content detected."
        )
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to decode text file. Please ensure UTF-8 encoding."
    )

def parse_vtt_content(content_bytes: bytes) -> str:
    raw_text = parse_txt_content(content_bytes)
    lines = raw_text.splitlines()
    
    # Validate WebVTT header
    first_few_lines = "\n".join(lines[:5])
    if "WEBVTT" not in first_few_lines and "-->" not in raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VTT file: missing WEBVTT header or cue timestamps."
        )

    # Clean VTT lines
    cleaned_lines = []
    timestamp_pattern = re.compile(r"^\s*(\d{1,2}:)?\d{2}:\d{2}\.\d{3}\s*-->\s*(\d{1,2}:)?\d{2}:\d{2}\.\d{3}")
    cue_id_pattern = re.compile(r"^\s*\d+\s*$")
    tag_pattern = re.compile(r"<[^>]+>")

    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if "WEBVTT" in line_strip:
            continue
        if timestamp_pattern.match(line_strip):
            continue
        if cue_id_pattern.match(line_strip):
            continue
        # Remove tags like <v Speaker> or <b>
        cleaned = tag_pattern.sub("", line_strip).strip()
        if cleaned:
            cleaned_lines.append(cleaned)

    return "\n".join(cleaned_lines)

def parse_docx_content(content_bytes: bytes) -> str:
    # Validate it's a valid ZIP archive containing word/document.xml
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
            namelist = z.namelist()
            if "word/document.xml" not in namelist:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DOCX file: missing document content structure."
                )
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid DOCX file: corrupt or non-zip format."
        )

    # Extract plain text only ignoring macros, embedded objects, images
    try:
        doc = docx.Document(io.BytesIO(content_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    paragraphs.append(" | ".join(row_text))
        return "\n".join(paragraphs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to safely extract text from DOCX: {str(e)}"
        )

def process_transcript_file(
    content_bytes: bytes,
    filename: str,
    privacy_consent_acknowledged: bool
) -> dict:
    if not privacy_consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Privacy and consent agreement must be acknowledged before uploading transcripts."
        )

    # Size check
    max_bytes = settings.MAX_TRANSCRIPT_FILE_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_TRANSCRIPT_FILE_SIZE_MB}MB."
        )

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ("txt", "vtt", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only .txt, .vtt, and .docx files are allowed."
        )

    if ext == "txt":
        extracted_text = parse_txt_content(content_bytes)
    elif ext == "vtt":
        extracted_text = parse_vtt_content(content_bytes)
    elif ext == "docx":
        extracted_text = parse_docx_content(content_bytes)
    else:
        extracted_text = ""

    extracted_text = extracted_text.strip()
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no extractable text."
        )

    # Calculate tokens & truncation
    total_tokens = estimate_tokens(extracted_text)
    max_tokens = settings.MAX_TRANSCRIPT_TOKENS
    
    if total_tokens > max_tokens:
        # Truncate by characters roughly matching max_tokens
        max_chars = max_tokens * 4
        truncated_text = extracted_text[:max_chars]
        used_tokens = estimate_tokens(truncated_text)
        truncated_ratio = round(used_tokens / total_tokens, 2)
    else:
        truncated_text = extracted_text
        used_tokens = total_tokens
        truncated_ratio = 1.0

    return {
        "raw_text": extracted_text,
        "used_text": truncated_text,
        "token_count": total_tokens,
        "used_token_count": used_tokens,
        "truncated_ratio": truncated_ratio,
        "file_type": ext
    }

def process_raw_notes(
    notes: str,
    topics_covered: str,
    privacy_consent_acknowledged: bool
) -> dict:
    if not privacy_consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Privacy and consent agreement must be acknowledged."
        )

    full_text = f"{notes or ''}\n\nTopics Covered:\n{topics_covered or ''}".strip()
    if not full_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notes or topics covered must be provided."
        )

    total_tokens = estimate_tokens(full_text)
    max_tokens = settings.MAX_TRANSCRIPT_TOKENS

    if total_tokens > max_tokens:
        max_chars = max_tokens * 4
        truncated_text = full_text[:max_chars]
        used_tokens = estimate_tokens(truncated_text)
        truncated_ratio = round(used_tokens / total_tokens, 2)
    else:
        truncated_text = full_text
        used_tokens = total_tokens
        truncated_ratio = 1.0

    return {
        "raw_text": full_text,
        "used_text": truncated_text,
        "token_count": total_tokens,
        "used_token_count": used_tokens,
        "truncated_ratio": truncated_ratio,
        "file_type": "notes"
    }
