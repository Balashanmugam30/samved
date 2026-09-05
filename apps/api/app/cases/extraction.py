"""Conservative Transcript Extraction Layer & Injection Defenses (Phase 11)."""

import re
from typing import Dict, List, Optional, Tuple
from app.cases.models import (
    CaseCandidate,
    CaseEntity,
    CaseEvidenceLink,
    ClaimStatus,
    EntityType,
    PersonRole,
    RelationshipType,
)
from app.cases.provenance import create_evidence_link

# Negation indicators across English, Tamil transliteration, and Hindi
NEGATION_WORDS = {
    "not", "never", "no", "neither", "nor", "nowhere", "without",
    "nahi", "nahin", "mat",
    "illai", "illa", "illaiye", "kidayadhu", "vendam"
}

# Common family & relation indicators
RELATION_PATTERNS = [
    (re.compile(r"\b(my\s+)?(sister|akka|thangai|behen)\s+([A-Z][a-z]+|[a-zA-Z]+)", re.IGNORECASE), PersonRole.SUPPORT_PERSON, "sister"),
    (re.compile(r"\b(my\s+)?(brother|annan|thambi|bhai)\s+([A-Z][a-z]+|[a-zA-Z]+)", re.IGNORECASE), PersonRole.HOUSEHOLD_MEMBER, "brother"),
    (re.compile(r"\b(my\s+)?(mother|amma|thaai|maa)\s*([A-Z][a-z]+)?", re.IGNORECASE), PersonRole.SUPPORT_PERSON, "mother"),
    (re.compile(r"\b(my\s+)?(father|appa|thandhai|pitaji)\s*([A-Z][a-z]+)?", re.IGNORECASE), PersonRole.HOUSEHOLD_MEMBER, "father"),
    (re.compile(r"\b(my\s+)?(friend|nanban|thozhan|dost)\s+([A-Z][a-z]+|[a-zA-Z]+)", re.IGNORECASE), PersonRole.SUPPORT_PERSON, "friend"),
    (re.compile(r"\b(my\s+)?(husband|kanavan|pati)\s*([A-Z][a-z]+)?", re.IGNORECASE), PersonRole.HOUSEHOLD_MEMBER, "husband"),
    (re.compile(r"\b(my\s+)?(wife|manaivi|patni)\s*([A-Z][a-z]+)?", re.IGNORECASE), PersonRole.HOUSEHOLD_MEMBER, "wife"),
    (re.compile(r"\b(dr\.|doctor)\s+([A-Z][a-z]+|[a-zA-Z]+)", re.IGNORECASE), PersonRole.SERVICE_PROVIDER, "doctor"),
]

# Location patterns
LOCATION_PATTERNS = [
    re.compile(r"\b(in|at|near|from)\s+([A-Z][a-z]+(?:nagar|puram|patti|halli|pet|bad|pur)?)\b", re.IGNORECASE),
    re.compile(r"\b(chennai|coimbatore|madurai|trichy|salem|tirunelveli|vellore|erode|delhi|mumbai|bengaluru|kolkata)\b", re.IGNORECASE),
]

# Prohibited / malicious claim markers that must be rejected
MALICIOUS_CLAIMS = [
    re.compile(r"\b(definitely\s+(?:lying|guilty)|confirmed\s+guilty|is\s+(?:the\s+offender|a\s+criminal|guilty))\b", re.IGNORECASE),
    re.compile(r"\b(ignore\s+previous\s+instructions|system\s+override|merge\s+all\s+people)\b", re.IGNORECASE),
    re.compile(r"\b(arrest\s+this\s+person|file\s+charges\s+immediately)\b", re.IGNORECASE),
]


def sanitize_dialogue(text: str) -> str:
    """Wraps text in boundary tags and strips control codes to prevent prompt injection."""
    if not text:
        return ""
    # Strip any artificial XML/tag boundaries the user might have inputted
    sanitized = text.replace("<untrusted_dialogue>", "").replace("</untrusted_dialogue>", "")
    sanitized = sanitized.replace("<retrieved_source_data>", "").replace("</retrieved_source_data>", "")
    return f"<untrusted_dialogue>{sanitized.strip()}</untrusted_dialogue>"


def is_claim_malicious_or_illegal(text: str) -> bool:
    """Detects whether proposed extraction text contains prohibited legal/guilt assertions or injection cues."""
    for pattern in MALICIOUS_CLAIMS:
        if pattern.search(text):
            return True
    return False


def is_sentence_negated(sentence: str) -> bool:
    """Checks if a sentence clause contains explicit negation cues."""
    words = set(re.findall(r"\b\w+\b", sentence.lower()))
    return len(words.intersection(NEGATION_WORDS)) > 0


def extract_case_candidates(
    utterance_id: str,
    text: str,
    turn_index: int = 0,
    caller_entity_id: str = "ent-caller",
    case_id: str = "case-default",
) -> Tuple[List[CaseEntity], List[CaseCandidate]]:
    """Conservatively extracts person, location, and relationship candidates from utterance text.
    
    Guarantees:
    - Never asserts guilt or legal determination.
    - Default claim status is REPORTED.
    - Negated clauses will not generate positive location or presence links.
    - Injection instructions and malicious accusations are rejected.
    """
    if is_claim_malicious_or_illegal(text):
        return [], []

    entities: List[CaseEntity] = []
    candidates: List[CaseCandidate] = []

    # Process by sentence clauses
    sentences = re.split(r"[.!?;\n]+", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        is_neg = is_sentence_negated(sent)

        # 1. Person & Role Extractions
        for pattern, role, rel_name in RELATION_PATTERNS:
            match = pattern.search(sent)
            if match:
                groups = [g for g in match.groups() if g]
                name_part = groups[-1].strip() if groups else rel_name.capitalize()
                # Skip if name_part is just relation prefix
                if name_part.lower() in {"my", "the", "a", "an"}:
                    name_part = rel_name.capitalize()

                entity_id = f"ent-person-{name_part.lower()}"
                person_entity = CaseEntity(
                    entity_id=entity_id,
                    case_id=case_id,
                    type=EntityType.PERSON,
                    role=role,
                    label=name_part.capitalize(),
                    claim_status=ClaimStatus.REPORTED,
                    confidence=0.88,
                    source_refs=[f"turn:{utterance_id}"],
                    evidence=[
                        create_evidence_link(
                            source_type="CALL_TRANSCRIPT",
                            source_id=utterance_id,
                            turn_index=turn_index,
                            verbatim_excerpt=sent,
                            confidence=0.88,
                        )
                    ],
                    metadata={"relation_to_caller": rel_name},
                )
                entities.append(person_entity)

                # Relationship candidate: Caller -> SUPPORTS / CONNECTED_TO
                rel_type = (
                    RelationshipType.SUPPORTS
                    if role == PersonRole.SUPPORT_PERSON
                    else RelationshipType.CONNECTED_TO
                )

                candidate = CaseCandidate(
                    case_id=case_id,
                    source_entity=caller_entity_id,
                    source_label="Caller",
                    relationship_type=rel_type,
                    target_entity=entity_id,
                    target_label=name_part.capitalize(),
                    confidence=0.85,
                    evidence_excerpt=sent,
                    source_turn=utterance_id,
                    status="PENDING",
                )
                candidates.append(candidate)

        # 2. Location Extractions (only if clause is NOT negated)
        if not is_neg:
            for loc_pattern in LOCATION_PATTERNS:
                loc_match = loc_pattern.search(sent)
                if loc_match:
                    loc_name = loc_match.group(0).split()[-1].capitalize()
                    loc_id = f"ent-loc-{loc_name.lower()}"
                    loc_entity = CaseEntity(
                        entity_id=loc_id,
                        case_id=case_id,
                        type=EntityType.LOCATION,
                        label=loc_name,
                        claim_status=ClaimStatus.REPORTED,
                        confidence=0.80,
                        source_refs=[f"turn:{utterance_id}"],
                        evidence=[
                            create_evidence_link(
                                source_type="CALL_TRANSCRIPT",
                                source_id=utterance_id,
                                turn_index=turn_index,
                                verbatim_excerpt=sent,
                                confidence=0.80,
                            )
                        ],
                    )
                    entities.append(loc_entity)

                    candidate_loc = CaseCandidate(
                        case_id=case_id,
                        source_entity=caller_entity_id,
                        source_label="Caller",
                        relationship_type=RelationshipType.LOCATED_AT,
                        target_entity=loc_id,
                        target_label=loc_name,
                        confidence=0.80,
                        evidence_excerpt=sent,
                        source_turn=utterance_id,
                        status="PENDING",
                    )
                    candidates.append(candidate_loc)

    return entities, candidates


# Aliases for convenience and backward compatibility
sanitize_transcript_for_extraction = sanitize_dialogue
extract_entities_and_relationships_from_text = extract_case_candidates
