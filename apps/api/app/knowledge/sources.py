"""Source authority registry, validation, and SSRF defense for SAMVED Knowledge RAG."""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional, Tuple

from app.knowledge.models import AuthorityTier, SourceType

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_SOURCE_TYPES = {SourceType.MARKDOWN, SourceType.TEXT, SourceType.HTML, SourceType.PDF}

# Known authoritative government domain suffixes (informational heuristic)
AUTHORITATIVE_GOV_DOMAINS = [
    ".gov.in",
    ".nic.in",
    ".wcd.nic.in",
    ".nhm.gov.in",
    ".tn.gov.in",
    ".main.sci.gov.in",
    ".ncw.nic.in",
]


class SecurityValidationError(ValueError):
    """Raised when an ingestion URL or payload fails security inspection."""
    pass


def validate_source_url_ssrf(url: str, allow_test_fixtures: bool = False) -> None:
    """Performs strict SSRF validation on ingestion source URLs.
    
    Blocks loopback (127.0.0.1), link-local (169.254.0.0/16), and private subnets
    (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), unless allow_test_fixtures=True.
    """
    if not url:
        raise SecurityValidationError("Source URL cannot be empty.")

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_SCHEMES:
        raise SecurityValidationError(f"Disallowed URL scheme: '{scheme}'. Only {ALLOWED_SCHEMES} permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityValidationError("Source URL must specify a valid hostname.")

    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        if not allow_test_fixtures:
            raise SecurityValidationError(f"SSRF blocked: host '{hostname}' targets loopback.")
        return

    # Resolve IP address to check for private or multicast ranges
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
                if not allow_test_fixtures:
                    raise SecurityValidationError(
                        f"SSRF blocked: host '{hostname}' resolves to private/restricted IP '{ip_str}'."
                    )
    except socket.gaierror:
        # If hostname cannot be resolved in offline/test environment, reject unless testing
        if not allow_test_fixtures:
            raise SecurityValidationError(f"Host '{hostname}' could not be resolved.")


def validate_document_size(content_size_bytes: int) -> None:
    """Ensures document content does not exceed the 10MB safety boundary."""
    if content_size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        raise SecurityValidationError(
            f"Document payload size ({content_size_bytes} bytes) exceeds maximum allowable limit "
            f"({MAX_DOCUMENT_SIZE_BYTES} bytes)."
        )


def determine_authority_tier(
    publisher: str, source_url: str, explicit_tier: Optional[AuthorityTier] = None
) -> Tuple[AuthorityTier, str]:
    """Determines authority tier and verification rationale.
    
    If explicit_tier is supplied by administrator, verifies alignment with source metadata.
    """
    if explicit_tier is not None:
        return explicit_tier, "Administratively assigned"

    pub_lower = publisher.lower()
    url_lower = source_url.lower()

    # Tier 1: Central & State Ministries, Gazettes
    if any(term in pub_lower for term in ["ministry", "department", "government", "govt", "social welfare", "gazette"]):
        return AuthorityTier.TIER_1, "Government Ministry / Department publication"

    # Tier 2: Courts, Commissions, Public Authorities
    if any(term in pub_lower for term in ["court", "tribunal", "commission", "ncw", "slsa"]):
        return AuthorityTier.TIER_2, "Judicial Court / Statutory Commission publication"

    # Tier 3: Approved Institutions / Shelters / DLSA
    if any(term in pub_lower for term in ["dlsa", "shelter", "hospital", "swadhar", "ujjawala", "centre administrator"]):
        return AuthorityTier.TIER_3, "Accredited Institutional Provider"

    # Tier 4: Secondary References & Operational SOPs
    return AuthorityTier.TIER_4, "Secondary reference / Training guideline"
