"""Document normalization, sanitization, and hashing utilities for SAMVED Knowledge RAG."""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Tuple


def compute_sha256(text: str) -> str:
    """Computes SHA-256 hexadecimal hash of given string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_source_url(url: str) -> str:
    """Normalizes source URL to canonical form.
    
    Strips tracking query parameters (utm_*, ref, source, fbclid),
    strips fragments, normalizes scheme and host to lower-case.
    """
    if not url:
        return ""
    
    parsed = urlparse(url.strip())
    # Canonicalize scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    # Clean redundant slashes
    path = re.sub(r"/+", "/", path)
    
    # Strip tracking query params
    clean_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            k_lower = k.lower()
            if not (k_lower.startswith("utm_") or k_lower in {"ref", "source", "fbclid", "gclid"}):
                clean_params.append((k, v))
                
    query = urlencode(clean_params)
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def sanitize_text(content: str) -> str:
    """Sanitizes document text for safe indexing and processing.
    
    Strips malicious HTML tags, scripts, macros, null bytes,
    and excessive whitespace while preserving newlines and multilingual Unicode (ta-IN, hi-IN).
    """
    if not content:
        return ""

    # Remove null bytes and dangerous control characters (preserve \n, \r, \t)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)

    # Strip script, style, iframe, object, embed tags and their contents
    cleaned = re.sub(
        r"<(script|style|iframe|object|embed|applet)[\s\S]*?</\1>",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Strip remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # Normalize excessive carriage returns and whitespace lines
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Compress 3+ newlines into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Compress multiple horizontal spaces into single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    return cleaned.strip()


def normalize_and_hash(content: str) -> Tuple[str, str, str]:
    """Processes document content returning (raw_checksum, normalized_text, content_hash)."""
    raw_checksum = compute_sha256(content)
    normalized_text = sanitize_text(content)
    content_hash = compute_sha256(normalized_text)
    return raw_checksum, normalized_text, content_hash
